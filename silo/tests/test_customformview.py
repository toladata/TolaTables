import json
import uuid
from datetime import datetime
from urlparse import urljoin

from django.conf import settings
from django.test import TestCase

from rest_framework.test import APIRequestFactory

import factories
from silo.tests import MongoTestCase
from silo.api import CustomFormViewSet, SiloViewSet
from silo.models import Silo, LabelValueStore


class CustomFormHasDataTest(TestCase, MongoTestCase):
    def setUp(self):
        factories.ReadType(read_type='CustomForm')
        self.tola_user = factories.TolaUser()
        self.factory = APIRequestFactory()

    def test_has_data_customform_superuser(self):
        self.tola_user.user.is_staff = True
        self.tola_user.user.is_superuser = True
        self.tola_user.user.save()

        wflvl1 = factories.WorkflowLevel1(
            organization=self.tola_user.organization)
        silo = factories.Silo(
            workflowlevel1=[wflvl1],
            owner=self.tola_user.user,
            public=False)

        request = self.factory.get('api/customform/%s/has_data' % silo.id)
        request.user = self.tola_user.user
        view = CustomFormViewSet.as_view({'get': 'has_data'})
        response = view(request, pk=silo.pk)

        self.assertEqual(response.status_code, 200)

    def test_has_data_customform_normaluser(self):
        wflvl1 = factories.WorkflowLevel1(
            organization=self.tola_user.organization)
        silo = factories.Silo(
            workflowlevel1=[wflvl1],
            owner=self.tola_user.user,
            public=False)

        request = self.factory.get('api/customform/%s/has_data' % 11)
        request.user = self.tola_user.user
        view = CustomFormViewSet.as_view({'get': 'has_data'})
        response = view(request, pk=silo.pk)

        self.assertEqual(response.status_code, 403)


class CustomFormCreateViewTest(TestCase, MongoTestCase):
    def setUp(self):
        factories.ReadType(read_type='CustomForm')
        self.tola_user = factories.TolaUser()
        self.factory = APIRequestFactory()

    def test_create_customform_fields_not_valid(self):
        self.tola_user.user.is_staff = True
        self.tola_user.user.is_superuser = True
        self.tola_user.user.save()

        wflvl1 = factories.WorkflowLevel1(
            organization=self.tola_user.organization)

        form_uuid = uuid.uuid4()
        data = {
            'name': 'CustomForm Test',
            'description': 'This is a test.',
            'fields': 'Test',
            'level1_uuid': wflvl1.level1_uuid,
            'tola_user_uuid': self.tola_user.tola_user_uuid,
            'form_uuid': form_uuid
        }

        request = self.factory.post('api/customform', data=data)
        request.user = self.tola_user.user
        view = CustomFormViewSet.as_view({'post': 'create'})
        response = view(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['fields'][0],
                         'Value must be valid JSON.')

    def test_create_customform_success_superuser(self):
        self.tola_user.user.is_staff = True
        self.tola_user.user.is_superuser = True
        self.tola_user.user.save()

        wflvl1 = factories.WorkflowLevel1(
            organization=self.tola_user.organization)
        fields = [
            {
                'name': 'name',
                'type': 'text'
            },
            {
                'name': 'age',
                'type': 'number'
            },
            {
                'name': 'city',
                'type': 'text'
            }
        ]

        form_uuid = uuid.uuid4()
        data = {
            'name': 'CustomForm Test',
            'description': 'This is a test.',
            'fields': json.dumps(fields),
            'level1_uuid': wflvl1.level1_uuid,
            'tola_user_uuid': self.tola_user.tola_user_uuid,
            'form_uuid': form_uuid
        }

        request = self.factory.post('api/customform', data=data)
        request.user = self.tola_user.user
        view = CustomFormViewSet.as_view({'post': 'create'})
        response = view(request)

        self.assertEqual(response.status_code, 201)

        # For the tearDown
        silo_id = response.data['id']
        silo = Silo.objects.get(pk=silo_id)
        form_name = '{} - {}'.format(data['name'], wflvl1.name)
        fields += CustomFormViewSet._default_columns
        level1_uuids = silo.workflowlevel1.values_list(
            'level1_uuid', flat=True).all()

        self.assertEqual(silo.data_count, 0)
        self.assertEqual(silo.name, form_name)
        self.assertEqual(silo.columns, json.dumps(fields))
        self.assertEqual(silo.description, data['description'])
        self.assertIn(str(data['level1_uuid']), level1_uuids)
        self.assertEqual(silo.owner.tola_user.tola_user_uuid,
                         str(data['tola_user_uuid']))
        self.assertEqual(silo.form_uuid, str(data['form_uuid']))

        url_subpath = '/activity/forms/{}/view'.format(form_uuid)
        form_url = urljoin(settings.ACTIVITY_URL, url_subpath)
        reads = silo.reads.all()
        self.assertEqual(reads[0].read_url, form_url)

    def test_create_customform_long_name(self):
        self.tola_user.user.is_staff = True
        self.tola_user.user.is_superuser = True
        self.tola_user.user.save()

        wflvl1 = factories.WorkflowLevel1(
            name='This Program was created to test when a table has a '
                 'really long name. It should accept long names but it has '
                 'to truncate those name. It is so hard to create a name '
                 'longer than 255 characters that I do not know if this is '
                 'going to work well. Almost there!',
            organization=self.tola_user.organization)
        fields = [
            {
                'name': 'name',
                'type': 'text'
            },
            {
                'name': 'age',
                'type': 'number'
            },
            {
                'name': 'city',
                'type': 'text'
            }
        ]

        form_uuid = uuid.uuid4()
        data = {
            'name': 'CustomForm Test',
            'description': 'This is a test.',
            'fields': json.dumps(fields),
            'level1_uuid': wflvl1.level1_uuid,
            'tola_user_uuid': self.tola_user.tola_user_uuid,
            'form_uuid': form_uuid
        }

        request = self.factory.post('api/customform', data=data)
        request.user = self.tola_user.user
        view = CustomFormViewSet.as_view({'post': 'create'})
        response = view(request)

        self.assertEqual(response.status_code, 201)

        # For the tearDown
        silo_id = response.data['id']
        silo = Silo.objects.get(pk=silo_id)
        silo_name = '{} - {}'.format(data['name'], wflvl1.name)
        silo_name = silo_name[:255]
        url_subpath = '/activity/forms/{}/view'.format(form_uuid)
        form_url = urljoin(settings.ACTIVITY_URL, url_subpath)

        self.assertEqual(len(silo.name), 255)
        self.assertEqual(silo.name, silo_name)

        reads = silo.reads.all()
        self.assertEqual(reads[0].read_url, form_url)

    def test_create_customform_tolauser_not_found(self):
        self.tola_user.user.is_staff = True
        self.tola_user.user.is_superuser = True
        self.tola_user.user.save()

        wflvl1 = factories.WorkflowLevel1(
            organization=self.tola_user.organization)
        fields = [
            {
                'name': 'name',
                'type': 'text'
            },
            {
                'name': 'age',
                'type': 'number'
            },
            {
                'name': 'city',
                'type': 'text'
            }
        ]

        tola_user_uuid = uuid.uuid4()
        form_uuid = uuid.uuid4()
        data = {
            'name': 'CustomForm Test',
            'description': 'This is a test.',
            'fields': json.dumps(fields),
            'level1_uuid': wflvl1.level1_uuid,
            'tola_user_uuid': tola_user_uuid,
            'form_uuid': form_uuid
        }

        request = self.factory.post('api/customform', data=data)
        request.user = self.tola_user.user
        view = CustomFormViewSet.as_view({'post': 'create'})
        response = view(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data,
                         'TolaUser matching query does not exist.')

    def test_create_customform_wfl1_not_found(self):
        self.tola_user.user.is_staff = True
        self.tola_user.user.is_superuser = True
        self.tola_user.user.save()

        fields = [
            {
                'name': 'name',
                'type': 'text'
            },
            {
                'name': 'age',
                'type': 'number'
            },
            {
                'name': 'city',
                'type': 'text'
            }
        ]

        level1_uuid = uuid.uuid4()
        form_uuid = uuid.uuid4()
        data = {
            'name': 'CustomForm Test',
            'description': 'This is a test.',
            'fields': json.dumps(fields),
            'level1_uuid': level1_uuid,
            'tola_user_uuid': self.tola_user.tola_user_uuid,
            'form_uuid': form_uuid
        }

        request = self.factory.post('api/customform', data=data)
        request.user = self.tola_user.user
        view = CustomFormViewSet.as_view({'post': 'create'})
        response = view(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data,
                         'WorkflowLevel1 matching query does not exist.')

    def test_create_customform_missing_fields(self):
        self.tola_user.user.is_staff = True
        self.tola_user.user.is_superuser = True
        self.tola_user.user.save()

        data = {
            'name': 'CustomForm Test',
            'description': 'This is a test.',
        }

        request = self.factory.post(
            'api/customform', data=json.dumps(data),
            content_type='application/json')
        request.user = self.tola_user.user
        view = CustomFormViewSet.as_view({'post': 'create'})
        response = view(request)

        missing_fields = {
            'level1_uuid': [u'This field is required.'],
            'fields': [u'This field is required.'],
            'tola_user_uuid': [u'This field is required.'],
            'form_uuid': [u'This field is required.']
        }

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data, missing_fields)

    def test_create_customform_normaluser(self):
        data = {
            'name': 'CustomForm Test',
            'description': 'This is a test.',
        }

        request = self.factory.post(
            'api/customform', data=json.dumps(data),
            content_type='application/json')
        request.user = self.tola_user.user
        view = CustomFormViewSet.as_view({'post': 'create'})
        response = view(request)

        self.assertEqual(response.status_code, 403)


class CustomFormUpdateViewTest(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.tola_user = factories.TolaUser()

    def test_update_customform_superuser_minimal(self):
        self.tola_user.user.is_staff = True
        self.tola_user.user.is_superuser = True
        self.tola_user.user.save()

        wflvl1 = factories.WorkflowLevel1(
            organization=self.tola_user.organization)
        silo = factories.Silo(
            workflowlevel1=[wflvl1],
            owner=self.tola_user.user,
            public=False)
        fields = [
            {
                'name': 'name',
                'type': 'text'
            },
            {
                'name': 'age',
                'type': 'number'
            },
            {
                'name': 'city',
                'type': 'text'
            }
        ]

        form_uuid = uuid.uuid4()
        data = {
            'name': 'CustomForm Test',
            'fields': json.dumps(fields),
            'level1_uuid': wflvl1.level1_uuid,
            'tola_user_uuid': self.tola_user.tola_user_uuid,
            'form_uuid': form_uuid
        }

        request = self.factory.post('api/customform', data=data)
        request.user = self.tola_user.user
        view = CustomFormViewSet.as_view({'post': 'update'})
        response = view(request, pk=silo.pk)

        self.assertEqual(response.status_code, 200)

        silo = Silo.objects.get(pk=response.data['id'])
        self.assertEquals(silo.name, 'customform_test_health_and_survival'
                                     '_for_syrians_in_affected_regions')
        self.assertEqual(silo.data_count, 0)

    def test_update_customform_missing_data_superuser(self):
        self.tola_user.user.is_staff = True
        self.tola_user.user.is_superuser = True
        self.tola_user.user.save()

        wflvl1 = factories.WorkflowLevel1(
            organization=self.tola_user.organization)
        silo = factories.Silo(
            workflowlevel1=[wflvl1],
            owner=self.tola_user.user,
            public=False)

        data = {
            'name': 'CustomForm Test',
            'description': 'This is a test.',
        }

        request = self.factory.post('api/customform', data=data)
        request.user = self.tola_user.user
        view = CustomFormViewSet.as_view({'post': 'update'})
        response = view(request, pk=silo.pk)

        self.assertEqual(response.status_code, 400)

    def test_update_customform_normaluser(self):
        wflvl1 = factories.WorkflowLevel1(
            organization=self.tola_user.organization)
        silo = factories.Silo(
            workflowlevel1=[wflvl1],
            owner=self.tola_user.user,
            public=False)

        data = {
            'name': 'CustomForm Test',
            'description': 'This is a test.',
        }

        request = self.factory.post('api/customform', data=data)
        request.user = self.tola_user.user
        view = CustomFormViewSet.as_view({'post': 'update'})
        response = view(request, pk=silo.pk)

        self.assertEqual(response.status_code, 403)


class CustomFormSaveDataViewTest(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.tola_user = factories.TolaUser()

        self.read = factories.Read(
            owner=self.tola_user.user,
            type=factories.ReadType(read_type='CustomForm'),
            read_name='Lennon Survey',
        )
        wflvl1 = factories.WorkflowLevel1(
            organization=self.tola_user.organization)
        self.silo = factories.Silo(
            name='Lennon Survey',
            workflowlevel1=[wflvl1],
            owner=self.tola_user.user,
            columns='[{"name": "name", "type": "text"},'
                    '{"name": "age", "type": "number"},'
                    '{"name": "city", "type": "text"},'
                    '{"name": "submitted_by", "type": "text"},'
                    '{"name": "submission_data", "type": "date"},'
                    '{"name": "submission_time", "type": "date"}]',
            reads=[self.read],
            public=False
        )

    def tearDown(self):
        # Have to remove the created lvs
        lvss = LabelValueStore.objects.filter(silo_id=self.silo.id)
        for lvs in lvss:
            lvs.delete()

    def test_save_data_customform_no_silo_superuser(self):
        self.tola_user.user.is_staff = True
        self.tola_user.user.is_superuser = True
        self.tola_user.user.save()

        data = {
            'silo_id': 123456,
            'data': {
                'name': 'John Lennon',
                'age': 40,
                'city': 'Liverpool'
            }
        }

        request = self.factory.post('api/customform/save_data',
                                    data=json.dumps(data),
                                    content_type='application/json')
        request.user = self.tola_user.user
        view = CustomFormViewSet.as_view({'post': 'save_data'})
        response = view(request)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data['detail'], 'Not found.')

    def test_save_data_customform_superuser(self):
        self.tola_user.user.is_staff = True
        self.tola_user.user.is_superuser = True
        self.tola_user.user.save()

        data = {
            'silo_id': self.silo.id,
            'data': {
                'name': 'John Lennon',
                'age': 40,
                'city': 'Liverpool'
            }
        }

        request = self.factory.post('api/customform/save_data',
                                    data=json.dumps(data),
                                    content_type='application/json')
        request.user = self.tola_user.user
        view = CustomFormViewSet.as_view({'post': 'save_data'})
        response = view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['detail'], 'It was successfully saved.')
        self.assertEqual(self.silo.data_count, 1)

        request = self.factory.get('/api/silo/{}/data'.format(self.silo.id))
        request.user = self.tola_user.user
        view = SiloViewSet.as_view({'get': 'data'})
        response = view(request, id=self.silo.id)
        json_content = json.loads(response.content)
        data = json_content['data'][0]

        self.assertEqual(data['name'], 'John Lennon')
        self.assertEqual(data['age'], 40)
        self.assertEqual(data['city'], 'Liverpool')

        # check the submission date
        submission_date = datetime.now().strftime('%Y-%m-%d')
        self.assertIn('submission_date', data)
        self.assertEqual(data['submission_date'], submission_date)

        # the time can be different if the request takes a while
        self.assertIn('submission_time', data)
        self.assertTrue(data['submission_time'])

        # it shouldn't have a submitted_by because it wasn't provided
        self.assertNotIn('submitted_by', data)

    def test_save_data_customform_missing_data_superuser(self):
        self.tola_user.user.is_staff = True
        self.tola_user.user.is_superuser = True
        self.tola_user.user.save()

        data = {
            'data': {
                'name': 'John Lennon',
                'age': 40,
                'city': 'Liverpool'
            }
        }

        request = self.factory.post('api/customform/save_data',
                                    data=json.dumps(data),
                                    content_type='application/json')
        request.user = self.tola_user.user
        view = CustomFormViewSet.as_view({'post': 'save_data'})
        response = view(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['detail'], 'Missing data.')

    def test_save_data_customform_normaluser(self):
        user = factories.User(first_name='Homer', last_name='Simpson')
        sender_tola_user = factories.TolaUser(user=user)

        data = {
            'silo_id': self.silo.id,
            'data': {
                'name': 'John Lennon',
                'age': 40,
                'city': 'Liverpool'
            },
            'submitted_by': sender_tola_user.tola_user_uuid.__str__(),
        }

        request = self.factory.post('api/customform/save_data',
                                    data=json.dumps(data),
                                    content_type='application/json')
        request.user = self.tola_user.user
        view = CustomFormViewSet.as_view({'post': 'save_data'})
        response = view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['detail'], 'It was successfully saved.')
        self.assertEqual(self.silo.data_count, 1)

        request = self.factory.get('/api/silo/{}/data'.format(self.silo.id))
        request.user = self.tola_user.user
        view = SiloViewSet.as_view({'get': 'data'})
        response = view(request, id=self.silo.id)
        json_content = json.loads(response.content)
        data = json_content['data'][0]

        self.assertEqual(data['name'], 'John Lennon')
        self.assertEqual(data['age'], 40)
        self.assertEqual(data['city'], 'Liverpool')

        # check the submission date
        submission_date = datetime.now().strftime('%Y-%m-%d')
        self.assertIn('submission_date', data)
        self.assertEqual(data['submission_date'], submission_date)

        # the time can be different if the request takes a while
        self.assertIn('submission_time', data)
        self.assertTrue(data['submission_time'])

        # check the name of who sent the data
        self.assertIn('submitted_by', data)
        self.assertEqual(data['submitted_by'], sender_tola_user.name)

    def test_save_data_customform_default_columns(self):
        user = factories.User(first_name='Homer', last_name='Simpson')
        sender_tola_user = factories.TolaUser(user=user)

        data = {
            'silo_id': self.silo.id,
            'data': {
                'name': 'John Lennon',
                'age': 40,
                'city': 'Liverpool'
            },
            'submitted_by': sender_tola_user.tola_user_uuid.__str__(),
        }

        request = self.factory.post('api/customform/save_data',
                                    data=json.dumps(data),
                                    content_type='application/json')
        request.user = self.tola_user.user
        view = CustomFormViewSet.as_view({'post': 'save_data'})
        response = view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['detail'], 'It was successfully saved.')
        self.assertEqual(self.silo.data_count, 1)

        # check if the default columns were created
        customform_silo = LabelValueStore.objects.get(silo_id=self.silo.id)
        table_column_names = customform_silo._dynamic_fields.keys()
        for default_col in CustomFormViewSet._default_columns:
            self.assertIn(default_col['name'], table_column_names)

        self.assertEqual(len(table_column_names), 6)

    def test_save_data_customform_no_data_normaluser(self):
        data = {}

        request = self.factory.post('api/customform/save_data',
                                    data=json.dumps(data),
                                    content_type='application/json')
        request.user = self.tola_user.user
        view = CustomFormViewSet.as_view({'post': 'save_data'})
        response = view(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['detail'], 'No data sent.')
