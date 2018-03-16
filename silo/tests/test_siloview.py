from django.test import TestCase

from rest_framework.test import APIRequestFactory

import factories
from silo.api import SiloViewSet


class SiloListViewsTest(TestCase):
    def setUp(self):
        factories.Organization(id=1)
        factories.Silo.create_batch(2)
        self.factory = APIRequestFactory()
        self.user = factories.User(first_name='Homer', last_name='Simpson')
        self.tola_user = factories.TolaUser(user=self.user)

    def test_list_silo_superuser(self):
        request = self.factory.get('/api/silo/')
        request.user = factories.User.build(is_superuser=True,
                                            is_staff=True)
        view = SiloViewSet.as_view({'get': 'list'})
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_list_silo_normal_user(self):
        request = self.factory.get('/api/silo/')
        request.user = self.tola_user.user
        view = SiloViewSet.as_view({'get': 'list'})
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

        factories.Silo(owner=self.tola_user.user)
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_list_silo_shared(self):
        user = factories.User(first_name='Marge', last_name='Simpson')
        factories.Silo(owner=user, shared=[self.user])

        request = self.factory.get('/api/silo/?user_uuid={}'.format(
            self.tola_user.tola_user_uuid))
        request.user = self.tola_user.user
        view = SiloViewSet.as_view({'get': 'list'})
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)


class SiloRetrieveViewsTest(TestCase):
    def setUp(self):
        factories.Organization(id=1)
        self.silos = factories.Silo.create_batch(2)
        self.factory = APIRequestFactory()
        self.user = factories.User(first_name='Homer', last_name='Simpson')
        self.tola_user = factories.TolaUser(user=self.user)

    def test_retrieve_silo_superuser(self):
        request = self.factory.get('/api/silo/')
        request.user = factories.User.build(is_superuser=True,
                                            is_staff=True)
        view = SiloViewSet.as_view({'get': 'retrieve'})
        response = view(request, id=self.silos[0].id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['name'], self.silos[0].name)

    def test_retrieve_silo_normal_user(self):
        request = self.factory.get('/api/silo/')
        request.user = self.tola_user.user
        view = SiloViewSet.as_view({'get': 'retrieve'})
        response = view(request, id=self.silos[0].id)
        self.assertEqual(response.status_code, 404)

        silo = factories.Silo(name='My Silo', owner=self.tola_user.user)
        response = view(request, id=silo.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['name'], silo.name)
