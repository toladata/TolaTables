import json
from django.test import TestCase, RequestFactory

import factories
from silo.tests import MongoTestCase
from silo.views import create_customform


class ReadTest(TestCase, MongoTestCase):
    def setUp(self):
        factories.ReadType()
        self.tola_user = factories.TolaUser(user=factories.User())
        self.factory = RequestFactory()

    def test_create_customform_superuser(self):
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
            'is_public': True,
            'level1_uuid': wflvl1.level1_uuid
        }

        request = self.factory.post(
            '/create_customform/', data=json.dumps(data),
            content_type='application/json')
        request.user = self.tola_user.user
        request._dont_enforce_csrf_checks = True
        response = create_customform(request)

        self.assertEqual(response.status_code, 201)
