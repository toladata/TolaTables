import logging
import json
import os
import urllib

from django.contrib import messages
from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist
from django.test import TestCase, override_settings
from django.urls import reverse
from oauth2client.client import (AccessTokenCredentialsError,
                                 HttpAccessTokenRefreshError,
                                 OAuth2Credentials)

from rest_framework.test import APIRequestFactory
from mock import Mock, patch

import silo.gviews_v4 as gviews_v4
import factories
from tola.util import save_data_to_silo
from silo.models import LabelValueStore, Silo


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
            save_data_to_silo(silo, data, read)

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

        url = reverse('export_new_gsheet', kwargs={'id': self.silo.pk})
        url = url + '?&query='+str(query)+'&shown_cols='+str(cols)

        request = self.factory.get(url, follow=True)
        request.user = self.tola_user.user
        response = gviews_v4.export_to_gsheet(request, self.silo.pk)
        cols.append('_id')

        mock_gsheet_helper.assert_called_once_with(self.tola_user.user,
                                                   spreadsheet_id,
                                                   self.silo.pk, query,
                                                   cols)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('list_silos'))

    @patch('silo.gviews_v4.export_to_gsheet_helper')
    def test_export_to_gsheet_no_params(self, mock_gsheet_helper):
        spreadsheet_id = None
        query = {}
        expected_cols = ['_id', 'cnt', 'grs', 'tit', 'rank', 'opn', 'yr']

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
        self.assertEqual(response.url, reverse('list_silos'))

    @patch('silo.gviews_v4.export_to_gsheet_helper')
    def test_export_to_gsheet_wrong_column_type(self, mock_gsheet_helper):
        query = {}

        mock_gsheet_helper.return_value = []

        url = reverse('export_new_gsheet', kwargs={'id': self.silo.pk})
        url = url + '?&query='+str(query)+'&shown_cols={"yr", "rank", "opn"}'

        with self.assertRaises(ValueError):
            request = self.factory.get(url, follow=True)
            request.user = self.tola_user.user
            gviews_v4.export_to_gsheet(request, self.silo.pk)

        mock_gsheet_helper.assert_not_called()

    @patch('silo.gviews_v4.export_to_gsheet_helper')
    def test_export_to_gsheet_wrong_query_type(self, mock_gsheet_helper):
        query = ["test"]

        mock_gsheet_helper.return_value = []

        url = reverse('export_new_gsheet', kwargs={'id': self.silo.pk})
        url = url + '?&query='+str(query)+'&shown_cols=["yr", "rank", "opn"]'

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
        cols = ["_id", "yr", "rank", "opn"]
        mock_gsheet_helper.return_value = []

        url = reverse('export_new_gsheet', kwargs={'id': self.silo.pk})
        url = url + '?&query='+str(query)+'&shown_cols=["yr", ' \
                                          '"rank", "opn"]'

        request = self.factory.get(url, follow=True)
        request.user = self.tola_user.user
        response = gviews_v4.export_to_gsheet(request, self.silo.pk)

        mock_gsheet_helper.assert_called_once_with(self.tola_user.user,
                                                   spreadsheet_id,
                                                   self.silo.pk,
                                                   query,
                                                   cols)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('list_silos'))

    @patch('silo.gviews_v4.export_to_gsheet_helper')
    def test_export_to_gsheet_with_query(self, mock_gsheet_helper):
        query = {"$or": [{"First_Name": {"$nin": ["1", 1.0, 1]}}]}
        expected_cols = ['_id']
        mock_gsheet_helper.return_value = []

        url = reverse('export_new_gsheet', kwargs={'id': self.silo.pk})
        url = url + '?&query={"$or": [{"First_Name": {"$nin": ["1", 1.0, 1]' \
                    '}}]}&shown_cols=[]'

        request = self.factory.get(url, follow=True)
        request.user = self.tola_user.user
        response = gviews_v4.export_to_gsheet(request, self.silo.pk)

        mock_gsheet_helper.assert_called_once_with(self.tola_user.user,
                                                   None,
                                                   self.silo.pk,
                                                   query,
                                                   expected_cols)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('list_silos'))

    @patch('silo.gviews_v4.export_to_gsheet_helper')
    def test_export_to_gsheet_redirect_uri(self, mock_gsheet_helper):
        spreadsheet_id = None
        query = {}
        expected_cols = ['_id', 'cnt', 'grs', 'tit', 'rank', 'opn', 'yr']

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
    def test_store_oauth2_credential_success_minimal(
            self, mock_storage, mock_oauthcred):
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
    def test_store_oauth2_credential_success_full(
            self, mock_storage, mock_oauthcred):
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


class ImportFromGSheetHelperTest(TestCase):
    def setUp(self):
        self.org = factories.Organization()
        self.tola_user = factories.TolaUser(organization=self.org)
        self.read = factories.Read(read_name='Test Read')
        self.silo = factories.Silo(reads=[self.read])

    def tearDown(self):
        # Have to remove the created lvs
        lvss = LabelValueStore.objects.filter(silo_id=self.silo.id)
        for lvs in lvss:
            lvs.delete()

    @patch('silo.gviews_v4._get_or_create_read')
    @patch('silo.gviews_v4._fetch_data_gsheet')
    @patch('silo.gviews_v4._get_gsheet_metadata')
    @patch('silo.gviews_v4._get_authorized_service')
    @patch('silo.gviews_v4._get_credential_object')
    def test_import_from_gsheet_helper_minimal(
            self, mock_get_credential_obj, mock_get_authorized_service,
            mock_get_gsheet_metadata, mock_fetch_data_gsheet,
            mock_get_or_create_read):
        data = [
            ['Name', 'Age'],
            ['John', '40'],
        ]
        expected_result = [
            {'silo_id': self.silo.id},
            {'msg': 'Operation successful', 'level': messages.SUCCESS}
        ]

        mock_get_credential_obj.return_value = Mock(OAuth2Credentials)
        mock_get_authorized_service.return_value = Mock()
        mock_get_gsheet_metadata.return_value = (Mock(), None)
        mock_fetch_data_gsheet.return_value = (data, None)
        mock_get_or_create_read.return_value = self.read

        result = gviews_v4.import_from_gsheet_helper(
            self.tola_user.user, self.silo.id, self.silo.name, 1234)

        self.silo = Silo.objects.get(id=self.silo.id)
        self.assertEqual(result, expected_result)

        lvss = LabelValueStore.objects.filter(silo_id=self.silo.id)
        for lvs in lvss:
            lvs_json = json.loads(lvs.to_json())
            self.assertEqual(lvs_json.get('Name'), 'John')
            self.assertEqual(lvs_json.get('Age'), 40)

    @patch('silo.gviews_v4._get_gsheet_metadata')
    @patch('silo.gviews_v4._get_authorized_service')
    @patch('silo.gviews_v4._get_credential_object')
    def test_import_from_gsheet_helper_sheet_not_selected(
            self, mock_get_credential_obj, mock_get_authorized_service,
            mock_get_gsheet_metadata):
        external_msg = {
            'level': messages.ERROR,
            'msg': 'Error: GSheet is not selected.'
        }
        expected_result = [
            {
                'level': messages.ERROR,
                'msg': 'A Google Spreadsheet is not selected to '
                       'import data from.',
                'redirect': reverse('index')
            },
            {'silo_id': self.silo.id},
            external_msg
        ]

        mock_get_credential_obj.return_value = Mock(OAuth2Credentials)
        mock_get_authorized_service.return_value = Mock()
        mock_get_gsheet_metadata.return_value = (None, external_msg)

        result = gviews_v4.import_from_gsheet_helper(
            self.tola_user.user, self.silo.id, self.silo.name, None)

        self.assertEqual(result, expected_result)

    @patch('silo.gviews_v4._get_gsheet_metadata')
    @patch('silo.gviews_v4._get_authorized_service')
    @patch('silo.gviews_v4._get_credential_object')
    def test_import_from_gsheet_helper_sheet_refresh_credential(
            self, mock_get_credential_obj, mock_get_authorized_service,
            mock_get_gsheet_metadata):
        mock_credential_obj = Mock(OAuth2Credentials)
        external_msg = {
            'credential': [mock_credential_obj],
        }

        mock_get_credential_obj.return_value = Mock(OAuth2Credentials)
        mock_get_authorized_service.return_value = Mock()
        mock_get_gsheet_metadata.return_value = (None, external_msg)

        result = gviews_v4.import_from_gsheet_helper(
            self.tola_user.user, self.silo.id, self.silo.name, None)

        self.assertEqual(result, [mock_credential_obj])

    @patch('silo.gviews_v4._get_credential_object')
    def test_import_from_gsheet_helper_wrong_creadential(
            self, mock_get_credential_obj):
        msg = {
            'msg': 'Requires Google Authorization Setup',
            'redirect': 'url',
            'redirect_uri_after_step2': True,
            'level': messages.ERROR
        }
        mock_get_credential_obj.return_value = msg

        result = gviews_v4.import_from_gsheet_helper(
            self.tola_user.user, self.silo.id, self.silo.name, 1234)
        self.assertEqual(result, [msg])

    @patch('silo.gviews_v4._get_or_create_read')
    @patch('silo.gviews_v4._fetch_data_gsheet')
    @patch('silo.gviews_v4._get_gsheet_metadata')
    @patch('silo.gviews_v4._get_authorized_service')
    @patch('silo.gviews_v4._get_credential_object')
    def test_import_from_gsheet_helper_error_fetching(
            self, mock_get_credential_obj, mock_get_authorized_service,
            mock_get_gsheet_metadata, mock_fetch_data_gsheet,
            mock_get_or_create_read):
        external_msg = {
            'level': messages.ERROR,
            'msg': 'Something went wrong 22: error',
            'redirect': None
        }
        expected_result = [
            {'silo_id': self.silo.id},
            external_msg
        ]

        mock_get_credential_obj.return_value = Mock(OAuth2Credentials)
        mock_get_authorized_service.return_value = Mock()
        mock_get_gsheet_metadata.return_value = (Mock(), None)
        mock_fetch_data_gsheet.return_value = (None, external_msg)
        mock_get_or_create_read.return_value = self.read

        result = gviews_v4.import_from_gsheet_helper(
            self.tola_user.user, self.silo.id, self.silo.name, 1234)
        self.assertEqual(result, expected_result)

    @patch('silo.gviews_v4._get_or_create_read')
    @patch('silo.gviews_v4._fetch_data_gsheet')
    @patch('silo.gviews_v4._get_gsheet_metadata')
    @patch('silo.gviews_v4._get_authorized_service')
    @patch('silo.gviews_v4._get_credential_object')
    def test_import_from_gsheet_helper_unique_fields(
            self, mock_get_credential_obj, mock_get_authorized_service,
            mock_get_gsheet_metadata, mock_fetch_data_gsheet,
            mock_get_or_create_read):
        lvs = LabelValueStore()
        lvs.silo_id = self.silo.id
        lvs.save()
        data = [{
            'First.Name': 'John',
            'Last.Name': 'Doe',
            'E-mail': 'john@example.org',
        }, {
            'First.Name': 'Bob',
            'Last.Name': 'Smith',
            'E-mail': 'bob@example.org',
        }]

        save_data_to_silo(self.silo, data, self.read)
        factories.UniqueFields(name='E-mail', silo=self.silo)

        data = [
            ['First.Name', 'Last.Name', 'E-mail'],
            ['John', 'Lennon', 'john@example.org'],
        ]
        expected_result = [
            {'silo_id': self.silo.id},
            {'msg': 'Operation successful', 'level': messages.SUCCESS}
        ]

        mock_get_credential_obj.return_value = Mock(OAuth2Credentials)
        mock_get_authorized_service.return_value = Mock()
        mock_get_gsheet_metadata.return_value = (Mock(), None)
        mock_fetch_data_gsheet.return_value = (data, None)
        mock_get_or_create_read.return_value = self.read

        result = gviews_v4.import_from_gsheet_helper(
            self.tola_user.user, self.silo.id, self.silo.name, 1234)
        self.assertEqual(result, expected_result)

        lvss = LabelValueStore.objects.filter(silo_id=self.silo.id)
        count = 0
        for lvs in lvss:
            lvs_json = json.loads(lvs.to_json())
            if lvs_json.get('First_Name') == 'John':
                self.assertEqual(lvs_json.get('Last_Name'), 'Lennon')
                count += 1

        self.assertEqual(count, 1)

    @patch('silo.gviews_v4._get_or_create_read')
    @patch('silo.gviews_v4._fetch_data_gsheet')
    @patch('silo.gviews_v4._get_gsheet_metadata')
    @patch('silo.gviews_v4._get_authorized_service')
    @patch('silo.gviews_v4._get_credential_object')
    def test_import_from_gsheet_helper_unique_fields_no_lvs(
            self, mock_get_credential_obj, mock_get_authorized_service,
            mock_get_gsheet_metadata, mock_fetch_data_gsheet,
            mock_get_or_create_read):
        data = [
            ['Name', 'Last.Name', 'E-mail'],
            ['John', 'Doe', 'john@example.org'],
            ['Bob', 'Smith', 'bob@example.org'],
        ]
        expected_result = [
            {'silo_id': self.silo.id},
            {'msg': 'Operation successful', 'level': messages.SUCCESS}
        ]

        mock_get_credential_obj.return_value = Mock(OAuth2Credentials)
        mock_get_authorized_service.return_value = Mock()
        mock_get_gsheet_metadata.return_value = (Mock(), None)
        mock_fetch_data_gsheet.return_value = (data, None)
        mock_get_or_create_read.return_value = self.read

        result = gviews_v4.import_from_gsheet_helper(
            self.tola_user.user, self.silo.id, self.silo.name, 1234)
        self.assertEqual(result, expected_result)

    @patch('silo.gviews_v4._get_or_create_read')
    @patch('silo.gviews_v4._fetch_data_gsheet')
    @patch('silo.gviews_v4._get_gsheet_metadata')
    @patch('silo.gviews_v4._get_authorized_service')
    @patch('silo.gviews_v4._get_credential_object')
    def test_import_from_gsheet_helper_skipped_rows(
            self, mock_get_credential_obj, mock_get_authorized_service,
            mock_get_gsheet_metadata, mock_fetch_data_gsheet,
            mock_get_or_create_read):
        lvs = LabelValueStore()
        lvs.silo_id = self.silo.id
        lvs.save()
        data = [{
            'First.Name': 'John',
            'Last.Name': 'Doe',
            'E-mail': 'john@example.org',
        }, {
            'First.Name': 'Bob',
            'Last.Name': 'Smith',
            'E-mail': 'bob@example.org',
        }]
        save_data_to_silo(self.silo, data, self.read)

        # create multiple lvs
        lvs = LabelValueStore()
        lvs.silo_id = self.silo.id
        lvs.save()
        save_data_to_silo(self.silo, data, self.read)

        factories.UniqueFields(name='E-mail', silo=self.silo)
        data = [
            ['First.Name', 'Last.Name', 'E-mail'],
            ['John', 'Lennon', 'john@example.org'],
        ]
        expected_result = [
            {'silo_id': self.silo.id},
            {'msg': 'Skipped updating/adding records where '
                    'E-mail=john@example.org,silo_id=1 because there are '
                    'already multiple records.', 'level': messages.WARNING},
            {'msg': 'Operation successful', 'level': messages.SUCCESS}]

        mock_get_credential_obj.return_value = Mock(OAuth2Credentials)
        mock_get_authorized_service.return_value = Mock()
        mock_get_gsheet_metadata.return_value = (Mock(), None)
        mock_fetch_data_gsheet.return_value = (data, None)
        mock_get_or_create_read.return_value = self.read

        result = gviews_v4.import_from_gsheet_helper(
            self.tola_user.user, self.silo.id, self.silo.name, 1234,
            partialcomplete=True)
        self.assertEqual(result, ([], expected_result))

    @patch('silo.gviews_v4._get_or_create_read')
    @patch('silo.gviews_v4._fetch_data_gsheet')
    @patch('silo.gviews_v4._get_gsheet_metadata')
    @patch('silo.gviews_v4._get_authorized_service')
    @patch('silo.gviews_v4._get_credential_object')
    def test_import_from_gsheet_helper_with_integer_unique_fields(
            self, mock_get_credential_obj, mock_get_authorized_service,
            mock_get_gsheet_metadata, mock_fetch_data_gsheet,
            mock_get_or_create_read):
        '''Import function should update existing data when it got new data with
        same unique field'''
        lvs = LabelValueStore()
        lvs.silo_id = self.silo.id
        lvs.save()
        data = [{
            'First.Name': 'John',
            'Last.Name': 'Doe',
            'Number': 1,
        }, {
            'First.Name': 'Bob',
            'Last.Name': 'Smith',
            'Number': 2,
        }]

        save_data_to_silo(self.silo, data, self.read)
        factories.UniqueFields(name='Number', silo=self.silo)

        data = [
            ['First.Name', 'Last.Name', 'Number'],
            ['John', 'Lennon', 1],
        ]
        expected_result = [
            {'silo_id': self.silo.id},
            {'msg': 'Operation successful', 'level': messages.SUCCESS}
        ]

        mock_get_credential_obj.return_value = Mock(OAuth2Credentials)
        mock_get_authorized_service.return_value = Mock()
        mock_get_gsheet_metadata.return_value = (Mock(), None)
        mock_fetch_data_gsheet.return_value = (data, None)
        mock_get_or_create_read.return_value = self.read

        result = gviews_v4.import_from_gsheet_helper(
            self.tola_user.user, self.silo.id, self.silo.name, 1234)
        self.assertEqual(result, expected_result)

        lvss = LabelValueStore.objects.filter(silo_id=self.silo.id)
        count = 0
        for lvs in lvss:
            lvs_json = json.loads(lvs.to_json())
            if lvs_json.get('First_Name') == 'John':
                self.assertEqual(lvs_json.get('Last_Name'), 'Lennon')
                count += 1

        self.assertEqual(count, 1)
        self.assertEqual(lvss.count(), 3)


class GetGSheetMetaDataTest(TestCase):
    def setUp(self):
        self.org = factories.Organization()
        self.tola_user = factories.TolaUser(organization=self.org)
        self.read = factories.Read(read_name='Test Read')

    @patch('silo.gviews_v4._get_authorized_service')
    def test_get_gsheet_metadata_success(self, mock_get_authorized_service):
        mock_service_execute = Mock()
        mock_credential_obj = Mock(OAuth2Credentials)
        mock_get_authorized_service.return_value = Mock()
        gviews_v4._get_authorized_service().spreadsheets().\
            get().execute.return_value = mock_service_execute

        spreadsheet, error = gviews_v4._get_gsheet_metadata(
            mock_credential_obj, 1234, self.tola_user.user)

        self.assertIsNone(error)
        self.assertEqual(spreadsheet, mock_service_execute)

    @patch('silo.gviews_v4._get_credential_object')
    def test_get_gsheet_metadata_refresh_error(self, mock_get_credential_obj):
        refresh_exception = HttpAccessTokenRefreshError()
        mock_credential_obj = Mock(OAuth2Credentials)
        mock_new_credential_obj = Mock(OAuth2Credentials)

        mock_service_execute = Mock(side_effect=refresh_exception)
        mock_get_credential_obj.return_value = mock_new_credential_obj
        gviews_v4._get_authorized_service = Mock()
        gviews_v4._get_authorized_service().spreadsheets = mock_service_execute

        spreadsheet, error = gviews_v4._get_gsheet_metadata(
            mock_credential_obj, 1234, self.tola_user.user)

        expected_error = {
            'credential': [mock_new_credential_obj]
        }

        self.assertIsNotNone(error)
        self.assertIsNone(spreadsheet)
        self.assertEqual(error, expected_error)

    def test_get_gsheet_metadata_exception(self):
        exception = Exception()
        exception.__setattr__(
            'content', '{"error": {"status": "ERROR", "message": "Msg Test"}}')

        mock_credential_obj = Mock(OAuth2Credentials)
        mock_service_execute = Mock(side_effect=exception)
        gviews_v4._get_authorized_service = Mock()
        gviews_v4._get_authorized_service().spreadsheets = mock_service_execute

        spreadsheet, error = gviews_v4._get_gsheet_metadata(
            mock_credential_obj, 1234, self.tola_user.user)

        expected_error = {
            'msg': 'ERROR: Msg Test',
            'level': messages.ERROR
        }

        self.assertIsNotNone(error)
        self.assertIsNone(spreadsheet)
        self.assertEqual(error, expected_error)


class FetchDataGSheetTest(TestCase):
    def setUp(self):
        logging.disable(logging.ERROR)
        self.org = factories.Organization()
        self.tola_user = factories.TolaUser(organization=self.org)
        self.read = factories.Read(read_name='Test Read')
        self.silo = factories.Silo(reads=[self.read])

    def tearDown(self):
        logging.disable(logging.NOTSET)

    @patch('silo.gviews_v4._get_authorized_service')
    def test_fetch_data_gsheet_success(self, mock_get_authorized_service):
        data = {
            'name': 'John',
            'age': 40
        }
        mock_credential_obj = Mock(OAuth2Credentials)
        mock_get_authorized_service.return_value = Mock()
        gviews_v4._get_authorized_service().spreadsheets().values().get().\
            execute().get.return_value = data

        values, error = gviews_v4._fetch_data_gsheet(
            mock_credential_obj, 1234, 'Syria Security Incidences')

        self.assertIsNone(error)
        self.assertEqual(values, data)

    def test_fetch_data_gsheet_exception(self):
        exception = Exception('Deu ruim')

        mock_credential_obj = Mock(OAuth2Credentials)
        mock_service_execute = Mock(side_effect=exception)
        gviews_v4._get_authorized_service = Mock()
        gviews_v4._get_authorized_service().spreadsheets = mock_service_execute

        values, error = gviews_v4._fetch_data_gsheet(
            mock_credential_obj, 1234, 'Syria Security Incidences')

        expected_error = {
            'level': messages.ERROR,
            'msg': 'Something went wrong 22: Deu ruim',
            'redirect': None
        }

        self.assertIsNotNone(error)
        self.assertIsNone(values)
        self.assertEqual(error, expected_error)


class ConvertGSheetDataTest(TestCase):
    def test_convert_gsheet_data_success(self):
        headers = ['Name', 'Age']
        values = [
            ['Paul', '75'],
            ['John', '40'],
        ]

        expected_data = [{'Age': '75', 'Name': 'Paul'},
                         {'Age': '40', 'Name': 'John'}]

        data = gviews_v4._convert_gsheet_data(headers, values)
        self.assertEqual(expected_data, data)

    def test_convert_gsheet_data_longer_values_than_header(self):
        headers = ['Name', 'Age']
        values = [
            ['Paul', '75', 'McCartney'],
            ['John', '40', 'Lennon'],
        ]

        expected_data = [{'Age': '75', 'Name': 'Paul'},
                         {'Age': '40', 'Name': 'John'}]

        data = gviews_v4._convert_gsheet_data(headers, values)
        self.assertEqual(expected_data, data)

    def test_convert_gsheet_data_longer_header_than_values(self):
        headers = ['Name', 'Age', 'Surname']
        values = [
            ['Paul', '75'],
            ['John', '40'],
        ]

        expected_data = [{'Age': '75', 'Name': 'Paul'},
                         {'Age': '40', 'Name': 'John'}]

        data = gviews_v4._convert_gsheet_data(headers, values)
        self.assertEqual(expected_data, data)

    def test_convert_gsheet_data_empty_header(self):
        values = [
            ['Paul', '75'],
            ['John', '40'],
        ]

        data = gviews_v4._convert_gsheet_data(list(), values)
        self.assertEqual(list(), data)

    def test_convert_gsheet_data_empty_values(self):
        headers = ['Name', 'Age']

        data = gviews_v4._convert_gsheet_data(headers, list())
        self.assertEqual(list(), data)

    def test_convert_gsheet_data_header_error(self):
        headers = [['Name', 'Age']]
        values = [
            ['Paul', '75'],
            ['John', '40'],
        ]

        with self.assertRaises(TypeError):
            gviews_v4._convert_gsheet_data(headers, values)

    def test_convert_gsheet_data_values_error(self):
        headers = ['Name', 'Age']
        values = ['Paul', 75, 'John', 40]

        with self.assertRaises(TypeError):
            gviews_v4._convert_gsheet_data(headers, values)
