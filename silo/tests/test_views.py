from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse
from django.test import TestCase, override_settings, RequestFactory

import factories
from silo import views


class IndexViewTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
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
        self.assertEqual(list(context['tags']),
                         [{'name': u'security', 'times_tagged': 4},
                          {'name': u'report', 'times_tagged': 4}]),
        self.assertEqual(context['site_name'], 'Track'),

    def test_index_template_authenticated_user(self):
        user_stranger = factories.User(username='stranger')
        factories.Silo(owner=user_stranger, name='open', public=True)

        user = factories.User()
        silo_pub_1 = factories.Silo(owner=user, name='pub_1', public=True)
        silo_pub_2 = factories.Silo(owner=user, name='pub_2', public=True)
        silo_priv_1 = factories.Silo(owner=user, name='priv_1', public=False)
        silo_shared_1 = factories.Silo(owner=user, name='shared_1', public=False,
                       shared=[user_stranger])

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
        self.assertEqual(response.status_code, 200)

    @override_settings(TOLA_ACTIVITY_API_URL='https://api.toladata.io')
    def test_index_get_unauthenticated(self):
        request = self.factory.get('', follow=True)
        request.user = AnonymousUser()
        response = views.IndexView.as_view()(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('https://api.toladata.io', response.url)

    @override_settings(TOLA_ACTIVITY_API_URL='https://api.toladata.io')
    def test_index_get_login_process(self):
        request = self.factory.get('', follow=True)
        request.user = AnonymousUser()
        request.META['HTTP_REFERER'] = 'https://api.toladata.io'
        response = views.IndexView.as_view()(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('login/tola', response.url)

    @override_settings(TOLA_ACTIVITY_API_URL=None)
    def test_index_get_unauthenticated_no_activity_api_url(self):
        request = self.factory.get('')
        request.user = AnonymousUser()
        with self.assertRaises(ImproperlyConfigured):
            views.IndexView.as_view()(request)
