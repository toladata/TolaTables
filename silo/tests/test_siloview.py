import os
from django.test import TestCase

from rest_framework.test import APIRequestFactory

import factories
import json
from silo.api import SiloViewSet
from silo.models import LabelValueStore
from tola.util import save_data_to_silo


class SiloListViewTest(TestCase):
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


class SiloRetrieveViewTest(TestCase):
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


class SiloDataViewTest(TestCase):
    def _import_json(self, silo, read):
        filename = os.path.join(os.path.dirname(__file__),
                                'sample_data/moviesbyearnings2013.json')
        with open(filename, 'r') as f:
            data = json.load(f)
            save_data_to_silo(silo, data, read)

    def setUp(self):
        self.factory = APIRequestFactory()
        self.tola_user = factories.TolaUser()

        self.read = factories.Read(read_name="test_data",
                                   owner=self.tola_user.user)
        self.silo = factories.Silo(owner=self.tola_user.user,
                                   reads=[self.read])
        self._import_json(self.silo, self.read)

    def tearDown(self):
        # Have to remove the created lvs
        lvss = LabelValueStore.objects.filter(silo_id=self.silo.id)
        for lvs in lvss:
            lvs.delete()

    def test_data_silo(self):
        request = self.factory.get('/api/silo/{}/data'.format(self.silo.id))
        request.user = self.tola_user.user
        view = SiloViewSet.as_view({'get': 'data'})
        response = view(request, id=self.silo.id)
        self.assertEqual(response.status_code, 200)
        json_content = json.loads(response.content)
        self.assertEqual(json_content['recordsTotal'], 20)
        self.assertEqual(json_content['recordsFiltered'], 20)

    def test_data_silo_empty_table(self):
        read = factories.Read(read_name="test_empty", owner=self.tola_user.user)
        silo = factories.Silo(owner=self.tola_user.user, reads=[read])

        request = self.factory.get('/api/silo/{}/data'.format(silo.id))
        request.user = self.tola_user.user
        view = SiloViewSet.as_view({'get': 'data'})
        response = view(request, id=silo.id)
        self.assertEqual(response.status_code, 200)
        json_content = json.loads(response.content)
        self.assertEqual(json_content['recordsTotal'], 0)
        self.assertEqual(json_content['recordsFiltered'], 0)

    def test_data_silo_query(self):
        query = '{"opn": "2015-11"}'
        request = self.factory.get('/api/silo/{}/data?query={}'.format(
            self.silo.id, query))
        request.user = self.tola_user.user
        view = SiloViewSet.as_view({'get': 'data'})
        response = view(request, id=self.silo.id)
        self.assertEqual(response.status_code, 200)
        json_content = json.loads(response.content)

        self.assertEqual(json_content['recordsTotal'], 3)
        self.assertEqual(json_content['recordsFiltered'], 3)

    def test_data_silo_group(self):
        group = '{"_id": null,"total_cnt":{"$sum":"$cnt"}}'
        request = self.factory.get('/api/silo/{}/data?group={}'.format(
            self.silo.id, group))
        request.user = self.tola_user.user
        view = SiloViewSet.as_view({'get': 'data'})
        response = view(request, id=self.silo.id)
        self.assertEqual(response.status_code, 200)
        json_content = json.loads(response.content)

        self.assertEqual(json_content['recordsTotal'], 1)
        self.assertEqual(json_content['recordsFiltered'], 1)
        res = json_content['data'][0]
        self.assertEqual(res['total_cnt'], 74376)

    def test_data_silo_query_group(self):
        query = '{"opn": "2015-11"}'
        group = '{"_id": null,"total_cnt":{"$sum":"$cnt"}}'
        request = self.factory.get('/api/silo/{}/data?query={}&group={}'.format(
            self.silo.id, query, group))
        request.user = self.tola_user.user
        view = SiloViewSet.as_view({'get': 'data'})
        response = view(request, id=self.silo.id)
        self.assertEqual(response.status_code, 200)
        json_content = json.loads(response.content)

        self.assertEqual(json_content['recordsTotal'], 1)
        self.assertEqual(json_content['recordsFiltered'], 1)
        res = json_content['data'][0]
        self.assertEqual(res['total_cnt'], 11746)

    def test_data_silo_sort(self):
        query = '{"opn": "2015-11"}'
        request = self.factory.get('/api/silo/{}/data?query={}'.format(
            self.silo.id, query))
        request.user = self.tola_user.user
        view = SiloViewSet.as_view({'get': 'data'})
        response = view(request, id=self.silo.id)
        self.assertEqual(response.status_code, 200)
        json_content = json.loads(response.content)

        data = json_content['data']
        last_rank = int(data[0]['rank'])
        for d in data[1:]:
            current_rank = int(d['rank'])
            self.assertTrue(last_rank < current_rank)
            last_rank = current_rank
