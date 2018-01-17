from django.test import TestCase

import factories
from tola import auth_pipeline
from silo.models import TolaUser


class OAuthTest(TestCase):
    """
    Test cases for OAuth Provider interface
    """

    def setUp(self):
        self.tola_user = factories.TolaUser()
        self.org = factories.Organization()
        self.country = factories.Country()

    def test_user_to_tola_with_tola_user_data(self):
        response = {
            'tola_user': {
                'tola_user_uuid': '13dac835-3860-4d9d-807e-d36a3c106057',
                'name': 'John Lennon',
                'employee_number': None,
                'title': 'mr',
                'privacy_disclaimer_accepted': True,
            },
            'organization': {
                'name': self.org.name,
                'url': '',
                'industry': '',
                'sector': '',
                'organization_uuid': self.org.organization_uuid
            }
        }

        user = factories.User(first_name='John', last_name='Lennon')
        auth_pipeline.user_to_tola(None, user, response)
        tola_user = TolaUser.objects.get(name='John Lennon')

        self.assertEqual(tola_user.name, response['tola_user']['name'])
        self.assertEqual(tola_user.organization.name, self.org.name)
