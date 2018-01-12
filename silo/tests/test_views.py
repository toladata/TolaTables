from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse
from django.test import TestCase, override_settings

from rest_framework.test import APIRequestFactory

from silo.tests import MongoTestCase
from silo.api import CustomFormViewSet
from silo.models import LabelValueStore, Read, Silo

import json
import factories
from silo import views
from tola import util


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
        self.assertEqual(len(context['readtypes']), 4)
        self.assertEqual(sorted(list(context['readtypes'])),
                         [u'CommCare', u'CustomForm', u'JSON', u'OneDrive'])
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
            reverse('siloDetail', kwargs={'silo_id': silo_pub_1.pk}),
            silo_pub_1.name)
        self.assertEqual(template_content.count(match), 1)

        match = '<a href="{}">{}</a>'.format(
            reverse('siloDetail', kwargs={'silo_id': silo_pub_2.pk}),
            silo_pub_2.name)
        self.assertEqual(template_content.count(match), 1)

        match = '<a href="{}">{}</a>'.format(
            reverse('siloDetail', kwargs={'silo_id': silo_priv_1.pk}),
            silo_priv_1.name)
        self.assertEqual(template_content.count(match), 1)

        match = '<a href="{}">{}</a>'.format(
            reverse('siloDetail', kwargs={'silo_id': silo_shared_1.pk}),
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
        request = self.factory.get('', follow=True)
        request.user = AnonymousUser()
        request.META['HTTP_REFERER'] = 'https://api.toladata.io'
        response = views.IndexView.as_view()(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('login/tola', response.url)

    @override_settings(TOLA_ACTIVITY_API_URL='https://api.toladata.io')
    @override_settings(ACTIVITY_URL='https://toladata.io')
    def test_index_get_from_index_page(self):
        request = self.factory.get('', follow=True)
        request.user = AnonymousUser()
        request.META['HTTP_REFERER'] = 'https://api.toladata.io'
        response = views.IndexView.as_view()(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('login/tola', response.url)

    @override_settings(TOLA_ACTIVITY_API_URL='https://api.toladata.io')
    @override_settings(ACTIVITY_URL='https://toladata.io')
    def test_index_get_from_app(self):
        request = self.factory.get('', follow=True)
        request.user = AnonymousUser()
        request.META['HTTP_REFERER'] = 'https://toladata.io'
        response = views.IndexView.as_view()(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('login/tola', response.url)

    @override_settings(TOLA_ACTIVITY_API_URL=None)
    @override_settings(ACTIVITY_URL='https://toladata.io')
    def test_index_get_unauthenticated_no_activity_api_url(self):
        request = self.factory.get('')
        request.user = AnonymousUser()
        with self.assertRaises(ImproperlyConfigured):
            views.IndexView.as_view()(request)

    @override_settings(TOLA_ACTIVITY_API_URL='https://api.toladata.io')
    @override_settings(ACTIVITY_URL=None)
    def test_index_get_unauthenticated_no_activity_url(self):
        request = self.factory.get('')
        request.user = AnonymousUser()
        with self.assertRaises(ImproperlyConfigured):
            views.IndexView.as_view()(request)


class ExportViewsTest(TestCase, MongoTestCase):
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
            'tola_user_uuid': self.tola_user.tola_user_uuid
        }
        request = self.factory.post('', data=meta)
        request.user = self.tola_user.user
        view = CustomFormViewSet.as_view({'post': 'create'})
        response = view(request)
        self.assertEqual(response.status_code, 201)
        # For the tearDown
        self.silo_id = response.data['id']
        silo = Silo.objects.get(id=self.silo_id)
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
        util.saveDataToSilo(silo, data, read)

        # Export to CSV
        request = self.factory.get('')
        request.user = self.tola_user.user
        response = views.export_silo(request, self.silo_id)
        self.assertEqual(response.status_code, 200)
        self.assertIn('color,type', response.content)
        self.assertIn('black,primary', response.content)


class SiloViewsTest(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def test_silo_template_authenticated_user(self):
        user = factories.User()

        request = self.factory.get('', follow=True)
        request.user = user
        response = views.listSilos(request)
        template_content = response.content

        match = '<span class="header__nav__link__label">Logout</span>'
        self.assertEqual(template_content.count(match), 1)