import json
from django.test import TestCase
from rest_framework.test import APIRequestFactory

import factories
from silo.tests import MongoTestCase
from silo.api import CustomFormViewSet
from silo.models import Silo


class CustomFormViewsTest(TestCase, MongoTestCase):
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


class CustomFormCreateViewsTest(TestCase, MongoTestCase):
    def setUp(self):
        factories.ReadType(read_type='CustomForm')
        self.tola_user = factories.TolaUser()
        self.factory = APIRequestFactory()

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


class CustomFormUpdateViewsTest(TestCase):
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
