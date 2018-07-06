import os
from django.test import TestCase

from rest_framework.test import APIRequestFactory

import factories
import json
import random
from silo.api import SiloViewSet
from silo.models import LabelValueStore, Silo
from tola.util import save_data_to_silo
from silo.views import merge_two_silos


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
        # Have to remove the created lvs
        lvss = LabelValueStore.objects.filter(silo_id=self.silo.id)
        for lvs in lvss:
            lvs.delete()
        self._import_json(self.silo, self.read)

    def test_data_silo_superuser(self):
        another_user = factories.User(first_name='Homer',
                                      last_name='Simpson', is_superuser=True)
        factories.TolaUser(user=another_user)

        request = self.factory.get('/api/silo/{}/data'.format(self.silo.id))
        request.user = another_user
        view = SiloViewSet.as_view({'get': 'data'})
        response = view(request, id=self.silo.id)

        self.assertEqual(response.status_code, 200)
        json_content = json.loads(response.content)
        self.assertEqual(json_content['recordsTotal'], 20)
        self.assertEqual(json_content['recordsFiltered'], 20)

    def test_data_silo_owner(self):
        request = self.factory.get('/api/silo/{}/data'.format(self.silo.id))
        request.user = self.tola_user.user
        view = SiloViewSet.as_view({'get': 'data'})
        response = view(request, id=self.silo.id)
        self.assertEqual(response.status_code, 200)
        json_content = json.loads(response.content)
        self.assertEqual(json_content['recordsTotal'], 20)
        self.assertEqual(json_content['recordsFiltered'], 20)

    def test_data_silo_empty_table(self):
        read = factories.Read(read_name="test_empty",
                              owner=self.tola_user.user)
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
        request = self.factory.get('/api/silo/{}/data?query={}&group='
                                   '{}'.format(self.silo.id, query, group))
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


class MergeTwoSilosTest(TestCase):
    def setUp(self):
        self.mapping_data = """{
                "0": {
                    "left_table_cols": ["number"],
                    "right_table_col": "number",
                    "merge_type": ""
                },
                "left_unmapped_cols": ["first name"],
                "right_unmapped_cols": ["last name"]
            }"""
        self.user = factories.User(username='test_user')

    def tearDown(self):
        LabelValueStore.objects.delete()

    def _create_silo(self, name, number, value, option):
        silo = factories.Silo(owner=self.user, name=name, public=True)
        silo_row = factories.LabelValueStore(silo_id=silo.pk)
        silo_row['number'] = number
        if option == 'left':
            silo_row['first name'] = value
        elif option == 'right':
            silo_row['last name'] = value
        silo_row.save()
        return silo

    def test_merge_silo(self):
        left_silo = self._create_silo('left_silo', 1, 'Bob', 'left')
        factories.UniqueFields(silo=left_silo, name='number')

        right_silo = self._create_silo('right_silo', 1, 'Marley', 'right')
        factories.UniqueFields(silo=right_silo, name='number')

        merged_silo = factories.Silo(owner=self.user,
                                     name='merged_silo',
                                     public=True)

        response = merge_two_silos(self.mapping_data, left_silo.pk,
                                   right_silo.pk, merged_silo.pk)

        self.assertEqual(response,
                         {'status': "success",
                          'message': "Merged data successfully"})

        merged_silo = Silo.objects.get(pk=merged_silo.pk)
        self.assertEqual(
            LabelValueStore.objects.filter(silo_id=merged_silo.pk).count(), 1)

        merged_silo_row = LabelValueStore.objects.get(silo_id=merged_silo.pk)
        self.assertEqual(merged_silo_row['first name'], 'Bob')
        self.assertEqual(merged_silo_row['last name'], 'Marley')

    def test_merge_silos_without_unique_field_in_left_silo(self):
        left_silo = self._create_silo('left_silo', 1, 'Bob', 'left')

        right_silo = self._create_silo('right_silo', 1, 'Marley', 'right')
        factories.UniqueFields(silo=right_silo, name='number')

        merged_silo = factories.Silo(owner=self.user,
                                     name='merged_silo',
                                     public=True)

        response = merge_two_silos(self.mapping_data, left_silo.pk,
                                   right_silo.pk, merged_silo.pk)

        self.assertEqual(response,
                         {'status': "danger",
                          'message': "The silo, [%s], must have a unique "
                                     "column and it should be the same as the "
                                     "one specified in [%s] silo." %
                                     (left_silo.name, right_silo.name)})

    def test_merge_silos_without_unique_field_in_right_silo(self):
        left_silo = self._create_silo('left_silo', 1, 'Bob', 'left')
        factories.UniqueFields(silo=left_silo, name='number')

        right_silo = self._create_silo('right_silo', 1, 'Marley', 'right')

        merged_silo = factories.Silo(owner=self.user,
                                     name='merged_silo',
                                     public=True)

        response = merge_two_silos(self.mapping_data, left_silo.pk,
                                   right_silo.pk, merged_silo.pk)

        self.assertEqual(response,
                         {'status': "danger",
                          'message': "The silo, [%s], must have a unique "
                                     "column and it should be the same as the "
                                     "one specified in [%s] silo." %
                                     (right_silo.name, left_silo.name)})

    def test_merge_silos_without_left_silo(self):
        left_silo_random_id = random.randint(1, 9999)

        right_silo = self._create_silo('right_silo', 1, 'Marley', 'right')
        factories.UniqueFields(silo=right_silo, name='number')

        merged_silo = factories.Silo(owner=self.user,
                                     name='merged_silo',
                                     public=True)

        response = merge_two_silos(self.mapping_data, left_silo_random_id,
                                   right_silo.pk, merged_silo.pk)

        self.assertEqual(response,
                         {'status': "danger",
                          'message': "Left Silo does not exist: "
                                     "silo_id=%s" % left_silo_random_id})

    def test_merge_silos_without_right_silo(self):
        left_silo = self._create_silo('left_silo', 1, 'Bob', 'left')
        factories.UniqueFields(silo=left_silo, name='number')

        right_silo_random_id = random.randint(1, 9999)

        merged_silo = factories.Silo(owner=self.user,
                                     name='merged_silo',
                                     public=True)

        response = merge_two_silos(self.mapping_data, left_silo.pk,
                                   right_silo_random_id, merged_silo.pk)

        self.assertEqual(response,
                         {'status': "danger",
                          'message': "Right Silo does not exist: "
                                     "silo_id=%s" % right_silo_random_id})

    def test_merge_silos_without_merged_silo(self):
        left_silo = self._create_silo('left_silo', 1, 'Bob', 'left')
        factories.UniqueFields(silo=left_silo, name='number')

        right_silo = self._create_silo('right_silo', 1, 'Marley', 'right')
        factories.UniqueFields(silo=right_silo, name='number')

        merged_silo_random_id = random.randint(1, 9999)

        response = merge_two_silos(self.mapping_data, left_silo.pk,
                                   right_silo.pk, merged_silo_random_id)

        self.assertEqual(response,
                         {'status': "danger",
                          'message': "Merged Silo does not exist: "
                                     "silo_id=%s" % merged_silo_random_id})

    def test_merge_silos_with_different_unique_fields(self):
        left_silo = self._create_silo('left_silo', 1, 'Bob', 'left')
        factories.UniqueFields(silo=left_silo, name='first name')

        right_silo = self._create_silo('right_silo', 1, 'Marley', 'right')
        factories.UniqueFields(silo=right_silo, name='number')

        merged_silo = factories.Silo(owner=self.user,
                                     name='merged_silo',
                                     public=True)

        response = merge_two_silos(self.mapping_data, left_silo.pk,
                                   right_silo.pk, merged_silo.pk)

        self.assertEqual(response,
                         {'status': "danger",
                          'message': "Both silos (%s, %s) must have the same "
                                     "column set as unique fields"
                                     % (left_silo.name, right_silo.name)})

    def test_merge_silos_without_mapped_columns(self):
        mapping_data = """{
                        "0": {
                              "left_table_cols": [],
                              "right_table_col": "",
                              "merge_type": ""
                        },
                        "left_unmapped_cols": ["first name"],
                        "right_unmapped_cols": ["last name"]
                    }"""
        left_silo = self._create_silo('left_silo', 1, 'Bob', 'left')
        factories.UniqueFields(silo=left_silo, name='first name')

        right_silo = self._create_silo('right_silo', 1, 'Marley', 'right')
        factories.UniqueFields(silo=right_silo, name='number')

        merged_silo = factories.Silo(owner=self.user,
                                     name='merged_silo',
                                     public=True)

        response = merge_two_silos(mapping_data, left_silo.pk,
                                   right_silo.pk, merged_silo.pk)

        self.assertEqual(response,
                         {'status': "danger",
                          'message': "Both silos (%s, %s) must have the same "
                                     "column set as unique fields"
                                     % (left_silo.name, right_silo.name)})

    def test_merge_silo_with_specified_merge_type(self):
        mapping_data = """{
                        "0": {
                              "left_table_cols": ["number", "points"],
                              "right_table_col": "number",
                              "merge_type": "Avg"
                        },
                        "left_unmapped_cols": [],
                        "right_unmapped_cols": []
                    }"""

        user = factories.User(username='test_user')
        left_silo = factories.Silo(owner=user, name='left_silo', public=True)
        left_silo_r = factories.LabelValueStore(silo_id=left_silo.pk)
        left_silo_r['number'] = 1
        left_silo_r['points'] = 5
        left_silo_r.save()
        left_silo_r2 = factories.LabelValueStore(silo_id=left_silo.pk)
        left_silo_r2['number'] = 2
        left_silo_r2['points'] = 7
        left_silo_r2.save()
        factories.UniqueFields(silo=left_silo, name='number')

        right_silo = factories.Silo(owner=user, name='right_silo', public=True)
        right_silo_r = factories.LabelValueStore(silo_id=right_silo.pk)
        right_silo_r['number'] = 1
        right_silo_r.save()
        right_silo_r2 = factories.LabelValueStore(silo_id=right_silo.pk)
        right_silo_r2['number'] = 2
        right_silo_r2.save()
        factories.UniqueFields(silo=right_silo, name='number')

        merged_silo = factories.Silo(owner=user,
                                     name='merged_silo',
                                     public=True)

        response = merge_two_silos(mapping_data, left_silo.pk,
                                   right_silo.pk, merged_silo.pk)

        self.assertEqual(response,
                         {'status': "success",
                          'message': "Merged data successfully"})

        merged_silo = Silo.objects.get(pk=merged_silo.pk)
        self.assertEqual(
            LabelValueStore.objects.filter(silo_id=merged_silo.pk).count(), 4)

        merged_silo_rows = LabelValueStore.objects.filter(
            silo_id=merged_silo.pk)
        self.assertEqual(merged_silo_rows[0]['number'], 1)
        self.assertEqual(merged_silo_rows[1]['number'], 2)
        self.assertEqual(merged_silo_rows[2]['number'], 3.0)
        self.assertEqual(merged_silo_rows[3]['number'], 4.5)

    def test_merge_silo_with_objectId_unique_field(self):
        left_silo = self._create_silo('left_silo', 1, 'Bob', 'left')
        factories.UniqueFields(silo=left_silo, name='_id')
        right_silo = self._create_silo('right_silo', 1, 'Marley', 'right')
        factories.UniqueFields(silo=right_silo, name='_id')

        merged_silo = factories.Silo(owner=self.user,
                                     name='merged_silo',
                                     public=True)

        response = merge_two_silos(self.mapping_data, left_silo.pk,
                                   right_silo.pk, merged_silo.pk)

        self.assertEqual(response,
                         {'status': "success",
                          'message': "Merged data successfully"})

        merged_silo = Silo.objects.get(pk=merged_silo.pk)
        self.assertEqual(
            LabelValueStore.objects.filter(silo_id=merged_silo.pk).count(), 1)

        merged_silo_row = LabelValueStore.objects.get(silo_id=merged_silo.pk)
        self.assertEqual(merged_silo_row['first name'], 'Bob')
        self.assertEqual(merged_silo_row['last name'], 'Marley')

    def test_merge_silo_with_datetime_unique_field(self):
        left_silo = self._create_silo('left_silo', 1, 'Bob', 'left')
        factories.UniqueFields(silo=left_silo, name='created_date')

        right_silo = self._create_silo('right_silo', 1, 'Marley', 'right')
        factories.UniqueFields(silo=right_silo, name='created_date')

        merged_silo = factories.Silo(owner=self.user,
                                     name='merged_silo',
                                     public=True)

        response = merge_two_silos(self.mapping_data, left_silo.pk,
                                   right_silo.pk, merged_silo.pk)

        self.assertEqual(response,
                         {'status': "success",
                          'message': "Merged data successfully"})

        merged_silo = Silo.objects.get(pk=merged_silo.pk)
        self.assertEqual(
            LabelValueStore.objects.filter(silo_id=merged_silo.pk).count(), 1)

        merged_silo_row = LabelValueStore.objects.get(silo_id=merged_silo.pk)
        self.assertEqual(merged_silo_row['first name'], 'Bob')
        self.assertEqual(merged_silo_row['last name'], 'Marley')
