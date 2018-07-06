from django.test import TestCase
from bson import ObjectId

import json
import logging
import factories
from mock import patch, mock
from silo.models import LabelValueStore
from silo.custom_csv_dict_reader import CustomDictReader
from tola.util import clean_data_obj, JSONEncoder, save_data_to_silo, \
    ona_parse_type_group

logger = logging.getLogger("tola")


class RegisterViewTest(TestCase):
    def test_json_encoder(self):
        dict_test = {
            '_id': ObjectId("5aaf820a58d8e7002c889905"),
            'silo_id': 2,
            'read_id': 2,
            'county': "CLAY COUNTY",
            'tiv_2011': 60946.79,
            'statecode': 'FL',
            'policy_id': 353022
        }

        with self.assertRaises(TypeError):
            json.dumps(dict_test)

        encoded = JSONEncoder().encode(dict_test)
        self.assertTrue(isinstance(encoded, str))
        self.assertEqual(encoded, '{"silo_id": 2, "read_id": 2, "county": '
                                  '"CLAY COUNTY", "tiv_2011": 60946.79, '
                                  '"statecode": "FL", "_id": {"$oid": '
                                  '"5aaf820a58d8e7002c889905"}, "policy_id": '
                                  '353022}')


class CleanDataObjTest(TestCase):
    """
    Tests the clean_data_obj function.
    - The returned dict should match with the given data
    - The function has to convert the data values to the right type
    """

    def test_clean_data_obj_success(self):
        rows = [{
            'name': 'John',
            'age': '40',
            'active': '1957-1980',
            'rate': '9.7'
        }]

        expected_data = {
            'name': 'John',
            'age': 40,
            'active': '1957-1980',
            'rate': 9.7
        }

        result = clean_data_obj(rows)
        self.assertEqual(result[0], expected_data)

    def test_clean_data_obj_javascript(self):
        rows = [{
            'name': 'John',
            'age': '40',
            'active': '<script src=/hacker/bad.js></script>',
            'rate': '9.7'
        }]

        expected_data = {
            'name': 'John',
            'age': 40,
            'active': '&lt;script src=/hacker/bad.js&gt;&lt;/script&gt;',
            'rate': 9.7
        }

        result = clean_data_obj(rows)
        self.assertEqual(result[0], expected_data)

    def test_clean_data_obj_empty_obj(self):
        result = clean_data_obj({})
        self.assertEqual(result, {})

    def test_clean_data_obj_list_data(self):
        row = ['John', '40', '1957-1980', '9.7']
        expected_data = ['John', 40, '1957-1980', 9.7]

        result = clean_data_obj(row)
        self.assertEqual(result, expected_data)


class save_data_to_siloTest(TestCase):
    """
    Tests the clean_data_obj function.
    - The returned dict should match with the given data
    - The function has to convert the data values to the right type
    """

    def setUp(self):
        self.tola_user = factories.TolaUser()
        self.read = factories.Read(read_name='Test Read')
        self.silo = factories.Silo(owner=self.tola_user.user,
                                   reads=[self.read])
        logging.disable(logging.ERROR)

    def tearDown(self):
        # Have to remove the created lvs
        lvss = LabelValueStore.objects.filter(silo_id=self.silo.id)
        for lvs in lvss:
            lvs.delete()
        logging.disable(logging.NOTSET)

    def test_save_data_to_silo_success(self):
        read_file = open('silo/tests/sample_data/test.csv')
        reader = CustomDictReader(read_file)
        expected_response = {
            'skipped_rows': set([]),
            'num_rows': 4
        }

        result = save_data_to_silo(self.silo, reader, self.read)
        self.assertEqual(result, expected_response)

    def test_save_data_to_silo_already_lvs(self):
        read_file = open('silo/tests/sample_data/test.csv')
        reader = CustomDictReader(read_file)
        lvs = factories.LabelValueStore()
        lvs.silo_id = self.silo.id
        lvs.save()
        expected_response = {
            'skipped_rows': set([]),
            'num_rows': 4
        }

        result = save_data_to_silo(self.silo, reader, self.read)
        self.assertEqual(result, expected_response)
        self.assertEqual(self.silo.data_count, 5)

    def test_save_data_to_silo_default_read(self):
        read_file = open('silo/tests/sample_data/test.csv')
        reader = CustomDictReader(read_file)
        expected_response = {
            'skipped_rows': set([]),
            'num_rows': 4
        }

        result = save_data_to_silo(self.silo, reader)
        lvss = LabelValueStore.objects.filter(silo_id=self.silo.id)
        self.assertEqual(result, expected_response)
        for lvs in lvss:
            self.assertEqual(lvs.read_id, -1)

    def test_save_data_to_silo_list_dict(self):
        data = [{
            'name': 'John',
            'age': '40',
            'active': '1957-1980',
            'rate': '9.7'
        }]
        expected_response = {
            'skipped_rows': set([]),
            'num_rows': 1
        }

        result = save_data_to_silo(self.silo, data, self.read)
        self.assertEqual(result, expected_response)

    def test_save_data_to_silo_empty(self):
        expected_response = {
            'skipped_rows': set([]),
            'num_rows': 0
        }

        result = save_data_to_silo(self.silo, list(), self.read)
        self.assertEqual(result, expected_response)

    def test_save_data_to_silo_unique_field(self):
        read_file = open('silo/tests/sample_data/test.csv')
        reader = CustomDictReader(read_file)
        lvs = factories.LabelValueStore()
        lvs.silo_id = self.silo.id
        lvs.save()
        expected_response = {
            'skipped_rows': set([]),
            'num_rows': 1
        }

        save_data_to_silo(self.silo, reader, self.read)
        factories.UniqueFields(name='E-mail', silo=self.silo)
        data = [{
            'First.Name': 'John',
            'Last.Name': 'Lennon',
            'E-mail': 'john@example.org',
        }]

        result = save_data_to_silo(self.silo, data, self.read)
        self.assertEqual(result, expected_response)
        lvss = LabelValueStore.objects.filter(silo_id=self.silo.id)
        count = 0
        for lvs in lvss:
            lvs_json = json.loads(lvs.to_json())
            if lvs_json.get('First_Name') == 'John':
                self.assertEqual(lvs_json.get('Last_Name'), 'Lennon')
                count += 1

        self.assertEqual(count, 1)

    def test_save_data_to_silo_unique_field_no_lvs(self):
        read_file = open('silo/tests/sample_data/test.csv')
        reader = CustomDictReader(read_file)
        expected_response = {
            'skipped_rows': set([]),
            'num_rows': 4
        }
        factories.UniqueFields(name='E-mail', silo=self.silo)
        result = save_data_to_silo(self.silo, reader, self.read)
        self.assertEqual(result, expected_response)

    def test_save_data_to_silo_skipped_rows(self):
        read_file = open('silo/tests/sample_data/test.csv')
        reader = CustomDictReader(read_file)
        lvs = factories.LabelValueStore()
        lvs.silo_id = self.silo.id
        lvs.save()
        save_data_to_silo(self.silo, reader, self.read)

        # create multiple lvs
        read_file = open('silo/tests/sample_data/test.csv')
        reader = CustomDictReader(read_file)
        lvs = factories.LabelValueStore()
        lvs.silo_id = self.silo.id
        lvs.save()
        save_data_to_silo(self.silo, reader, self.read)

        factories.UniqueFields(name='E-mail', silo=self.silo)
        skipped_rows = ['E-mail=john@example.org',
                        'silo_id={}'.format(self.silo.id)]
        expected_response = {
            'skipped_rows': set(skipped_rows),
            'num_rows': 0}
        data = [{
            'First.Name': 'John',
            'Last.Name': 'Lennon',
            'E-mail': 'john@example.org',
        }]

        result = save_data_to_silo(self.silo, data, self.read)
        self.assertEqual(result, expected_response)

    @patch('tola.util.ona_parse_type_repeat')
    def test_ona_parse_type_group_with_valid_data(self,
                                                  mock_ona_parse_type_repeat):

        mock_ona_parse_type_repeat.return_value = []
        silo = factories.Silo(name='test_ona')
        read = factories.Read(read_name='test_ona_read',
                              owner=self.tola_user.user)
        silo.reads.add(read)
        data = [{
                    '_notes': [],
                    'Name': 'Bob',
                    'Number': '1',
                    '_edited': False,
                    '_status': 'submitted_via_web',
                    '_submission_time': '2018-06-26T15:01:19',
                    '_id': 31108803
                }, {
                    '_notes': [],
                    'Name': 'Jason',
                    'Number': '2',
                    '_edited': False,
                    '_status': 'submitted_via_web',
                    '_submission_time': '2018-06-26T15:01:19',
                    '_id': 31108806
                }]

        form_data = [{
                        'bind': {
                            'required': 'true'
                        },
                        'type': 'text',
                        'name': 'Name',
                        'label': 'Name'
                    }, {
                        'bind': {
                            'required': 'true'
                        },
                        'type': 'text',
                        'name': 'Number',
                        'label': 'Number'
                    }, {
                        'bind': {
                            'calculate': "'vviKGm8pxer5Zu3E3H3wbf'"
                        },
                        'type': 'calculate',
                        'name': '__version__'
                    }, {
                        'control': {
                            'bodyless': True
                        },
                        'type': 'group',
                        'children': [{
                            'bind': {
                                'readonly': 'true()',
                                'calculate': "concat('uuid:', uuid())"
                            },
                            'type': 'calculate',
                            'name': 'instanceID'
                        }],
                        'name': 'meta'
                    }]

        with mock.patch.object(logger, 'warning') as mock_logger:
            ona_parse_type_group(data, form_data, '', silo, read)
            mock_logger.assert_not_called()

    @patch('tola.util.ona_parse_type_repeat')
    def test_ona_parse_type_group_with_invalid_keys(
            self, mock_ona_parse_type_repeat):

        mock_ona_parse_type_repeat.return_value = []
        silo = factories.Silo(name='test_ona')
        read = factories.Read(read_name='test_ona_read',
                              owner=self.tola_user.user)
        silo.reads.add(read)
        data = [{
                    '_notes': [],
                    'Name': 'Bob',
                    '_Number': '1',
                    '_edited': False,
                    '_status': 'submitted_via_web',
                    '_submission_time': '2018-06-26T15:01:19',
                    '_id': 31108803
                }, {
                    '_notes': [],
                    'Name': 'Jason',
                    '_Number': '2',
                    '_edited': False,
                    '_status': 'submitted_via_web',
                    '_submission_time': '2018-06-26T15:01:19',
                    '_id': 31108806
                }]

        form_data = [{
                        'bind': {
                            'required': 'true'
                        },
                        'type': 'text',
                        'name': 'Name',
                        'label': 'Name'
                    }, {
                        'bind': {
                            'required': 'true'
                        },
                        'type': 'text',
                        'name': 'Number2',
                        'label': 'Number'
                    }, {
                        'bind': {
                            'calculate': "'vviKGm8pxer5Zu3E3H3wbf'"
                        },
                        'type': 'calculate',
                        'name': '__version__'
                    }, {
                        'control': {
                            'bodyless': True
                        },
                        'type': 'group',
                        'children': [{
                            'bind': {
                                'readonly': 'true()',
                                'calculate': "concat('uuid:', uuid())"
                            },
                            'type': 'calculate',
                            'name': 'instanceID'
                        }],
                        'name': 'meta'
                    }]

        with mock.patch.object(logger, 'warning') as mock_logger:
            ona_parse_type_group(data, form_data, '', silo, read)
            mock_logger.assert_called_once_with(
                "Keyerror for silo 2, 'Number2'")
