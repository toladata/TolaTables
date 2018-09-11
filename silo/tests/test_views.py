# -*- coding: utf-8 -*-
from django.test import TestCase, override_settings, Client, RequestFactory
from django.urls import reverse

from rest_framework.test import APIRequestFactory

from silo.tests import MongoTestCase
from silo.api import CustomFormViewSet, PublicSiloViewSet
from silo.models import LabelValueStore, Silo, Tag, ReadType

from mock import Mock, patch
from pymongo.errors import WriteError

import json
import random
import uuid
import factories
from silo import views
from tola import util, MASTER_BRANCH

from social_django.models import UserSocialAuth
from django.contrib.messages.storage.fallback import FallbackStorage


class IndexViewTest(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        factories.TolaSites()
        factories.ReadType.create_batch(4)

    def test_index_context_data(self):
        user_stranger = factories.User(username='stranger')
        factories.Silo(owner=user_stranger, name='open', public=True)

        user = factories.User()
        factories.Silo(owner=user, name='pub_1', public=True)
        factories.Silo(owner=user, name='pub_2', public=True)
        factories.Silo(owner=user, name='priv_1', public=False)
        factories.Silo(owner=user, name='shared_1', public=False,
                       shared=[user_stranger])

        request = self.factory.get('', follow=True)
        request.user = user
        context = views.IndexView()._get_context_data(request)
        self.assertEqual(context['site_name'], 'Track')
        self.assertEqual(len(context['silos_user']), 4)
        self.assertEqual(context['silos_user'][0].name, 'pub_1')
        self.assertEqual(context['silos_user'][1].name, 'pub_2')
        self.assertEqual(context['silos_user'][2].name, 'priv_1')
        self.assertEqual(context['silos_user_public_total'], 2)
        self.assertEqual(context['silos_user_shared_total'], 1)
        self.assertEqual(context['silos_public'][0].name, 'open')
        self.assertEqual(len(context['silos_public']), 1)
        self.assertEqual(len(context['readtypes']), 7)
        self.assertEqual(sorted(list(context['readtypes'])),
                         [u'CSV', u'CommCare', u'CustomForm', u'GSheet Import',
                          u'JSON', u'ONA', u'OneDrive'])
        # self.assertEqual(list(context['tags']),
        #                  [{'name': u'security', 'times_tagged': 4},
        #                   {'name': u'report', 'times_tagged': 4}]),
        self.assertEqual(context['site_name'], 'Track'),

    """
    Index removed for logged in user with re-direct to silo list
    remove or rewrite test GWL 9-1-2017
    def test_index_template_authenticated_user(self):
        user_stranger = factories.User(username='stranger')
        factories.Silo(owner=user_stranger, name='open', public=True)

        user = factories.User()
        silo_pub_1 = factories.Silo(owner=user, name='pub_1', public=True)
        silo_pub_2 = factories.Silo(owner=user, name='pub_2', public=True)
        silo_priv_1 = factories.Silo(owner=user, name='priv_1', public=False)
        silo_shared_1 = factories.Silo(owner=user, name='shared_1',
                                       public=False, shared=[user_stranger])

        request = self.factory.get('', follow=True)
        request.user = user
        view = views.IndexView.as_view()
        response = view(request)
        template_content = response.content

        match = '<a href="{}">{}</a>'.format(
            reverse('silo_detail', kwargs={'silo_id': silo_pub_1.pk}),
            silo_pub_1.name)
        self.assertEqual(template_content.count(match), 1)

        match = '<a href="{}">{}</a>'.format(
            reverse('silo_detail', kwargs={'silo_id': silo_pub_2.pk}),
            silo_pub_2.name)
        self.assertEqual(template_content.count(match), 1)

        match = '<a href="{}">{}</a>'.format(
            reverse('silo_detail', kwargs={'silo_id': silo_priv_1.pk}),
            silo_priv_1.name)
        self.assertEqual(template_content.count(match), 1)

        match = '<a href="{}">{}</a>'.format(
            reverse('silo_detail', kwargs={'silo_id': silo_shared_1.pk}),
            silo_shared_1.name)
        self.assertEqual(template_content.count(match), 1)

    def test_index_get_authenticated(self):
        silo = factories.Silo()
        user = silo.owner

        request = self.factory.get('', follow=True)
        request.user = user
        response = views.IndexView.as_view()(request)
        self.assertEqual(response.status_code, 302)
    """
    @override_settings(TOLA_ACTIVITY_API_URL='https://api.toladata.io')
    @override_settings(ACTIVITY_URL='https://toladata.io')
    def test_index_get_unauthenticated(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('login/tola', response.url)

    @override_settings(TOLA_ACTIVITY_API_URL=None)
    @override_settings(ACTIVITY_URL='https://toladata.io')
    def test_index_get_unauthenticated_no_activity_api_url(self):
        response = self.client.get('')
        self.assertEqual(response.status_code, 302)
        self.assertIn('login/tola', response.url)


class ExportViewsTest(TestCase, MongoTestCase):
    def setUp(self):
        factories.ReadType(read_type='CustomForm')
        self.tola_user = factories.TolaUser()
        self.factory = APIRequestFactory()

    def test_export_csv(self):
        self.tola_user.user.is_staff = True
        self.tola_user.user.is_superuser = True
        self.tola_user.user.save()

        # Create the Silo to store the data
        wflvl1 = factories.WorkflowLevel1(
            organization=self.tola_user.organization)
        fields = [
            {
                'name': 'color',
                'type': 'text'
            },
            {
                'name': 'type',
                'type': 'text'
            }
        ]
        meta = {
            'name': 'Export Test',
            'description': 'This is a test.',
            'fields': json.dumps(fields),
            'level1_uuid': wflvl1.level1_uuid,
            'tola_user_uuid': self.tola_user.tola_user_uuid,
            'form_uuid': uuid.uuid4()
        }
        request = self.factory.post('', data=meta)
        request.user = self.tola_user.user
        view = CustomFormViewSet.as_view({'post': 'create'})
        response = view(request)
        self.assertEqual(response.status_code, 201)
        # For the tearDown
        silo_id = response.data['id']
        silo = Silo.objects.get(id=silo_id)
        read = silo.reads.all()[0]

        # Upload data
        data = [{
            'color': 'black',
            'type': 'primary'
        }, {
            'color': 'white',
            'type': 'primary'
        }, {
            'color': 'red',
            'type': 'primary'
        }]
        util.save_data_to_silo(silo, data, read)

        # Export to CSV
        request = self.factory.get('')
        request.user = self.tola_user.user
        response = views.export_silo(request, silo_id)
        self.assertEqual(response.status_code, 200)
        self.assertIn('color,type', response.content)
        self.assertIn('black,primary', response.content)


class SiloViewsTest(TestCase, MongoTestCase):
    def setUp(self):
        factories.ReadType(read_type='CustomForm')
        self.org = factories.Organization()
        self.tola_user = factories.TolaUser(organization=self.org)
        self.factory = APIRequestFactory()

    def _bugfix_django_messages(self, request):
        """
        RequestFactory requests can't be used to test views
        that call messages.add
        https://code.djangoproject.com/ticket/17971
        """
        setattr(request, 'session', 'session')
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)

    @patch('silo.views.get_workflowlevel1s', return_value=[])
    def test_silo_template_authenticated_user(self, mock_get_workflowlevel1s):
        request = self.factory.get('', follow=True)
        request.user = self.tola_user.user
        response = views.list_silos(request)
        template_content = response.content

        match = '<span id="user_init"'
        self.assertEqual(template_content.count(match), 1)

        match = '<div id="profileDropDown" ' \
                'class="dropdown-menu dropdown-menu-right">'
        self.assertEqual(template_content.count(match), 1)

    @patch('tola.activity_proxy.get_workflowteams')
    @patch('silo.forms.get_workflowlevel1s')
    def test_get_edit_silo(self, mock_get_workflowlevel1s,
                           mock_get_workflowteams):
        silo = factories.Silo(owner=self.tola_user.user)
        wfl1_1 = factories.WorkflowLevel1(level1_uuid=random.randint(1, 9999),
                                          name='Workflowlevel1 1')
        wfl1_2 = factories.WorkflowLevel1(level1_uuid=random.randint(1, 9999),
                                          name='Workflowlevel1 2')

        wfl1_data = {
            'level1_uuid': wfl1_1.level1_uuid
        }

        wfteams = [
            {
                'workflowlevel1': wfl1_data
            }
        ]

        mock_get_workflowlevel1s.return_value = [wfl1_1.level1_uuid]
        mock_get_workflowteams.return_value = wfteams
        request = self.factory.get('/silo_edit/{}/'.format(silo.id),
                                   follow=True)
        request.user = self.tola_user.user
        response = views.edit_silo(request, silo.id)
        template_content = response.content

        match = 'selected>{}</option>'.format(self.tola_user.user.username)
        self.assertEqual(template_content.count(match), 1)

        # check if only the allowed programs are shown
        self.assertEqual(template_content.count(wfl1_1.name), 1)
        self.assertEqual(template_content.count(wfl1_2.name), 0)

    @patch('tola.activity_proxy.get_workflowteams')
    @patch('silo.views.get_workflowlevel1s', return_value=[])
    def test_get_edit_silo_no_teams(self, mock_get_workflowteams,
                                    mock_get_workflowlevel1s):
        silo = factories.Silo(owner=self.tola_user.user)
        wfteams = []
        mock_get_workflowteams.return_value = wfteams
        request = self.factory.get('/silo_edit/{}/'.format(silo.id),
                                   follow=True)
        request.user = self.tola_user.user
        response = views.edit_silo(request, silo.id)
        template_content = response.content

        match = 'selected>{}</option>'.format(self.tola_user.user.username)
        self.assertEqual(template_content.count(match), 1)

    @patch('silo.views.get_workflowlevel1s', return_value=[])
    def test_post_edit_silo(self, mock_get_workflowlevel1s):
        silo = factories.Silo(owner=self.tola_user.user)
        olg_tag = factories.Tag(name='Old Tag', owner=self.tola_user.user)

        data = {
            'name': 'The new silo name',
            'description': '',
            'owner': self.tola_user.user.pk,
            'tags': [olg_tag.id, 'New Tag'],
        }

        request = self.factory.post('/silo_edit/{}/'.format(silo.id), data)
        request.user = self.tola_user.user
        response = views.edit_silo(request, silo.id)
        self.assertEqual(response.status_code, 302)

        silo = Silo.objects.get(pk=silo.id)
        self.assertEqual(silo.name, 'The new silo name')

        # check if the tags were selected and the new one was created
        new_tag = Tag.objects.get(name='New Tag')
        silo_tags = silo.tags.all()
        self.assertIn(olg_tag, silo_tags)
        self.assertIn(new_tag, silo_tags)

    def test_silo_edit_columns(self):
        self.tola_user.user.is_staff = True
        self.tola_user.user.is_superuser = True
        self.tola_user.user.save()

        columns = [{'name': 'name', 'type': 'text'}]
        read = factories.Read(read_name='Read Test', owner=self.tola_user.user)
        silo = factories.Silo(owner=self.tola_user.user,
                              columns=json.dumps(columns), reads=[read])

        data = {
            'id': '',
            'silo_id': silo.id,
            'name': 'given_name',
        }
        request = self.factory.post('', data=data)
        request.user = self.tola_user.user
        self._bugfix_django_messages(request)
        response = views.edit_columns(request, silo.id)

        column_names = util.getSiloColumnNames(silo.id)

        self.assertTrue('given_name' in column_names)
        self.assertEqual(len(column_names), 1)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/silo_detail/'+str(silo.id)+'/')

    def test_silo_edit_columns_utf8(self):
        self.tola_user.user.is_staff = True
        self.tola_user.user.is_superuser = True
        self.tola_user.user.save()

        columns = [{'name': 'name', 'type': 'text'}]
        read = factories.Read(read_name='Read Test', owner=self.tola_user.user)
        silo = factories.Silo(owner=self.tola_user.user,
                              columns=json.dumps(columns), reads=[read])

        data = {
            'id': '',
            'silo_id': silo.id,
            'name': u'ürlaub',
        }
        request = self.factory.post('', data=data)
        request.user = self.tola_user.user
        self._bugfix_django_messages(request)
        response = views.edit_columns(request, silo.id)

        column_names = util.getSiloColumnNames(silo.id)

        self.assertTrue(u'ürlaub' in column_names)
        self.assertEqual(len(column_names), 1)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/silo_detail/'+str(silo.id)+'/')

    def test_silo_edit_columns_keep_data(self):
        self.tola_user.user.is_staff = True
        self.tola_user.user.is_superuser = True
        self.tola_user.user.save()

        columns = [
            {
                'name': 'color',
                'type': 'text'
            },
            {
                'name': 'type',
                'type': 'text'
            }
        ]
        read = factories.Read(read_name='Read Test', owner=self.tola_user.user)
        silo = factories.Silo(owner=self.tola_user.user,
                              columns=json.dumps(columns), reads=[read])

        # Upload data
        data = [{
            'color': 'black',
            'type': 'primary'
        }, {
            'color': 'white',
            'type': 'primary'
        }, {
            'color': 'red',
            'type': 'primary'
        }]
        util.save_data_to_silo(silo, data, read)

        # Check if the data was inserted
        filter_fields = {}
        db_data = LabelValueStore.objects(silo_id=silo.id, **filter_fields). \
            exclude('create_date', 'edit_date', 'silo_id', 'read_id')
        json_data = json.loads(db_data.to_json())

        self.assertEqual(len(json_data), 3)
        self.assertTrue('color' in json_data[0])
        self.assertTrue('type' in json_data[0])

        self.assertTrue(json_data[0]['color'] in ['black', 'white', 'red'])
        self.assertEqual(json_data[0]['type'], 'primary')

        data = {
            'id': '',
            'silo_id': silo.id,
            'color': 'farbe',
            'type': 'art'
        }
        request = self.factory.post('', data=data)
        request.user = self.tola_user.user
        self._bugfix_django_messages(request)
        views.edit_columns(request, silo.id)

        # Check if the data was kept but the column name was changed
        db_data = LabelValueStore.objects(silo_id=silo.id, **filter_fields).\
            exclude('create_date', 'edit_date', 'silo_id', 'read_id')
        json_data = json.loads(db_data.to_json())

        self.assertEqual(len(json_data), 3)
        self.assertTrue('farbe' in json_data[0])
        self.assertTrue('art' in json_data[0])

        self.assertTrue(json_data[0]['farbe'] in ['black', 'white', 'red'])
        self.assertEqual(json_data[0]['art'], 'primary')

    @patch('silo.views.db')
    def test_silo_edit_columns_delete(self, mock_db):
        mock_db.return_value = Mock()
        self.tola_user.user.is_staff = True
        self.tola_user.user.is_superuser = True
        self.tola_user.user.save()

        fields = [
            {
                'name': 'test_color',
                'type': 'text'
            },
            {
                'name': 'type',
                'type': 'text'
            }
        ]
        silo = factories.Silo(
            name='Delete Test',
            columns=json.dumps(fields),
        )

        data = {
            'id': '',
            'silo_id': silo.id,
            'test_color_delete': True,
            'type': 'type'
        }
        request = self.factory.post('', data=data)
        request.user = self.tola_user.user
        self._bugfix_django_messages(request)
        views.edit_columns(request, silo.id)

        silo = Silo.objects.get(pk=silo.id)
        column_names = util.getSiloColumnNames(silo.id)
        self.assertTrue('test_color' not in column_names)
        self.assertTrue('type' in column_names)

    def test_silo_edit_columns_invalid_form(self):
        self.tola_user.user.is_staff = True
        self.tola_user.user.is_superuser = True
        self.tola_user.user.save()

        wflvl1 = factories.WorkflowLevel1(
            organization=self.tola_user.organization)
        fields = [
            {
                'name': 'color',
                'type': 'text'
            },
            {
                'name': 'type',
                'type': 'text'
            }
        ]
        meta = {
            'name': 'Export Test',
            'description': 'This is a test.',
            'fields': json.dumps(fields),
            'level1_uuid': wflvl1.level1_uuid,
            'tola_user_uuid': self.tola_user.tola_user_uuid,
            'form_uuid': uuid.uuid4()
        }
        request = self.factory.post('', data=meta)
        request.user = self.tola_user.user
        view = CustomFormViewSet.as_view({'post': 'create'})
        response = view(request)
        # For the tearDown
        silo_id = response.data['id']
        silo = Silo.objects.get(id=silo_id)

        data = {}
        request = self.factory.post('', data=data)
        request.user = self.tola_user.user
        self._bugfix_django_messages(request)
        response = views.edit_columns(request, silo.id)
        template_content = response.content

        match = '<label for="id_color" class="control-label col-sm-5">'
        self.assertIn(match, template_content)

        match = '<label for="id_type" class="control-label col-sm-5">'
        self.assertIn(match, template_content)

    def test_silo_edit_columns_fields_dont_match(self):
        self.tola_user.user.is_staff = True
        self.tola_user.user.is_superuser = True
        self.tola_user.user.save()

        wflvl1 = factories.WorkflowLevel1(
            organization=self.tola_user.organization)
        fields = [
            {
                'name': 'color',
                'type': 'text'
            },
            {
                'name': 'type',
                'type': 'text'
            }
        ]
        meta = {
            'name': 'Export Test',
            'description': 'This is a test.',
            'fields': json.dumps(fields),
            'level1_uuid': wflvl1.level1_uuid,
            'tola_user_uuid': self.tola_user.tola_user_uuid,
            'form_uuid': uuid.uuid4()
        }
        request = self.factory.post('', data=meta)
        request.user = self.tola_user.user
        view = CustomFormViewSet.as_view({'post': 'create'})
        response = view(request)
        # For the tearDown
        silo_id = response.data['id']
        silo = Silo.objects.get(id=silo_id)

        data = {
            'invalid': 'invalid',
            'test': 'test'
        }
        request = self.factory.post('', data=data)
        request.user = self.tola_user.user
        with self.assertRaises(WriteError):
            views.edit_columns(request, silo.id)


class SaveAndImportReadViewTest(TestCase):
    def setUp(self):
        self.org = factories.Organization()
        self.tola_user = factories.TolaUser(organization=self.org)
        self.factory = APIRequestFactory()

    @patch('silo.views.save_data_to_silo')
    @patch('silo.views.requests')
    def test_save_and_import_read(self, mock_requests, mock_savedatasilo):
        data_res = {'detail': 'Success'}
        mock_savedatasilo.return_value = Mock()
        mock_requests.get.return_value = Mock(content=json.dumps(data_res))

        read = factories.Read(read_name='Read Test', owner=self.tola_user.user)
        silo = factories.Silo(owner=self.tola_user.user, reads=[read])
        factories.ThirdPartyTokens(user=self.tola_user.user, name='ONA')
        factories.ReadType(read_type='ONA')

        data = {
            'read_name': read.read_name,
            'description': silo.description,
            'silo_id': silo.id,
            'silo_name': silo.name
        }

        request = self.factory.post('', data)
        request.user = self.tola_user.user
        response = views.saveAndImportRead(request)
        template_content = response.content

        match = reverse('silo_detail', args=[silo.pk])
        self.assertIn(match, template_content)

    @patch('silo.views.requests')
    def test_save_and_import_read_without_data(self, mock_requests):
        mock_requests.get.return_value = Mock(content='[]')

        read = factories.Read(read_name='Read Test', owner=self.tola_user.user)
        silo = factories.Silo(owner=self.tola_user.user, reads=[read])
        factories.ThirdPartyTokens(user=self.tola_user.user, name='ONA')
        factories.ReadType(read_type='ONA')

        data = {
            'read_name': read.read_name,
            'description': silo.description,
            'silo_id': silo.id,
            'silo_name': silo.name
        }

        request = self.factory.post('', data)
        request.user = self.tola_user.user
        response = views.saveAndImportRead(request)
        content = response.content

        self.assertEqual('There is not data for the selected form, {}'.format(
            read.read_name), content)

    @patch('silo.views.requests')
    def test_save_and_import_read_without_silo_id(self, mock_requests):
        data_res = {'detail': 'Success'}
        mock_requests.get.return_value = Mock(content=json.dumps(data_res))

        read = factories.Read(read_name='Read Test', owner=self.tola_user.user)
        silo = factories.Silo(owner=self.tola_user.user, reads=[read])
        factories.ThirdPartyTokens(user=self.tola_user.user, name='ONA')
        factories.ReadType(read_type='ONA')

        data = {
            'read_name': read.read_name,
            'description': silo.description,
            'silo_name': silo.name
        }

        request = self.factory.post('', data)
        request.user = self.tola_user.user
        response = views.saveAndImportRead(request)
        content = response.content

        self.assertEqual('Silo ID can only be an integer', content)

    @patch('silo.views.requests')
    def test_save_and_import_read_without_wrong_read_name(self, mock_requests):
        data_res = {'detail': 'Success'}
        mock_requests.get.return_value = Mock(content=json.dumps(data_res))

        read = factories.Read(read_name='Read Test', owner=self.tola_user.user)
        silo = factories.Silo(owner=self.tola_user.user, reads=[read])
        factories.ThirdPartyTokens(user=self.tola_user.user, name='ONA')
        factories.ReadType(read_type='ONA')

        data = {
            'read_name': 'This Read does not exist',
            'description': silo.description,
            'silo_id': silo.id,
            'silo_name': silo.name
        }

        request = self.factory.post('', data)
        request.user = self.tola_user.user
        response = views.saveAndImportRead(request)
        content = response.content

        self.assertEqual('Invalid name and/or URL', content)


class DoMergeViewTest(TestCase):
    def setUp(self):
        self.org = factories.Organization()
        self.tola_user = factories.TolaUser(organization=self.org)
        self.factory = APIRequestFactory()

    @patch('silo.views.merge_two_silos')
    @patch('silo.views.MergedSilosFieldMapping')
    def test_merge(self, mock_merged_silos_map, mock_merge_two_silos):
        mock_merge_two_silos.return_value = {
            'status': 'success',
            'message': 'Merged data successfully'
        }
        mock_merged_silos_map.return_value = Mock()

        columns = [{'name': 'name', 'type': 'text'}]
        left_read = factories.Read(read_name='Read Left',
                                   owner=self.tola_user.user)
        right_read = factories.Read(read_name='Read Right',
                                    owner=self.tola_user.user)
        left_silo = factories.Silo(owner=self.tola_user.user,
                                   columns=json.dumps(columns),
                                   reads=[left_read])
        right_silo = factories.Silo(owner=self.tola_user.user,
                                    columns=json.dumps(columns),
                                    reads=[right_read])
        merged_silo_name = '{}_{}'.format(left_silo.name, right_silo.name)

        data = {
            'left_table_id': left_silo.id,
            'right_table_id': right_silo.id,
            'tableMergeType': 'merge',
            'columns_data': 'Test',
            'merged_table_name': merged_silo_name
        }

        request = self.factory.post('', data=data)
        request.user = self.tola_user.user
        response = views.do_merge(request)
        content = json.loads(response.content)

        silo = Silo.objects.get(name=merged_silo_name)
        expected_silo_url = reverse('silo_detail', args=[silo.id])

        self.assertEqual(response.status_code, 200)
        self.assertEqual(content['status'], 'success')
        self.assertEqual(content['message'], 'Merged data successfully')
        self.assertEqual(content['silo_url'], expected_silo_url)
        self.assertIn(left_read, silo.reads.all())
        self.assertIn(right_read, silo.reads.all())

    @patch('silo.views.appendTwoSilos')
    @patch('silo.views.MergedSilosFieldMapping')
    def test_append(self, mock_merged_silos_map, mock_append_two_silos):
        mock_append_two_silos.return_value = {
            'status': 'success',
            'message': 'Appended data successfully'
        }
        mock_merged_silos_map.return_value = Mock()

        columns = [{'name': 'name', 'type': 'text'}]
        left_read = factories.Read(read_name='Read Left',
                                   owner=self.tola_user.user)
        right_read = factories.Read(read_name='Read Right',
                                    owner=self.tola_user.user)
        left_silo = factories.Silo(owner=self.tola_user.user,
                                   columns=json.dumps(columns),
                                   reads=[left_read])
        right_silo = factories.Silo(owner=self.tola_user.user,
                                    columns=json.dumps(columns),
                                    reads=[right_read])
        merged_silo_name = '{}_{}'.format(left_silo.name, right_silo.name)

        data = {
            'left_table_id': left_silo.id,
            'right_table_id': right_silo.id,
            'tableMergeType': 'append',
            'columns_data': 'Test',
            'merged_table_name': merged_silo_name
        }

        request = self.factory.post('', data=data)
        request.user = self.tola_user.user
        response = views.do_merge(request)
        content = json.loads(response.content)

        silo = Silo.objects.get(name=merged_silo_name)
        expected_silo_url = reverse('silo_detail', args=[silo.id])

        self.assertEqual(response.status_code, 200)
        self.assertEqual(content['status'], 'success')
        self.assertEqual(content['message'], 'Appended data successfully')
        self.assertEqual(content['silo_url'], expected_silo_url)
        self.assertIn(left_read, silo.reads.all())
        self.assertIn(right_read, silo.reads.all())

    @patch('silo.views.merge_two_silos')
    def test_status_danger(self, mock_merge_two_silos):
        mock_merge_two_silos.return_value = {'status': 'danger'}

        columns = [{'name': 'name', 'type': 'text'}]
        left_read = factories.Read(read_name='Read Left',
                                   owner=self.tola_user.user)
        right_read = factories.Read(read_name='Read Right',
                                    owner=self.tola_user.user)
        left_silo = factories.Silo(owner=self.tola_user.user,
                                   columns=json.dumps(columns),
                                   reads=[left_read])
        right_silo = factories.Silo(owner=self.tola_user.user,
                                    columns=json.dumps(columns),
                                    reads=[right_read])
        merged_silo_name = '{}_{}'.format(left_silo.name, right_silo.name)

        data = {
            'left_table_id': left_silo.id,
            'right_table_id': right_silo.id,
            'tableMergeType': 'merge',
            'columns_data': 'Test',
            'merged_table_name': merged_silo_name
        }

        request = self.factory.post('', data=data)
        request.user = self.tola_user.user
        response = views.do_merge(request)
        content = json.loads(response.content)

        self.assertRaises(Silo.DoesNotExist,
                          Silo.objects.get, name=merged_silo_name)
        self.assertEqual(content['status'], 'danger')

    def test_no_columns_passed(self):
        read = factories.Read(read_name='Read Test', owner=self.tola_user.user)
        left_silo = factories.Silo(owner=self.tola_user.user, reads=[read])
        right_silo = factories.Silo(owner=self.tola_user.user, reads=[read])
        merged_silo_name = '{}_{}'.format(left_silo.name, right_silo.name)

        data = {
            'left_table_id': left_silo.id,
            'right_table_id': right_silo.id,
            'tableMergeType': 'merge',
            'merged_table_name': merged_silo_name
        }

        request = self.factory.post('', data=data)
        request.user = self.tola_user.user
        response = views.do_merge(request)
        content = json.loads(response.content)

        self.assertRaises(Silo.DoesNotExist,
                          Silo.objects.get, name=merged_silo_name)
        self.assertEqual(content['status'], 'danger')
        self.assertEqual(content['message'], 'No columns data passed')

    def test_cannot_find_tables(self):
        read = factories.Read(read_name='Read Test', owner=self.tola_user.user)
        silo = factories.Silo(owner=self.tola_user.user, reads=[read])

        # Do not find the left table
        data = {
            'left_table_id': 999,
            'right_table_id': silo.id,
            'merged_table_name': 'Another test'
        }

        request = self.factory.post('', data=data)
        request.user = self.tola_user.user
        response = views.do_merge(request)
        content = json.loads(response.content)

        self.assertEqual(content['status'], 'danger')
        self.assertEqual(content['message'],
                         'Could not find the left table with id=999')

        # Do not find the right table
        data = {
            'left_table_id': silo.id,
            'right_table_id': 999,
            'merged_table_name': 'Another test'
        }

        request = self.factory.post('', data=data)
        request.user = self.tola_user.user
        response = views.do_merge(request)
        content = json.loads(response.content)

        self.assertEqual(content['status'], 'danger')
        self.assertEqual(content['message'],
                         'Could not find the right table with id=999')

    @patch('silo.views.merge_two_silos')
    @patch('silo.views.MergedSilosFieldMapping')
    def test_no_merge_name(self, mock_merged_silos_map, mock_merge_two_silos):
        mock_merge_two_silos.return_value = {
            'status': 'success',
            'message': 'Merged data successfully'
        }
        mock_merged_silos_map.return_value = Mock()

        columns = [{'name': 'name', 'type': 'text'}]
        left_read = factories.Read(read_name='Read Left',
                                   owner=self.tola_user.user)
        right_read = factories.Read(read_name='Read Right',
                                    owner=self.tola_user.user)
        left_silo = factories.Silo(owner=self.tola_user.user,
                                   columns=json.dumps(columns),
                                   reads=[left_read])
        right_silo = factories.Silo(owner=self.tola_user.user,
                                    columns=json.dumps(columns),
                                    reads=[right_read])
        merged_silo_name = 'Merging of {} and {}'.format(
            left_silo.id, right_silo.id)

        data = {
            'left_table_id': left_silo.id,
            'right_table_id': right_silo.id,
            'tableMergeType': 'merge',
            'columns_data': 'Test',
            'merged_table_name': ''
        }

        request = self.factory.post('', data=data)
        request.user = self.tola_user.user
        response = views.do_merge(request)
        content = json.loads(response.content)

        silo = Silo.objects.get(name=merged_silo_name)
        expected_silo_url = reverse('silo_detail', args=[silo.id])

        self.assertEqual(response.status_code, 200)
        self.assertEqual(content['status'], 'success')
        self.assertEqual(content['message'], 'Merged data successfully')
        self.assertEqual(content['silo_url'], expected_silo_url)
        self.assertIn(left_read, silo.reads.all())
        self.assertIn(right_read, silo.reads.all())


class OneDriveViewsTest(TestCase):

    def setUp(self):
        self.org = factories.Organization()
        self.tola_user = factories.TolaUser(organization=self.org)
        self.user = factories.User()
        factories.ReadType.create_batch(7)

    def test_onedrive_js_page(self):
        self.client.force_login(self.user)
        response = self.client.get('/onedrive')

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'silo/onedrive.html')

    def test_onedrive_js_page_no_login(self):
        response = self.client.get('/onedrive')

        self.assertEqual(response.status_code, 302)
        self.assertTemplateNotUsed(response, 'silo/onedrive.html')

    def test_read_view_onedrive_contains_fields(self):
        self.client.force_login(self.user)
        response = self.client.get('/source/new/?type=OneDrive')

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'read/read.html')
        self.assertContains(response, "https://js.live.net/v7.2/OneDrive.js")
        self.assertContains(response, "launchOneDrivePicker")
        self.assertContains(response, '<input type="hidden" '
                                      'name="onedrive_file" '
                                      'id="id_onedrive_file" />')
        self.assertContains(response, '<input type="hidden" '
                                      'name="onedrive_access_token" '
                                      'id="id_onedrive_access_token" />')

    def test_other_views_dont_contain_fields(self):
        self.client.force_login(self.user)
        response = self.client.get('/source/new/?type=CSV')

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'read/read.html')
        self.assertNotContains(response, '<input type="hidden" '
                                         'name="onedrive_file" '
                                         'id="id_onedrive_file" />')


class OneDriveReadTest(TestCase):
    new_read_url = '/source/new/'
    # Is the UserSocialAuth extra data obj updated when there is already
    # one? I saw a test when there is no UserSocialAuth.

    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()
        self.tola_user = factories.TolaUser()
        factories.ReadType.create_batch(7)

    def test_new_read_post(self):
        read_type = ReadType.objects.get(read_type="OneDrive")

        params = {
            'owner': self.tola_user.user.pk,
            'type': read_type.pk,
            'read_name': 'TEST READ ONEDRIVE',
            'description': 'TEST DESCRIPTION for test read source',
            'onedrive_file': 'TEST10000100',
            'onedrive_access_token': 'TEST_DUMMY_TOKEN',
            'create_date': '2018-01-26 12:33:00',
        }
        request = self.factory.post(self.new_read_url, data=params)
        request.user = self.tola_user.user

        response = views.showRead(request, 0)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/import_onedrive/1/')

        # check for social auth updated

        social_auth = UserSocialAuth.objects.get(user=self.tola_user.user,
                                                 provider='microsoft-graph')
        self.assertEqual(social_auth.extra_data['access_token'],
                         'TEST_DUMMY_TOKEN')

    def test_new_read_post_existing_token(self):
        read_type = ReadType.objects.get(read_type="OneDrive")

        factories.UserSocialAuth(user=self.tola_user.user,
                                 provider='microsoft-graph',
                                 extra_data={"token_type": "Bearer",
                                             "access_token": "OLD_TOKEN"})

        params = {
            'owner': self.tola_user.user.pk,
            'type': read_type.pk,
            'read_name': 'TEST READ ONEDRIVE',
            'description': 'TEST DESCRIPTION for test read source',
            'onedrive_file': 'TEST10000100',
            'onedrive_access_token': 'TEST_DUMMY_TOKEN_CHANGED',
            'create_date': '2018-01-26 12:33:00',
        }
        request = self.factory.post(self.new_read_url, data=params)
        request.user = self.tola_user.user

        response = views.showRead(request, 0)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/import_onedrive/1/')

        # check for social auth updated

        social_auth = UserSocialAuth.objects.get(user=self.tola_user.user,
                                                 provider='microsoft-graph')
        self.assertEqual(social_auth.extra_data['access_token'],
                         'TEST_DUMMY_TOKEN_CHANGED')

    def test_new_read_post_fails_no_token(self):
        read_type = ReadType.objects.get(read_type="OneDrive")

        params = {
            'owner': self.tola_user.user.pk,
            'type': read_type.pk,
            'read_name': 'TEST READ ONEDRIVE',
            'description': 'TEST DESCRIPTION for test read source',
            'onedrive_file': 'TEST10000100',
            'create_date': '2018-01-26 12:33:00',
        }
        request = self.factory.post(self.new_read_url, data=params)
        request.user = self.tola_user.user
        request.session = 'session'
        message_storage = FallbackStorage(request)
        request._messages = message_storage
        views.showRead(request, 0)

        messages = []
        for m in message_storage:
            messages.append(m.message)

        self.assertIn('Invalid Form', messages)

    def test_new_read_post_fails_no_file(self):
        read_type = ReadType.objects.get(read_type="OneDrive")

        params = {
            'owner': self.tola_user.user.pk,
            'type': read_type.pk,
            'read_name': 'TEST READ ONEDRIVE',
            'description': 'TEST DESCRIPTION for test read source',
            'onedrive_access_token': 'TEST_DUMMY_TOKEN',
            'create_date': '2018-01-26 12:33:00',
        }
        request = self.factory.post(self.new_read_url, data=params)
        request.user = self.tola_user.user
        request.session = 'session'
        message_storage = FallbackStorage(request)
        request._messages = message_storage
        views.showRead(request, 0)
        messages = []
        for m in message_storage:
            messages.append(m.message)

        self.assertIn('Invalid Form', messages)

    def test_new_read_post_creates_uuid(self):
        """
        POST for onedrive should create uuid for UserSocialAuth, otherwise
        unique_together will not be unique.
        """
        read_type = ReadType.objects.get(read_type="OneDrive")

        params = {
            'owner': self.tola_user.user.pk,
            'type': read_type.pk,
            'read_name': 'TEST READ ONEDRIVE',
            'description': 'TEST DESCRIPTION for test read source',
            'onedrive_file': 'TEST10000100',
            'onedrive_access_token': 'TEST_DUMMY_TOKEN',
            'create_date': '2018-01-26 12:33:00',
        }
        request = self.factory.post(self.new_read_url, data=params)
        request.user = self.tola_user.user

        response = views.showRead(request, 0)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/import_onedrive/1/')

        # check for social auth updated

        social_auth = UserSocialAuth.objects.get(user=self.tola_user.user,
                                                 provider='microsoft-graph')

        self.assertNotEqual(social_auth.uid, '')


class SiloDetailViewTest(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = factories.User()
        self.tola_user = factories.TolaUser(user=self.user)

    def test_silo_detail_view(self):
        read = factories.Read(read_name="test_data",
                              owner=self.user)
        silo = factories.Silo(owner=self.user,
                              reads=[read])
        url = reverse('silo_detail', args=[silo.pk])

        request = self.factory.get(url)
        request.user = self.user
        response = views.silo_detail(request, silo.pk)

        self.assertEqual(response.status_code, 200)

    def test_private_silo_detail_with_unshared_user(self):
        read = factories.Read(read_name="test_data",
                              owner=self.user)
        silo = factories.Silo(owner=self.user,
                              reads=[read],
                              public=False,
                              shared=[])
        url = reverse('silo_detail', args=[silo.pk])

        request_user = factories.User(username='Another User')
        factories.TolaUser(user=request_user)

        request = self.factory.get(url)
        request.user = request_user
        request.session = 'session'
        message_storage = FallbackStorage(request)
        request._messages = message_storage
        views.silo_detail(request, silo.pk)
        messages = []
        for m in message_storage:
            messages.append(m.message)

        self.assertIn('You do not have permission to view this table.',
                      messages)

    def test_pulic_silo_detail_with_unshared_user(self):
        read = factories.Read(read_name="test_data",
                              owner=self.user)
        silo = factories.Silo(owner=self.user,
                              reads=[read],
                              public=True,
                              shared=[])
        url = reverse('silo_detail', args=[silo.pk])

        request_user = factories.User(username='Another User')
        factories.TolaUser(user=request_user)

        request = self.factory.get(url)
        request.user = request_user
        response = views.silo_detail(request, silo.pk)

        self.assertEqual(response.status_code, 200)

    def test_private_silo_detail_with_shared_user(self):

        request_user = factories.User(username='Another User')
        factories.TolaUser(user=request_user)

        read = factories.Read(read_name="test_data",
                              owner=self.user)
        silo = factories.Silo(owner=self.user,
                              reads=[read],
                              public=False,
                              shared=[request_user])
        url = reverse('silo_detail', args=[silo.pk])

        request = self.factory.get(url)
        request.user = request_user
        response = views.silo_detail(request, silo.pk)

        self.assertEqual(response.status_code, 200)

    def test_private_silo_detail_with_owner_user(self):

        request_user = factories.User(username='Another User')

        read = factories.Read(read_name="test_data",
                              owner=self.user)
        silo = factories.Silo(owner=self.user,
                              reads=[read],
                              public=False,
                              shared=[request_user])
        url = reverse('silo_detail', args=[silo.pk])

        request = self.factory.get(url)
        request.user = self.user
        response = views.silo_detail(request, silo.pk)

        self.assertEqual(response.status_code, 200)

    def test_public_silo_detail_with_owner_user(self):
        read = factories.Read(read_name="test_data",
                              owner=self.user)
        silo = factories.Silo(owner=self.user,
                              reads=[read],
                              public=True)
        url = reverse('silo_detail', args=[silo.pk])

        request = self.factory.get(url)
        request.user = self.user
        response = views.silo_detail(request, silo.pk)
        template_content = response.content

        self.assertEqual(response.status_code, 200)
        self.assertIn('<a href="#" id="id_public-{}"'.format(silo.id),
                      template_content)

    def test_public_silo_detail_with_not_owner_user(self):
        request_user = factories.User(username='Another User')
        factories.TolaUser(user=request_user)

        read = factories.Read(read_name="test_data",
                              owner=self.user)
        silo = factories.Silo(owner=self.user,
                              reads=[read],
                              public=True)
        url = reverse('silo_detail', args=[silo.pk])

        request = self.factory.get(url)
        request.user = request_user
        response = views.silo_detail(request, silo.pk)
        template_content = response.content

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('<a href="#" id="id_public-{}"'.format(silo.id),
                         template_content)

    def test_silo_detail_share_with_organization(self):
        request_user = factories.User(username='Another User')
        organization = self.tola_user.organization
        factories.TolaUser(user=request_user, organization=organization)

        read = factories.Read(read_name="test_data",
                              owner=self.tola_user.user)

        silo = factories.Silo(owner=self.tola_user.user,
                              reads=[read],
                              public=False,
                              shared=[],
                              share_with_organization=True)

        url = reverse('silo_detail', args=[silo.pk])

        request = self.factory.get(url)
        request.user = request_user
        response = views.silo_detail(request, silo.pk)

        self.assertEqual(response.status_code, 200)

    def test_silo_detail_not_share_with_organization(self):
        request_user = factories.User(username='Another User')
        factories.TolaUser(user=request_user,
                           organization=self.tola_user.organization)

        read = factories.Read(read_name="test_data",
                              owner=self.tola_user.user)

        silo = factories.Silo(owner=self.tola_user.user,
                              reads=[read],
                              public=False,
                              shared=[],
                              share_with_organization=False)

        url = reverse('silo_detail', args=[silo.pk])

        request = self.factory.get(url)
        request.user = request_user
        request.session = 'session'
        message_storage = FallbackStorage(request)
        request._messages = message_storage
        views.silo_detail(request, silo.pk)
        messages = []
        for m in message_storage:
            messages.append(m.message)

        self.assertIn('You do not have permission to view this table.',
                      messages)

    def test_silo_detail_share_with_different_organization(self):
        request_user = factories.User(username='Another User')
        factories.TolaUser(user=request_user)

        read = factories.Read(read_name="test_data",
                              owner=self.tola_user.user)

        silo = factories.Silo(name='Test Share Silo',
                              owner=self.tola_user.user,
                              reads=[read],
                              public=False,
                              shared=[],
                              share_with_organization=True)

        url = reverse('silo_detail', args=[silo.pk])

        request = self.factory.get(url)
        request.user = request_user
        request.session = 'session'
        message_storage = FallbackStorage(request)
        request._messages = message_storage
        views.silo_detail(request, silo.pk)
        messages = []
        for m in message_storage:
            messages.append(m.message)

        self.assertIn('You do not have permission to view this table.',
                      messages)

    @patch('silo.views.get_workflowlevel1s')
    def test_silo_detail_shared_with_workflow(self,
                                              mock_get_workflowlevel1s):

        request_user = factories.User(username='Another User')
        wfl1_1 = factories.WorkflowLevel1(name='Workflowlevel1 1')

        user_wf1s = [wfl1_1.level1_uuid]

        factories.TolaUser(user=request_user)

        silo = factories.Silo(name='Test Share Silo',
                              owner=self.tola_user.user,
                              workflowlevel1=[wfl1_1],
                              shared=[],
                              share_with_organization=False)

        mock_get_workflowlevel1s.return_value = user_wf1s
        request = self.factory.get('')
        request.user = request_user
        response = views.silo_detail(request, silo.pk)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Share Silo')

    @patch('silo.views.get_workflowlevel1s')
    def test_silo_detail_not_shared_with_workflow(self,
                                                  mock_get_workflowlevel1s):

        request_user = factories.User(username='Another User')
        wfl1_1 = factories.WorkflowLevel1(name='Workflowlevel1 1')

        user_wf1s = [wfl1_1.level1_uuid]
        factories.TolaUser(user=request_user)
        silo = factories.Silo(name='Test Share Silo',
                              owner=self.tola_user.user,
                              workflowlevel1=[],
                              shared=[],
                              share_with_organization=False)

        mock_get_workflowlevel1s.return_value = user_wf1s
        request = self.factory.get('')
        request.user = request_user
        request.session = 'session'
        message_storage = FallbackStorage(request)
        request._messages = message_storage
        views.silo_detail(request, silo.pk)

        messages = []
        for m in message_storage:
            messages.append(m.message)

        self.assertIn("You do not have permission to view this table.",
                      messages)

    def test_silo_detail_change_publicty_owner(self):

        read = factories.Read(read_name="test_data",
                              owner=self.tola_user.user)

        silo = factories.Silo(name='Test Share Silo',
                              owner=self.tola_user.user,
                              reads=[read],
                              public=False,
                              shared=[],
                              share_with_organization=True)

        request = self.factory.get('/toggle_silo_publicity/?silo_id={}'
                                   .format(silo.pk))
        request.user = self.user
        response = views.toggle_silo_publicity(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, 'Your change has been saved')

    def test_silo_detail_change_publicty_not_owner(self):

        request_user = factories.User(username='Another User')
        factories.TolaUser(user=request_user)
        read = factories.Read(read_name="test_data",
                              owner=self.tola_user.user)

        silo = factories.Silo(name='Test Share Silo',
                              owner=self.tola_user.user,
                              reads=[read],
                              public=False,
                              shared=[],
                              share_with_organization=True)

        request = self.factory.get('/toggle_silo_publicity/?silo_id={}'
                                   .format(silo.pk))
        request.user = request_user
        response = views.toggle_silo_publicity(request)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content,
                         'You can not  change publicity of this table')


class SiloListViewTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = factories.User()
        self.tola_user = factories.TolaUser(user=self.user)

    def test_list_silos_share_with_users_organization(self):
        request_user = factories.User(username='Another User')
        factories.TolaUser(user=request_user,
                           organization=self.tola_user.organization)

        read = factories.Read(read_name="test_data",
                              owner=self.tola_user.user)

        factories.Silo(name='Test Share Silo',
                       owner=self.tola_user.user,
                       reads=[read],
                       public=False,
                       shared=[],
                       share_with_organization=True)

        request = self.factory.get('')
        request.user = request_user
        response = views.list_silos(request)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Share Silo')

    def test_list_silos_share_with_different_organization(self):
        request_user = factories.User(username='Another User')
        factories.TolaUser(user=request_user)

        read = factories.Read(read_name="test_data",
                              owner=self.tola_user.user)

        factories.Silo(name='Test Share Silo',
                       owner=self.tola_user.user,
                       reads=[read],
                       public=False,
                       shared=[],
                       share_with_organization=True)
        request = self.factory.get('')
        request.user = request_user
        response = views.list_silos(request)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Test Share Silo')

    def test_list_silos_not_share_with_organization(self):
        request_user = factories.User(username='Another User')
        factories.TolaUser(user=request_user,
                           organization=self.tola_user.organization)

        read = factories.Read(read_name="test_data",
                              owner=self.tola_user.user)

        factories.Silo(name='Test Share Silo',
                       owner=self.tola_user.user,
                       reads=[read],
                       public=False,
                       shared=[],
                       share_with_organization=False)

        request = self.factory.get('')
        request.user = request_user
        response = views.list_silos(request)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Test Share Silo')

    def test_list_silos_with_owner_user(self):

        read = factories.Read(read_name="test_data",
                              owner=self.tola_user.user)

        factories.Silo(name='Test Share Silo',
                       owner=self.tola_user.user,
                       reads=[read],
                       public=False,
                       shared=[],
                       share_with_organization=True)

        request = self.factory.get('')
        request.user = self.user
        response = views.list_silos(request)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Share Silo')

    def test_list_silos_with_shared_user(self):

        request_user = factories.User(username='Another User')
        read = factories.Read(read_name="test_data",
                              owner=self.tola_user.user)

        factories.Silo(name='Test Share Silo',
                       owner=self.tola_user.user,
                       reads=[read],
                       public=False,
                       shared=[request_user],
                       share_with_organization=False)

        request = self.factory.get('')
        request.user = self.user
        response = views.list_silos(request)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Share Silo')

    def test_list_public_silo(self):
        request_user = factories.User(username='Another User')
        factories.TolaUser(user=request_user)

        read = factories.Read(read_name="test_data",
                              owner=self.tola_user.user)

        factories.Silo(name='Test Share Silo',
                       owner=self.tola_user.user,
                       reads=[read],
                       public=True,
                       shared=[],
                       share_with_organization=False)

        request = self.factory.get('')
        request.user = request_user
        response = views.list_silos(request)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Share Silo')

    def test_list_silos_share_with_owner(self):
        read = factories.Read(read_name="test_data",
                              owner=self.tola_user.user)

        silo = factories.Silo(name='Test Share Silo',
                              owner=self.tola_user.user,
                              reads=[read],
                              public=False,
                              shared=[self.tola_user.user],
                              share_with_organization=False)

        request = self.factory.get('')
        request.user = self.tola_user.user
        response = views.list_silos(request)
        match = '<a href="/silo_edit/%s">Test Share Silo</a>' % silo.pk
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.count(match), 1)

    def test_list_silos_share_with_owner_organization(self):
        read = factories.Read(read_name="test_data",
                              owner=self.tola_user.user)

        silo = factories.Silo(name='Test Share Silo',
                              owner=self.tola_user.user,
                              reads=[read],
                              public=False,
                              shared=[],
                              share_with_organization=True)

        request = self.factory.get('')
        request.user = self.tola_user.user
        response = views.list_silos(request)
        match = '<a href="/silo_edit/%s">Test Share Silo</a>' % silo.pk
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.count(match), 1)

    @patch('silo.views.get_workflowlevel1s')
    def test_list_silo_shared_with_workflow(self,
                                            mock_get_workflowlevel1s):
        request_user = factories.User(username='Another User')
        wfl1_1 = factories.WorkflowLevel1(name='Workflowlevel1 1')

        user_wf1s = [wfl1_1.level1_uuid]

        factories.TolaUser(user=request_user)

        factories.Silo(name='Test Share Silo',
                       owner=self.tola_user.user,
                       workflowlevel1=[wfl1_1],
                       shared=[],
                       share_with_organization=False)

        mock_get_workflowlevel1s.return_value = user_wf1s
        request = self.factory.get('')
        request.user = request_user
        response = views.list_silos(request)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Share Silo')

    @patch('silo.views.get_workflowlevel1s')
    def test_list_silo_not_shared_with_workflow(self,
                                                mock_get_workflowlevel1s):

        request_user = factories.User(username='Another User')
        wfl1_1 = factories.WorkflowLevel1(name='Workflowlevel1 1')

        user_wf1s = [wfl1_1.level1_uuid]
        factories.TolaUser(user=request_user)
        factories.Silo(name='Test Share Silo',
                       owner=self.tola_user.user,
                       workflowlevel1=[],
                       shared=[],
                       share_with_organization=False)

        mock_get_workflowlevel1s.return_value = user_wf1s
        request = self.factory.get('')
        request.user = request_user
        response = views.list_silos(request)
        self.assertNotContains(response, 'Test Share Silo')

    @override_settings(APP_BRANCH='demo')
    def test_list_silo_inlinemanual_tour_in_demo(self):
        request = self.factory.get('')
        request.user = self.tola_user.user
        response = views.list_silos(request)
        match = 'https://inlinemanual.com/embed/' \
                'player.3c86e010f5c79d355223b63b3ec541ea.js'
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.count(match), 0)

    @override_settings(APP_BRANCH=MASTER_BRANCH)
    def test_list_silo_inlinemanual_tour_in_master(self):
        request = self.factory.get('')
        request.user = self.tola_user.user
        response = views.list_silos(request)
        match = 'https://inlinemanual.com/embed/' \
                'player.3c86e010f5c79d355223b63b3ec541ea.js'
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.count(match), 1)


class SiloEditViewTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = factories.User()
        self.tola_user = factories.TolaUser(user=self.user)

    @patch('tola.activity_proxy.get_workflowteams')
    def test_silo_edit_page_with_unauthorized_user(self,
                                                   mock_get_workflowteams):
        request_user = factories.User(username='Another User')
        organization = factories.Organization(name='Another Organization')
        factories.TolaUser(user=request_user, organization=organization)

        read = factories.Read(read_name="test_data",
                              owner=self.tola_user.user)

        silo = factories.Silo(name='Test Share Silo',
                              owner=self.tola_user.user,
                              reads=[read],
                              public=False,
                              shared=[],
                              share_with_organization=False)

        request = self.factory.get('')
        request.user = request_user
        response = views.edit_silo(request, silo.pk)
        self.assertEqual(response.status_code, 404)

    @patch('tola.activity_proxy.get_workflowteams')
    def test_silo_edit_page_with_owner(self, mock_get_workflowteams):

        read = factories.Read(read_name="test_data",
                              owner=self.tola_user.user)

        silo = factories.Silo(name='Test Share Silo',
                              owner=self.tola_user.user,
                              reads=[read],
                              public=False,
                              shared=[],
                              share_with_organization=False)

        request = self.factory.get('')
        request.user = self.tola_user.user
        response = views.edit_silo(request, silo.pk)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Share Silo')

    @patch('tola.activity_proxy.get_workflowteams')
    def test_silo_edit_page_with_shared_user(self, mock_get_workflowteams):
        request_user = factories.User(username='Another User')
        factories.TolaUser(user=request_user)

        read = factories.Read(read_name="test_data",
                              owner=self.tola_user.user)

        silo = factories.Silo(name='Test Share Silo',
                              owner=self.tola_user.user,
                              reads=[read],
                              public=False,
                              shared=[request_user],
                              share_with_organization=False)

        request = self.factory.get('')
        request.user = request_user
        response = views.edit_silo(request, silo.pk)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Share Silo')

    @patch('tola.activity_proxy.get_workflowteams')
    def test_silo_edit_page_with_shared_organizaton_user(
            self, mock_get_workflowteams):

        request_user = factories.User(username='Another User')
        factories.TolaUser(user=request_user,
                           organization=self.tola_user.organization)

        read = factories.Read(read_name="test_data",
                              owner=self.tola_user.user)

        silo = factories.Silo(name='Test Share Silo',
                              owner=self.tola_user.user,
                              reads=[read],
                              public=False,
                              shared=[],
                              share_with_organization=True)

        request = self.factory.get('')
        request.user = request_user
        response = views.edit_silo(request, silo.pk)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Share Silo')

    @patch('tola.activity_proxy.get_workflowteams')
    def test_public_silo_edit_page(self, mock_get_workflowteams):

        request_user = factories.User(username='Another User')
        factories.TolaUser(user=request_user,
                           organization=self.tola_user.organization)

        read = factories.Read(read_name="test_data",
                              owner=self.tola_user.user)

        silo = factories.Silo(name='Test Share Silo',
                              owner=self.tola_user.user,
                              reads=[read],
                              public=True,
                              shared=[],
                              share_with_organization=False)

        request = self.factory.get('')
        request.user = request_user
        response = views.edit_silo(request, silo.pk)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Share Silo')

    @patch('tola.activity_proxy.get_workflowteams')
    def test_share_silo_with_owner_failed_for_owner(
            self, mock_get_workflowteams):
        silo = factories.Silo(owner=self.tola_user.user)

        data = {
            'name': 'The new silo name 2',
            'description': '',
            'owner': self.tola_user.user.pk,
            'shared': self.tola_user.user.pk
        }

        request = self.factory.post('/silo_edit/{}/'.format(silo.id), data)
        request.user = self.tola_user.user
        request._dont_enforce_csrf_checks = True
        request.session = 'session'
        message_storage = FallbackStorage(request)
        request._messages = message_storage
        views.edit_silo(request, silo.pk)

        messages = []
        for m in message_storage:
            messages.append(m.message)

        self.assertIn('Invalid Form', messages)

    @patch('tola.activity_proxy.get_workflowteams')
    def test_share_silo_with_owner_failed_for_user(self,
                                                   mock_get_workflowteams):

        request_user = factories.User(username='Another User')
        factories.TolaUser(user=request_user)

        silo = factories.Silo(owner=self.tola_user.user,
                              shared=[request_user])

        data = {
            'name': 'The new silo name 2',
            'description': '',
            'owner': self.tola_user.user.pk,
            'shared': self.tola_user.user.pk,
        }

        request = self.factory.post('/silo_edit/{}/'.format(silo.id), data)
        request.user = request_user
        request._dont_enforce_csrf_checks = True
        request.session = 'session'
        message_storage = FallbackStorage(request)
        request._messages = message_storage
        views.edit_silo(request, silo.pk)

        messages = []
        for m in message_storage:
            messages.append(m.message)

        self.assertIn('Invalid Form', messages)

    @patch('tola.activity_proxy.get_workflowteams')
    def test_share_silo_without_owner_failed_for_user(
            self, mock_get_workflowteams):
        silo = factories.Silo(owner=self.tola_user.user)

        data = {
            'name': 'The new silo name 2',
            'description': '',
            'shared': self.tola_user.user.pk
        }

        request = self.factory.post('/silo_edit/{}/'.format(silo.id), data)
        request.user = self.tola_user.user
        request._dont_enforce_csrf_checks = True
        request.session = 'session'
        message_storage = FallbackStorage(request)
        request._messages = message_storage
        views.edit_silo(request, silo.pk)

        messages = []
        for m in message_storage:
            messages.append(m.message)

        self.assertIn('Invalid Form', messages)

    @patch('silo.views.get_workflowlevel1s')
    @patch('tola.activity_proxy.get_workflowteams')
    def test_edit_silo_shared_with_workflow(self,
                                            mock_get_workflowteams,
                                            mock_get_workflowlevel1s):
        request_user = factories.User(username='Another User')
        wfl1_1 = factories.WorkflowLevel1(name='Workflowlevel1 1')

        user_wf1s = [wfl1_1.level1_uuid]

        wfteams = [
            {
                'workflowlevel1': 'example.de/workflowlevel1/{}/'.format(
                    wfl1_1.id)
            }
        ]

        mock_get_workflowteams.mock_get_workflowteams = wfteams
        mock_get_workflowlevel1s.return_value = user_wf1s

        factories.TolaUser(user=request_user)

        silo = factories.Silo(name='Test Share Silo',
                              owner=self.tola_user.user,
                              workflowlevel1=[wfl1_1],
                              shared=[],
                              share_with_organization=False)

        request = self.factory.get('')
        request.user = request_user
        response = views.edit_silo(request, silo.pk)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Share Silo')

    @patch('silo.views.get_workflowlevel1s')
    def test_edit_silo_not_shared_with_workflow(self,
                                                mock_get_workflowlevel1s):

        request_user = factories.User(username='Another User')
        wfl1_1 = factories.WorkflowLevel1(name='Workflowlevel1 1')

        mock_get_workflowlevel1s.return_value = [wfl1_1.level1_uuid]
        factories.TolaUser(user=request_user)
        silo = factories.Silo(name='Test Share Silo',
                              owner=self.tola_user.user,
                              workflowlevel1=[],
                              shared=[],
                              share_with_organization=False)

        request = self.factory.get('')
        request.user = request_user
        response = views.edit_silo(request, silo.pk)
        self.assertEqual(response.status_code, 404)

    @patch('silo.views.get_workflowlevel1s')
    def test_edit_silo_success_get_owner_selectbox(self,
                                                   mock_get_workflowlevel1s):

        mock_get_workflowlevel1s.return_value = []
        silo = factories.Silo(name='Test Share Silo',
                              owner=self.tola_user.user,
                              workflowlevel1=[],
                              share_with_organization=False)

        request = self.factory.get('')
        request.user = self.tola_user.user
        response = views.edit_silo(request, silo.pk)
        template_content = response.content

        match = '<select name="owner"'
        self.assertEqual(template_content.count(match), 1)

    @patch('silo.views.get_workflowlevel1s')
    def test_edit_silo_fail_get_owner_selectbox(self,
                                                mock_get_workflowlevel1s):

        request_user = factories.User(username='Another User')
        wfl1_1 = factories.WorkflowLevel1(name='Workflowlevel1 1')

        mock_get_workflowlevel1s.return_value = [wfl1_1.level1_uuid]
        factories.TolaUser(user=request_user)
        silo = factories.Silo(name='Test Share Silo',
                              owner=self.tola_user.user,
                              workflowlevel1=[],
                              shared=[request_user],
                              share_with_organization=False)

        request = self.factory.get('')
        request.user = request_user
        response = views.edit_silo(request, silo.pk)
        template_content = response.content

        match = '<select name="owner"'
        self.assertEqual(template_content.count(match), 0)

    @patch('silo.views.get_workflowlevel1s', return_value=[])
    def test_post_edit_silo_success_change_owner(self,
                                                 mock_get_workflowlevel1s):

        silo = factories.Silo(owner=self.tola_user.user)
        request_user = factories.User(username='Another User')
        factories.TolaUser(user=request_user,
                           organization=self.tola_user.organization)

        data = {
            'name': 'The new silo name',
            'description': '',
            'owner': request_user.pk,
            'tags': [],
        }

        request = self.factory.post('/silo_edit/{}/'.format(silo.id), data)
        # request.user same with owner
        request.user = self.tola_user.user
        request._dont_enforce_csrf_checks = True
        response = views.edit_silo(request, silo.pk)
        self.assertEqual(response.status_code, 302)

        silo = Silo.objects.get(pk=silo.pk)
        self.assertEqual(silo.owner, request_user)

    @patch('silo.views.get_workflowlevel1s', return_value=[])
    def test_post_edit_silo_fail_change_owner(self,
                                              mock_get_workflowlevel1s):

        silo = factories.Silo(owner=self.tola_user.user)
        request_user = factories.User(username='Another User')
        factories.TolaUser(user=request_user,
                           organization=self.tola_user.organization)

        data = {
            'name': 'The new silo name',
            'description': '',
            'owner': request_user.pk,
            'tags': [],
        }

        request = self.factory.post('/silo_edit/{}/'.format(silo.id), data)
        # request user different from owner
        request.user = request_user
        request._dont_enforce_csrf_checks = True
        response = views.edit_silo(request, silo.pk)
        self.assertEqual(response.status_code, 404)

        silo = Silo.objects.get(pk=silo.pk)
        self.assertNotEqual(silo.owner, request_user)


class PublicSiloViewTest(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.organizaton = factories.Organization()
        self.user = factories.User(username='Test User')
        self.tola_user = factories.TolaUser(user=self.user)

    def test_public_silo_view_with_private_silo(self):
        silo = factories.Silo(name='test',
                              public=False,
                              organization=self.organizaton,
                              owner=self.tola_user.user)

        request = self.factory.get(
            '/api/public_tables/{}/data'.format(silo.pk))
        request.user = self.user
        view = PublicSiloViewSet.as_view({'get': 'data'})
        response = view(request, id=silo.id)

        self.assertEqual(response.status_code, 302)
