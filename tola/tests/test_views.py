from django.test import Client, TestCase, RequestFactory
from django.conf import settings
from django.contrib import auth

import factories
from tola.views import register
from urlparse import urljoin


class RegisterViewTest(TestCase):
    def setUp(self):
        self.tola_user = factories.TolaUser(user=factories.User())
        self.factory = RequestFactory()

    def test_post_success_with_superuser(self):
        """
        Only superusers are allowed to send a post to this endpoint
        """
        self.tola_user.user.is_staff = True
        self.tola_user.user.is_superuser = True
        self.tola_user.user.save()

        data = {
            'first_name': 'John',
            'last_name': 'Lennon',
            'email': 'john_lennon@test.de',
            'username': 'john_lennon',
            'password1': 1234,
            'password2': 1234,
            'title': '',
            'privacy_diclaimer_accepted': 'on',
            'org': self.tola_user.organization.name,
            'tola_user_uuid': 1234567890
        }

        request = self.factory.post('/accounts/register/', data)
        request.user = self.tola_user.user
        request._dont_enforce_csrf_checks = True
        response = register(request)

        self.assertEqual(response.status_code, 201)

    def test_post_nouuid_with_superuser(self):
        """
        Post without tola_user_uuid gets a bad request
        """
        self.tola_user.user.is_staff = True
        self.tola_user.user.is_superuser = True
        self.tola_user.user.save()

        data = {
            'first_name': 'John',
            'last_name': 'Lennon',
            'email': 'john_lennon@test.de',
            'username': 'john_lennon',
            'password1': 1234,
            'password2': 1234,
            'title': '',
            'privacy_diclaimer_accepted': 'on',
            'org': self.tola_user.organization.name
        }

        request = self.factory.post('/accounts/register/', data)
        request.user = self.tola_user.user
        request._dont_enforce_csrf_checks = True
        response = register(request)

        self.assertEqual(response.status_code, 400)

    def test_post_invalid_form_with_superuser(self):
        """
        Post with an invalid form gets a bad request
        """
        self.tola_user.user.is_staff = True
        self.tola_user.user.is_superuser = True
        self.tola_user.user.save()

        data = {
            'first_name': 'John',
            'last_name': 'Lennon',
            'email': 'john_lennon@test.de',
            'username': 'john_lennon',
            'title': '',
            'privacy_diclaimer_accepted': 'on',
            'org': self.tola_user.organization.name,
            'tola_user_uuid': 1234567890
        }

        request = self.factory.post('/accounts/register/', data)
        request.user = self.tola_user.user
        request._dont_enforce_csrf_checks = True
        response = register(request)

        self.assertEqual(response.status_code, 400)

    def test_post_unsuccess_with_normaluser(self):
        """
        Normal users are not allowed to send a post to this endpoint
        """
        data = {
            'first_name': 'John',
            'last_name': 'Lennon',
            'email': 'john_lennon@test.de',
            'username': 'john_lennon',
            'password1': 1234,
            'password2': 1234,
            'title': '',
            'privacy_diclaimer_accepted': 'on',
            'org': self.tola_user.organization.name,
            'tola_user_uuid': 1234567890
        }

        request = self.factory.post('/accounts/register/', data)
        request.user = self.tola_user.user
        request._dont_enforce_csrf_checks = True
        response = register(request)

        self.assertEqual(response.status_code, 403)


class LogoutViewTest(TestCase):
    def setUp(self):
        self.user = factories.User()
        self.user.set_password(12345)
        self.user.save()
        self.tola_user = factories.TolaUser(user=self.user)
        self.factory = RequestFactory()

    def test_logout_redirect_logout_activity(self):
        c = Client()
        c.post('/accounts/login/', {'username': self.user.username,
                                    'password': '12345'})
        self.user = auth.get_user(c)
        self.assertEqual(self.user.is_authenticated(), True)

        response = c.post('/accounts/logout/')
        self.user = auth.get_user(c)
        self.assertEqual(self.user.is_authenticated(), False)
        self.assertEqual(response.status_code, 302)

        url_subpath = 'accounts/logout/'
        redirect_url = urljoin(settings.TABLES_LOGIN_URL, url_subpath)
        self.assertEqual(response.url, redirect_url)

    def test_logout_redirect_to_activity(self):
        c = Client()
        response = c.post('/accounts/logout/')
        self.user = auth.get_user(c)
        self.assertEqual(self.user.is_authenticated(), False)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, settings.TABLES_LOGIN_URL)
