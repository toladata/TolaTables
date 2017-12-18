import json

from django.test import TestCase
from django.contrib.auth.models import AnonymousUser

from rest_framework.test import APIRequestFactory

import factories
from silo.tests import MongoTestCase
from silo.api import CustomFormViewSet
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
        self.silo_id = None

    def tearDown(self):
        if self.silo_id:
            # Have to remove the created lvs
            lvss = LabelValueStore.objects.filter(silo_id=self.silo_id)
            for lvs in lvss:
                lvs.delete()

    def test_create_customform_superuser(self):
        self.tola_user.user.is_staff = True
        self.tola_user.user.is_superuser = True
        self.tola_user.user.save()

        wflvl1 = factories.WorkflowLevel1(
            organization=self.tola_user.organization)

        data = {
            'name': 'CustomForm Test',
            'description': 'This is a test.',
            'fields': [
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
            ],
            'level1_uuid': wflvl1.level1_uuid,
            'tola_user_uuid': self.tola_user.tola_user_uuid
        }

        request = self.factory.post('api/customform', data=data)
        request.user = self.tola_user.user
        view = CustomFormViewSet.as_view({'post': 'create'})
        response = view(request)

        self.assertEqual(response.status_code, 201)

        # For the tearDown
        self.silo_id = response.data['id']

    def test_create_customform_missing_data_superuser(self):
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

        self.assertEqual(response.status_code, 400)

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

    def test_update_customform_superuser(self):
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
            'fields': [
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
        }

        request = self.factory.post('api/customform', data=data)
        request.user = self.tola_user.user
        view = CustomFormViewSet.as_view({'post': 'update'})
        response = view(request, pk=silo.pk)

        self.assertEqual(response.status_code, 200)

        customform = Silo.objects.get(pk=response.data['id'])
        self.assertEquals(customform.name, 'customform_test_health_and_survival'
                                           '_for_syrians_in_affected_regions')

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
                    '{"name": "city", "type": "text"}]',
            reads=[self.read],
            public=False
        )

    def tearDown(self):
        # Have to remove the created lvs
        lvss = LabelValueStore.objects.filter(silo_id=self.silo.id)
        for lvs in lvss:
            lvs.delete()

    def test_save_data_customform_no_lvs_superuser(self):
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

        request = self.factory.post('api/customform/%s/save_data' %
                                    self.silo.id, data=json.dumps(data),
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

        factories.LabelValueStore(silo_id=self.silo.id, read_id=self.read.id)

        data = {
            'silo_id': self.silo.id,
            'data': {
                'name': 'John Lennon',
                'age': 40,
                'city': 'Liverpool'
            }
        }

        request = self.factory.post('api/customform/%s/save_data' %
                                    self.silo.id, data=json.dumps(data),
                                    content_type='application/json')
        request.user = self.tola_user.user
        view = CustomFormViewSet.as_view({'post': 'save_data'})
        response = view(request)

        self.assertEqual(response.status_code, 200)

    def test_save_data_customform_missing_data_superuser(self):
        self.tola_user.user.is_staff = True
        self.tola_user.user.is_superuser = True
        self.tola_user.user.save()

        factories.LabelValueStore(silo_id=self.silo.id, read_id=self.read.id)

        data = {
            'data': {
                'name': 'John Lennon',
                'age': 40,
                'city': 'Liverpool'
            }
        }

        request = self.factory.post('api/customform/%s/save_data' %
                                    self.silo.id, data=json.dumps(data),
                                    content_type='application/json')
        request.user = self.tola_user.user
        view = CustomFormViewSet.as_view({'post': 'save_data'})
        response = view(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['detail'], 'Missing data.')

    def test_save_data_customform_normaluser(self):
        factories.LabelValueStore(silo_id=self.silo.id, read_id=self.read.id)

        data = {
            'silo_id': self.silo.id,
            'data': {
                'name': 'John Lennon',
                'age': 40,
                'city': 'Liverpool'
            }
        }

        request = self.factory.post('api/customform/%s/save_data' %
                                    self.silo.id, data=json.dumps(data),
                                    content_type='application/json')
        request.user = self.tola_user.user
        view = CustomFormViewSet.as_view({'post': 'save_data'})
        response = view(request)

        self.assertEqual(response.status_code, 200)

    def test_save_data_customform_no_data_normaluser(self):
        factories.LabelValueStore(silo_id=self.silo.id, read_id=self.read.id)

        data = {}

        request = self.factory.post('api/customform/%s/save_data' %
                                    self.silo.id, data=data)
        request.user = self.tola_user.user
        view = CustomFormViewSet.as_view({'post': 'save_data'})
        response = view(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['detail'], 'No data sent.')
