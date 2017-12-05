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
        silo = factories.Silo()
        user = silo.owner

        request = self.factory.get('', follow=True)
        request.user = user
        response = views.IndexView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        import pdb; pdb.set_trace()

    def test_index_get_authenticated(self):
        silo = factories.Silo()
        user = silo.owner

        request = self.factory.get('', follow=True)
        request.user = user
        response = views.IndexView.as_view()(request)
        self.assertEqual(response.status_code, 200)

    @override_settings(ACTIVITY_URL='https://api.toladata.io')
    def test_index_get_unauthenticated(self):
        request = self.factory.get('', follow=True)
        request.user = AnonymousUser()
        response = views.IndexView.as_view()(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('https://api.toladata.io', response.url)

    @override_settings(ACTIVITY_URL=None)
    def test_index_get_unauthenticated_no_activity_url(self):
        request = self.factory.get('')
        request.user = AnonymousUser()
        with self.assertRaises(ImproperlyConfigured):
            views.IndexView.as_view()(request)
