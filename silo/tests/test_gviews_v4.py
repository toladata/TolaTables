import json
import os
from unittest import TestCase as PythonTestCase
import urllib

from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, override_settings
from django.urls import reverse
from mock import patch

import silo.gviews_v4 as gviews_v4


class GetOauthFlowTest(PythonTestCase):
    @override_settings(GOOGLE_OAUTH_CLIENT_ID=None,
                       GOOGLE_OAUTH_CLIENT_SECRET=None)
    def test_get_oauth_flow_no_conf(self):
        with self.assertRaises(ImproperlyConfigured):
            gviews_v4._get_oauth_flow()

    @override_settings(GOOGLE_OAUTH_CLIENT_ID=None,
                       GOOGLE_OAUTH_CLIENT_SECRET='pass')
    def test_get_oauth_flow_no_conf_client_var(self):
        with self.assertRaises(ImproperlyConfigured):
            gviews_v4._get_oauth_flow()

    @override_settings(GOOGLE_OAUTH_CLIENT_ID='123',
                       GOOGLE_OAUTH_CLIENT_SECRET=None)
    def test_get_oauth_flow_no_conf_secret_var(self):
        with self.assertRaises(ImproperlyConfigured):
            gviews_v4._get_oauth_flow()

    @override_settings(GOOGLE_OAUTH_CLIENT_ID='123',
                       GOOGLE_OAUTH_CLIENT_SECRET='pass',
                       GOOGLE_REDIRECT_URL='url')
    def test_get_oauth_flow_with_conf(self):
        flow = gviews_v4._get_oauth_flow()
        self.assertEqual(flow.client_id, '123')
        self.assertEqual(flow.client_secret, 'pass')
        self.assertEqual(flow.scope, gviews_v4.SCOPE)
        self.assertEqual(flow.redirect_uri, 'url')

    @override_settings(GOOGLE_OAUTH_CLIENT_ID=None,
                       GOOGLE_OAUTH_CLIENT_SECRET=None,
                       GOOGLE_REDIRECT_URL='url')
    def test_get_oauth_flow_with_file(self):
        gviews_v4.CLIENT_SECRETS_FILENAME = os.path.join(
            'tests', 'client_secrets_test.json')
        flow = gviews_v4._get_oauth_flow()
        self.assertEqual(flow.client_id, '123.apps.googleusercontent.com')
        self.assertEqual(flow.client_secret, 'pass')
        self.assertEqual(flow.scope, gviews_v4.SCOPE)
        self.assertEqual(flow.redirect_uri, 'url')


class GetSheetsFromGoogleTest(TestCase):
    def setUp(self):
        credentials = {
            'username': 'johnlennon',
            'password': 'yok0',
        }
        self.user = User.objects.create_user(**credentials)
        self.client.login(**credentials)

    @patch('silo.gviews_v4._get_credential_object')
    def test_get_sheets_from_google_spreadsheet(self, mock_get_credential_obj):
        mock_get_credential_obj.return_value = {}
        url = reverse('get_sheets') + '?spreadsheet_id=ID'
        self.client.get(url)
        mock_get_credential_obj.assert_called_once_with(self.user)


class GetCredentialObjectTest(TestCase):
    @override_settings(GOOGLE_OAUTH_CLIENT_ID='123',
                       GOOGLE_OAUTH_CLIENT_SECRET='pass',
                       GOOGLE_REDIRECT_URL='url')
    def test_get_credential_object_non_existing(self):
        user = User.objects.create_user(username='johnlennon', password='yok0')
        credential = gviews_v4._get_credential_object(user)
        self.assertIn('https://accounts.google.com/o/oauth2/v2/auth',
                      credential['redirect'])
        self.assertIn('redirect_uri=url', credential['redirect'])
        self.assertIn('approval_prompt=force', credential['redirect'])
        self.assertIn('access_type=offline', credential['redirect'])
        scope_url = urllib.quote_plus(gviews_v4.SCOPE)
        self.assertIn('scope={}'.format(scope_url), credential['redirect'])
