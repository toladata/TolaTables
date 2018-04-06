from django.test import TestCase
from bson import ObjectId

import json
import logging
import factories
from silo.models import LabelValueStore
from silo.custom_csv_dict_reader import CustomDictReader
from tola.util import clean_data_obj, JSONEncoder, saveDataToSilo


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


class SaveDataToSiloTest(TestCase):
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

        result = saveDataToSilo(self.silo, reader, self.read)
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

        result = saveDataToSilo(self.silo, reader, self.read)
        self.assertEqual(result, expected_response)
        self.assertEqual(self.silo.data_count, 5)

    def test_save_data_to_silo_default_read(self):
        read_file = open('silo/tests/sample_data/test.csv')
        reader = CustomDictReader(read_file)
        expected_response = {
            'skipped_rows': set([]),
            'num_rows': 4
        }

        result = saveDataToSilo(self.silo, reader)
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

        result = saveDataToSilo(self.silo, data, self.read)
        self.assertEqual(result, expected_response)

    def test_save_data_to_silo_empty(self):
        expected_response = {
            'skipped_rows': set([]),
            'num_rows': 0
        }

        result = saveDataToSilo(self.silo, list(), self.read)
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

        saveDataToSilo(self.silo, reader, self.read)
        factories.UniqueFields(name='E-mail', silo=self.silo)
        data = [{
            'First.Name': 'John',
            'Last.Name': 'Lennon',
            'E-mail': 'john@example.org',
        }]

        result = saveDataToSilo(self.silo, data, self.read)
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
        result = saveDataToSilo(self.silo, reader, self.read)
        self.assertEqual(result, expected_response)

    def test_save_data_to_silo_skipped_rows(self):
        read_file = open('silo/tests/sample_data/test.csv')
        reader = CustomDictReader(read_file)
        lvs = factories.LabelValueStore()
        lvs.silo_id = self.silo.id
        lvs.save()
        saveDataToSilo(self.silo, reader, self.read)

        # create multiple lvs
        read_file = open('silo/tests/sample_data/test.csv')
        reader = CustomDictReader(read_file)
        lvs = factories.LabelValueStore()
        lvs.silo_id = self.silo.id
        lvs.save()
        saveDataToSilo(self.silo, reader, self.read)

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

        result = saveDataToSilo(self.silo, data, self.read)
        self.assertEqual(result, expected_response)
