from django.test import TestCase

from rest_framework.test import APIRequestFactory

import factories
from silo.api import ReadViewSet
from silo.models import Read
from django.urls import reverse


class ReadListViewTest(TestCase):
    def setUp(self):
        factories.Organization(id=1)
        factories.Read.create_batch(4)
        self.factory = APIRequestFactory()
        self.user = factories.User(first_name='Homer', last_name='Simpson')
        self.tola_user = factories.TolaUser(user=self.user)

    def test_list_read_superuser(self):
        request = self.factory.get('/api/read/')
        request.user = factories.User.build(is_superuser=True,
                                            is_staff=True)
        view = ReadViewSet.as_view({'get': 'list'})
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 4)

    def test_list_read_owner(self):
        request = self.factory.get('/api/read/')
        request.user = self.tola_user.user
        view = ReadViewSet.as_view({'get': 'list'})
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

        factories.Read(owner=self.tola_user.user)
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_list_read_public(self):
        request = self.factory.get('/api/read/')
        request.user = self.tola_user.user
        view = ReadViewSet.as_view({'get': 'list'})
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

        owner = factories.User()
        read = factories.Read(read_name='It is public', owner=owner)
        factories.Silo(public=True, reads=[read])

        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_list_read_shared(self):
        request = self.factory.get('/api/read/')
        request.user = self.tola_user.user
        view = ReadViewSet.as_view({'get': 'list'})
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

        owner = factories.User()
        read = factories.Read(read_name='It is shared', owner=owner)
        factories.Silo(shared=[self.tola_user.user], reads=[read])

        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)


class ReadRetrieveViewTest(TestCase):
    def setUp(self):
        factories.Organization(id=1)
        self.user = factories.User(first_name='Homer', last_name='Simpson')
        self.tola_user = factories.TolaUser(user=self.user)
        self.read = factories.Read(read_name="test_data",
                                   owner=self.tola_user.user)
        self.silo = factories.Silo(owner=self.tola_user.user,
                                   reads=[self.read])
        self.factory = APIRequestFactory()

    def test_retrieve_read_superuser(self):
        request = self.factory.get('/api/read/')
        request.user = factories.User.build(is_superuser=True,
                                            is_staff=True)
        view = ReadViewSet.as_view({'get': 'retrieve'})
        response = view(request, pk=self.read.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['read_name'], self.read.read_name)

    def test_retrieve_read_owner(self):
        request = self.factory.get('/api/read/')
        request.user = factories.User.build(is_superuser=False,
                                            is_staff=False)
        view = ReadViewSet.as_view({'get': 'retrieve'})
        response = view(request, pk=self.read.id)
        self.assertEqual(response.status_code, 404)

        request = self.factory.get('/api/read/')
        request.user = self.tola_user.user

        response = view(request, pk=self.read.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['read_name'], self.read.read_name)

    def test_retrieve_read_public(self):
        user = factories.User(is_superuser=False, is_staff=False)

        request = self.factory.get('/api/read/')
        request.user = user
        view = ReadViewSet.as_view({'get': 'retrieve'})
        response = view(request, pk=self.read.id)
        self.assertEqual(response.status_code, 404)

        read = factories.Read(read_name='It is public',
                              owner=self.tola_user.user)
        factories.Silo(public=True, reads=[read])

        response = view(request, pk=read.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['read_name'], 'It is public')

    def test_retrieve_read_shared(self):
        shared_user = factories.User(is_superuser=False, is_staff=False)

        request = self.factory.get('/api/read/')
        request.user = shared_user
        view = ReadViewSet.as_view({'get': 'retrieve'})
        response = view(request, pk=self.read.id)
        self.assertEqual(response.status_code, 404)

        read = factories.Read(read_name='It is shared',
                              owner=self.tola_user.user)
        factories.Silo(shared=[shared_user], reads=[read])

        response = view(request, pk=read.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['read_name'], 'It is shared')


class ReadCreateViewTest(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.tola_user = factories.TolaUser()

        self.read = factories.Read(read_name="test_data",
                                   owner=self.tola_user.user)

        self.read_type = factories.ReadType.create(read_type='CSV')

    def test_create_read(self):
        data = {
            "type": reverse('readtype-detail',
                            kwargs={'pk': self.read_type.id}),
            "owner": reverse('user-detail',
                             kwargs={'pk': self.tola_user.user.id}),
            "read_name": "test",
            "read_url": "",
            "autopull_frequency": "daily",
            "autopush_frequency": "weekly",
            "autopull_expiration": "",
            "autopush_expiration": ""
            }

        request = self.factory.post('/api/read/', data)
        request.user = self.tola_user.user
        view = ReadViewSet.as_view({'post': 'create'})
        response = view(request)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['read_name'],
                         data['read_name'])

        self.assertEqual(response.data['autopull_frequency'],
                         data['autopull_frequency'])
        self.assertEqual(response.data['autopush_frequency'],
                         data['autopush_frequency'])

        self.assertContains(response, "/api/users/"+str(
            self.tola_user.user.id), status_code=201)
        self.assertContains(response, "/api/readtype/"+str(
            self.read_type.id), status_code=201)

        created_read = Read.objects.get(id=response.data['pk'])
        self.assertEqual(created_read.read_name, data["read_name"])


class ReadUpdateViewTest(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.tola_user = factories.TolaUser()

        self.read = factories.Read(read_name="test_data",
                                   owner=self.tola_user.user)

        self.read_type = factories.ReadType.create(read_type='CSV')

    def test_update_read_super_user(self):
        self.tola_user.user.is_superuser = True
        self.tola_user.user.save()

        another_user = factories.User(first_name='Homer', last_name='Simpson')
        silo = factories.Silo(owner=another_user, public=True)
        new_read = factories.Read(read_name="test_data",
                                  autopull_frequency="daily",
                                  autopush_frequency="daily",
                                  owner=another_user)
        silo.reads.add(new_read)

        data = {
            "type": reverse('readtype-detail',
                            kwargs={'pk': self.read_type.id}),
            "owner": reverse('user-detail',
                             kwargs={'pk': self.tola_user.user.id}),
            "autopull_frequency": "weekly",
            "autopush_frequency": "weekly",
        }

        request = self.factory.post('/api/read/', data)
        request.user = self.tola_user.user
        view = ReadViewSet.as_view({'post': 'update'})
        response = view(request, pk=new_read.pk)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['read_name'],
                         new_read.read_name)
        self.assertEqual(response.data['autopull_frequency'],
                         data['autopull_frequency'])
        self.assertEqual(response.data['autopush_frequency'],
                         data['autopush_frequency'])

        self.assertContains(response, "/api/users/" + str(
            self.tola_user.user.id), status_code=200)
        self.assertContains(response, "/api/readtype/" + str(
            self.read_type.id), status_code=200)

        updated_read = Read.objects.get(id=new_read.pk)
        self.assertEqual(updated_read.autopull_frequency,
                         data["autopull_frequency"])
        self.assertEqual(updated_read.autopush_frequency,
                         data["autopush_frequency"])

    def test_update_read_owner(self):
        new_read = factories.Read(read_name="test_data",
                                  autopull_frequency="daily",
                                  autopush_frequency="daily",
                                  owner=self.tola_user.user)

        data = {
            "type": reverse('readtype-detail',
                            kwargs={'pk': self.read_type.id}),
            "owner": reverse('user-detail',
                             kwargs={'pk': self.tola_user.user.id}),
            "autopull_frequency": "weekly",
            "autopush_frequency": "weekly",
        }

        request = self.factory.post('/api/read/', data)
        request.user = self.tola_user.user
        view = ReadViewSet.as_view({'post': 'update'})
        response = view(request, pk=new_read.pk)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['read_name'],
                         new_read.read_name)
        self.assertEqual(response.data['autopull_frequency'],
                         data['autopull_frequency'])
        self.assertEqual(response.data['autopush_frequency'],
                         data['autopush_frequency'])

        self.assertContains(response, "/api/users/" + str(
            self.tola_user.user.id), status_code=200)
        self.assertContains(response, "/api/readtype/" + str(
            self.read_type.id), status_code=200)

        updated_read = Read.objects.get(id=new_read.pk)
        self.assertEqual(updated_read.autopull_frequency,
                         data["autopull_frequency"])
        self.assertEqual(updated_read.autopush_frequency,
                         data["autopush_frequency"])

    def test_update_read_not_owner(self):
        another_user = factories.User(first_name='Homer', last_name='Simpson')
        silo = factories.Silo(owner=another_user, public=True)
        new_read = factories.Read(read_name="test_data",
                                  autopull_frequency="daily",
                                  autopush_frequency="daily",
                                  owner=another_user)
        silo.reads.add(new_read)

        data = {
            "type": reverse('readtype-detail',
                            kwargs={'pk': self.read_type.id}),
            "autopull_frequency": "weekly",
            "autopush_frequency": "weekly",
        }

        request = self.factory.post('/api/read/', data)
        request.user = self.tola_user.user
        view = ReadViewSet.as_view({'post': 'update'})
        response = view(request, pk=new_read.pk)

        self.assertEqual(response.status_code, 403)
