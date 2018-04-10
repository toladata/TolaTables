import logging
import json
import os
import urllib

from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist
from django.test import TestCase, override_settings
from django.urls import reverse
from oauth2client.client import AccessTokenCredentialsError

from rest_framework.test import APIRequestFactory
from mock import Mock, patch

import silo.gviews_v4 as gviews_v4
import factories
from silo.models import LabelValueStore
from tola.util import saveDataToSilo


class GetOauthFlowTest(TestCase):
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


class ExportToGSheetTest(TestCase):

    def _import_json(self, silo, read):
        filename = os.path.join(os.path.dirname(__file__),
                                'sample_data/moviesbyearnings2013.json')
        with open(filename, 'r') as f:
            data = json.load(f)
            saveDataToSilo(silo, data, read)

    def setUp(self):
        self.org = factories.Organization()
        self.tola_user = factories.TolaUser(organization=self.org)

        self.read = factories.Read(read_name="test_data",
                                   owner=self.tola_user.user)
        self.silo = factories.Silo(owner=self.tola_user.user,
                                   reads=[self.read])
        self._import_json(self.silo, self.read)

        self.factory = APIRequestFactory()

    def tearDown(self):
        # Have to remove the created lvs
        lvss = LabelValueStore.objects.filter(silo_id=self.silo.id)
        for lvs in lvss:
            lvs.delete()

    @patch('silo.gviews_v4.export_to_gsheet_helper')
    def test_export_to_gsheet(self, mock_gsheet_helper):
        spreadsheet_id = None
        query = {}
        cols = []

        mock_gsheet_helper.return_value = []

        url = reverse('export_new_gsheet', kwargs={'id': self.silo.pk}) + \
              '?&query='+str(query)+'&shown_cols='+str(cols)
        request = self.factory.get(url, follow=True)
        request.user = self.tola_user.user
        response = gviews_v4.export_to_gsheet(request, self.silo.pk)

        mock_gsheet_helper.assert_called_once_with(self.tola_user.user,
                                                   spreadsheet_id,
                                                   self.silo.pk, query,
                                                   cols)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('listSilos'))

    @patch('silo.gviews_v4.export_to_gsheet_helper')
    def test_export_to_gsheet_no_params(self, mock_gsheet_helper):
        spreadsheet_id = None
        query = {}
        expected_cols = ['cnt', 'grs', 'tit', 'rank', 'opn', 'yr']

        mock_gsheet_helper.return_value = []

        url = reverse('export_new_gsheet', kwargs={'id': self.silo.pk})
        request = self.factory.get(url, follow=True)
        request.user = self.tola_user.user
        response = gviews_v4.export_to_gsheet(request, self.silo.pk)

        mock_gsheet_helper.assert_called_once_with(self.tola_user.user,
                                                   spreadsheet_id,
                                                   self.silo.pk,
                                                   query,
                                                   expected_cols)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('listSilos'))

    @patch('silo.gviews_v4.export_to_gsheet_helper')
    def test_export_to_gsheet_wrong_column_type(self, mock_gsheet_helper):
        query = {}

        mock_gsheet_helper.return_value = []

        url = reverse('export_new_gsheet', kwargs={'id': self.silo.pk}) + \
              '?&query='+str(query)+'&shown_cols={"yr", "rank", "opn"}'

        with self.assertRaises(ValueError):
            request = self.factory.get(url, follow=True)
            request.user = self.tola_user.user
            gviews_v4.export_to_gsheet(request, self.silo.pk)

        mock_gsheet_helper.assert_not_called()

    @patch('silo.gviews_v4.export_to_gsheet_helper')
    def test_export_to_gsheet_wrong_query_type(self, mock_gsheet_helper):
        query = ["test"]

        mock_gsheet_helper.return_value = []

        url = reverse('export_new_gsheet', kwargs={'id': self.silo.pk}) + \
              '?&query='+str(query)+'&shown_cols=["yr", "rank", "opn"]'

        with self.assertRaises(ValueError):
            request = self.factory.get(url, follow=True)
            request.user = self.tola_user.user
            gviews_v4.export_to_gsheet(request, self.silo.pk)

        mock_gsheet_helper.assert_not_called()

    @patch('silo.gviews_v4.export_to_gsheet_helper')
    def test_export_to_gsheet_no_silo(self, mock_gsheet_helper):
        mock_gsheet_helper.return_value = []

        url = reverse('export_new_gsheet', kwargs={'id': 0})

        with self.assertRaises(ObjectDoesNotExist):
            request = self.factory.get(url, follow=True)
            request.user = self.tola_user.user
            gviews_v4.export_to_gsheet(request, 0)

        mock_gsheet_helper.assert_not_called()

    @patch('silo.gviews_v4.export_to_gsheet_helper')
    def test_export_to_gsheet_with_cols(self, mock_gsheet_helper):
        spreadsheet_id = None
        query = {}
        cols = ["yr", "rank", "opn"]
        mock_gsheet_helper.return_value = []

        url = reverse('export_new_gsheet', kwargs={'id': self.silo.pk}) + \
              '?&query='+str(query)+'&shown_cols=["yr", "rank", "opn"]'

        request = self.factory.get(url, follow=True)
        request.user = self.tola_user.user
        response = gviews_v4.export_to_gsheet(request, self.silo.pk)

        mock_gsheet_helper.assert_called_once_with(self.tola_user.user,
                                                   spreadsheet_id,
                                                   self.silo.pk,
                                                   query,
                                                   cols)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('listSilos'))

    @patch('silo.gviews_v4.export_to_gsheet_helper')
    def test_export_to_gsheet_with_query(self, mock_gsheet_helper):
        query = {"$or": [{"First_Name": {"$nin": ["1", 1.0, 1]}}]}
        expected_cols = []
        mock_gsheet_helper.return_value = []

        url = reverse('export_new_gsheet', kwargs={'id': self.silo.pk}) + \
              '?&query={"$or": [{"First_Name": {"$nin": ["1", 1.0, 1]}}]}' \
              '&shown_cols=[]'

        request = self.factory.get(url, follow=True)
        request.user = self.tola_user.user
        response = gviews_v4.export_to_gsheet(request, self.silo.pk)

        mock_gsheet_helper.assert_called_once_with(self.tola_user.user,
                                                   None,
                                                   self.silo.pk,
                                                   query,
                                                   expected_cols)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('listSilos'))

    @patch('silo.gviews_v4.export_to_gsheet_helper')
    def test_export_to_gsheet_redirect_uri(self, mock_gsheet_helper):
        spreadsheet_id = None
        query = {}
        expected_cols = ['cnt', 'grs', 'tit', 'rank', 'opn', 'yr']

        url = reverse('export_new_gsheet', kwargs={'id': self.silo.pk})
        request = self.factory.get(url, follow=True)
        setattr(request, 'session', {})

        mock_gsheet_helper.return_value = [{
            "level": 123,
            "msg": "Requires Google Authorization Setup",
            "redirect": "redirect_url",
            "redirect_uri_after_step2": True
        }]

        request.user = self.tola_user.user
        response = gviews_v4.export_to_gsheet(request, self.silo.pk)

        mock_gsheet_helper.assert_called_once_with(self.tola_user.user,
                                                   spreadsheet_id,
                                                   self.silo.pk,
                                                   query,
                                                   expected_cols)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "redirect_url")


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


class OAuthTest(TestCase):
    def setUp(self):
        logging.disable(logging.ERROR)
        
        self.org = factories.Organization()
        self.tola_user = factories.TolaUser(organization=self.org)
        self.factory = APIRequestFactory()
    
    def tearDown(self):
        logging.disable(logging.NOTSET)

    def test_store_oauth2_credential_method_notallowed(self):
        request = self.factory.get('')
        request.user = self.tola_user.user
        response = gviews_v4.store_oauth2_credential(request)

        self.assertEqual(response.status_code, 405)
        self.assertEqual(response['Allow'], 'POST, OPTIONS')

    @patch('silo.gviews_v4.OAuth2Credentials')
    @patch('silo.gviews_v4.Storage')
    def test_store_oauth2_credential_success_minimal(self, mock_storage,
                                              mock_oauthcred):
        mock_storage.return_value = Mock()
        mock_oauthcred.return_value = Mock()
        data = {
            'access_token': 'mytestaccesstoken',
        }
        request = self.factory.post('', data=data)
        request.user = self.tola_user.user
        response = gviews_v4.store_oauth2_credential(request)
        content = json.loads(response.content)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(content['detail'],
                         'The credential was successfully saved.')

    @patch('silo.gviews_v4.OAuth2Credentials')
    @patch('silo.gviews_v4.Storage')
    def test_store_oauth2_credential_success_full(self, mock_storage,
                                              mock_oauthcred):
        mock_storage.return_value = Mock()
        mock_oauthcred.return_value = Mock()
        data = {
            'access_token': 'mytestaccesstoken',
            'refresh_token': 'myrefreshtoken',
            'expires_in': 3573,
        }
        request = self.factory.post('', data=data)
        request.user = self.tola_user.user
        response = gviews_v4.store_oauth2_credential(request)
        content = json.loads(response.content)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(content['detail'],
                         'The credential was successfully saved.')

    def test_store_oauth2_credential_no_access_token(self):
        request = self.factory.post('', {})
        request.user = self.tola_user.user

        with self.assertRaises(AccessTokenCredentialsError):
            gviews_v4.store_oauth2_credential(request)
