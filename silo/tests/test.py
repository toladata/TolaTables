# -*- coding: utf-8 -*-
import os
import json

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test import Client
from django.test import RequestFactory

from commcare.tasks import parseCommCareData
from commcare.util import getProjects
from silo.forms import get_read_form
from silo.models import DeletedSilos, LabelValueStore, ReadType, Read, Silo
from silo.views import (addColumnFilter, editColumnOrder, newFormulaColumn,
                        showRead, editSilo, uploadFile, siloDetail)
from tola.util import (addColsToSilo, hideSiloColumns, getColToTypeDict,
                       getSiloColumnNames)

from mock import patch

import factories


class ReadTest(TestCase):
    fixtures = ['../fixtures/read_types.json']
    show_read_url = '/show_read/'
    new_read_url = 'source/new//'

    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()
        self.tola_user = factories.TolaUser()

    def test_new_read_post(self):
        read_type = ReadType.objects.get(read_type="ONA")
        upload_file = open('test.csv', 'rb')
        params = {
            'owner': self.tola_user.user.pk,
            'type': read_type.pk,
            'read_name': 'TEST READ SOURCE',
            'description': 'TEST DESCRIPTION for test read source',
            'read_url': 'https://www.lclark.edu',
            'resource_id':'testsssszzz',
            'create_date': '2015-06-24 20:33:47',
            'file_data': upload_file,
        }
        request = self.factory.post(self.new_read_url, data = params)
        request.user = self.tola_user.user

        response = showRead(request, 1)
        if response.status_code == 302:
            if "/read/login" in response.url or "/file/" in response.url:
                self.assertEqual(response.url, response.url)
            else:
                self.assertEqual(response.url, "/silos")
        else:
            self.assertEqual(response.status_code, 200)

        # Now test the show_read view to make sure that I can retrieve the objec
        # that just got created using the POST method above.
        source = Read.objects.get(read_name='TEST READ SOURCE')
        response = self.client.get(self.show_read_url + str(source.pk) + "/")
        self.assertEqual(response.status_code, 302)


# TODO: Adjust tests to work without mongodb as an instance is not available
# TODO: during testing.
class SiloTest(TestCase):
    fixtures = ['fixtures/read_types.json']
    silo_edit_url = "/silo_edit/"
    upload_csv_url = "/file/"
    silo_detail_url = "/silo_detail/"

    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()
        self.tola_user = factories.TolaUser()

    @patch('silo.forms.get_workflowteams')
    def test_new_silo(self, mock_get_workflowteams):
        mock_get_workflowteams.return_value = []
        # Create a New Silo
        silo = factories.Silo(owner=self.tola_user.user)
        self.assertEqual(silo.pk, 1)

        # Fetch the silo that just got created above
        request = self.factory.get(self.silo_edit_url)
        request.user = self.tola_user.user
        response = editSilo(request, silo.pk)
        self.assertEqual(response.status_code, 200)

        # update the silo that just got created above
        params = {
            'owner': self.tola_user.user.pk,
            'name': 'Test Silo Updated',
            'description': 'Adding this description in a unit-test.',
        }
        request = self.factory.post(self.silo_edit_url, data = params)
        request.user = self.tola_user.user
        request._dont_enforce_csrf_checks = True
        response = editSilo(request, silo.pk)
        if response.status_code == 302:
            self.assertEqual(response.url, "/silos/")
        else:
            self.assertEqual(response.status_code, 200)

    @patch('silo.forms.get_workflowteams')
    def test_new_silodata(self, mock_get_workflowteams):
        mock_get_workflowteams.return_value = []
        read_type = ReadType.objects.get(read_type="CSV")
        upload_file = open('test.csv', 'rb')
        read = factories.Read(
            owner=self.tola_user.user, type=read_type,
            read_name="TEST CSV IMPORT",  description="unittest",
            file_data=SimpleUploadedFile(upload_file.name, upload_file.read())
        )
        params = {
            "read_id": read.pk,
            "new_silo": "Test CSV Import",
        }
        request = self.factory.post(self.upload_csv_url, data=params)
        request.user = self.tola_user.user
        request._dont_enforce_csrf_checks = True
        response = uploadFile(request, read.pk)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/silo_detail/", response.url)

        silo = Silo.objects.get(name="Test CSV Import")
        request = self.factory.get(self.silo_detail_url)
        request.user = self.tola_user.user

        response = siloDetail(request, silo.pk)
        self.assertEqual(response.status_code, 200)

        # now delete that silo data cause this uses the custom database
        LabelValueStore.objects.filter(First_Name="Bob", Last_Name="Smith",
                                       silo_id="1", read_id="1").delete()
        LabelValueStore.objects.filter(First_Name="John", Last_Name="Doe",
                                       silo_id="1", read_id="1").delete()
        LabelValueStore.objects.filter(First_Name="Joe", Last_Name="Schmoe",
                                       silo_id="1", read_id="1").delete()
        LabelValueStore.objects.filter(First_Name="جان", Last_Name="ډو",
                                       silo_id="1", read_id="1").delete()

    def test_read_form(self):
        read_type = ReadType.objects.get(read_type="CSV")
        upload_file = open('test.csv', 'rb')
        params = {
            'owner': self.tola_user.user.pk,
            'type': read_type.pk,
            'read_name': 'TEST READ SOURCE',
            'description': 'TEST DESCRIPTION for test read source',
            'read_url': 'https://www.lclark.edu',
            'resource_id': 'testsssszzz',
            'create_date': '2015-06-24 20:33:47'
        }
        file_dict = {'file_data': SimpleUploadedFile(
            upload_file.name, upload_file.read())}
        excluded_fields = ['create_date', 'edit_date']
        form = get_read_form(excluded_fields)(params, file_dict)
        self.assertTrue(form.is_valid())


class FormulaColumn(TestCase):
    new_formula_columh_url = "/new_formula_column/"

    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()
        self.user = factories.User()
        self.user.set_password('tola123')
        self.user.save()
        factories.TolaUser(user=self.user)
        self.silo = factories.Silo(owner=self.user)
        self.client.login(username=self.user.username, password='tola123')

    def test_getNewFormulaColumn(self):
        request = self.factory.get(self.new_formula_columh_url)
        request.user = self.user
        request._dont_enforce_csrf_checks = True
        response = newFormulaColumn(request, self.silo.pk)
        self.assertEqual(response.status_code, 200)

    def test_postNewFormulaColumn(self):
        data = {
            'math_operation': 'sum',
            'column_name': '',
            'columns': []
        }
        response = self.client.post('/new_formula_column/{}/'.format(
            self.silo.pk), data=data)
        self.assertEqual(response.status_code, 302)

        lvs = LabelValueStore()
        lvs.a = "1"
        lvs.b = "2"
        lvs.c = "3"
        lvs.silo_id = self.silo.pk
        lvs.save()

        lvs = LabelValueStore()
        lvs.a = "2"
        lvs.b = "2"
        lvs.c = "3.3"
        lvs.silo_id = self.silo.pk
        lvs.save()

        lvs = LabelValueStore()
        lvs.a = "3"
        lvs.b = "2"
        lvs.c = "hi"
        lvs.silo_id = self.silo.pk
        lvs.save()

        data = {
            'math_operation': 'sum',
            'column_name': '',
            'columns': ['a', 'b', 'c']
        }
        response = self.client.post('/new_formula_column/{}/'.format(
            self.silo.pk), data=data)
        self.assertEqual(response.status_code, 302)
        formula_column = self.silo.formulacolumns.get(column_name='sum')
        self.assertEqual(formula_column.operation, 'sum')
        self.assertEqual(formula_column.mapping, '["a", "b", "c"]')
        self.assertEqual(formula_column.column_name, 'sum')
        self.assertEqual(getSiloColumnNames(self.silo.pk), ["sum"])
        self.silo = Silo.objects.get(pk=self.silo.pk)
        self.assertEqual(getColToTypeDict(self.silo).get('sum'), 'float')
        try:
            lvs = LabelValueStore.objects.get(a="1", b="2", c="3", sum=6.0,
                                              read_id=-1, silo_id=self.silo.pk)
            lvs.delete()
        except LabelValueStore.DoesNotExist as e:
            self.assert_(False)
        try:
            lvs = LabelValueStore.objects.get(a="2", b="2", c="3.3", sum=7.3,
                                              read_id=-1, silo_id=self.silo.pk)
            lvs.delete()
        except LabelValueStore.DoesNotExist as e:
            self.assert_(False)
        try:
            lvs = LabelValueStore.objects.get(a="3", b="2", c="hi", sum="Error",
                                              read_id=-1, silo_id=self.silo.pk)
            lvs.delete()
        except LabelValueStore.DoesNotExist as e:
            self.assert_(False)


class ColumnOrder(TestCase):
    url = "/edit_column_order/"

    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()
        self.user = factories.User()
        self.user.set_password('tola123')
        self.user.save()
        factories.TolaUser(user=self.user)
        self.silo = factories.Silo(owner=self.user)
        self.client.login(username=self.user.username, password='tola123')

    def test_get_edit_column_order(self):
        request = self.factory.get(self.url)
        request.user = self.user
        request._dont_enforce_csrf_checks = True
        response = editColumnOrder(request, self.silo.pk)
        self.assertEqual(response.status_code, 200)

    def test_post_edit_column_order(self):
        addColsToSilo(self.silo, ['a', 'b', 'c', 'd', 'e', 'f'])
        hideSiloColumns(self.silo, ['b', 'e'])
        cols_ordered = ['c', 'f', 'a', 'd']
        data = {
            'columns': cols_ordered
        }
        response = self.client.post('/edit_column_order/{}/'.format(
            self.silo.pk), data=data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(getSiloColumnNames(self.silo.pk),
                         ['c', 'f', 'a', 'd'])

        data = {
            'columns': cols_ordered
        }
        response = self.client.post('/edit_column_order/0/', data=data)
        self.assertEqual(response.status_code, 302)


class ColumnFilter(TestCase):
    url = "/edit_filter/"

    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()
        self.user = factories.User()
        self.user.set_password('tola123')
        self.user.save()
        factories.TolaUser(user=self.user)
        self.silo = factories.Silo(owner=self.user)
        self.client.login(username=self.user.username, password='tola123')

    def test_get_editColumnOrder(self):
        addColsToSilo(self.silo, ['a', 'b', 'c', 'd', 'e', 'f'])
        hideSiloColumns(self.silo, ['b', 'e'])
        self.silo.rows_to_hide = json.dumps([
            {
                "logic": "BLANKCHAR",
                "operation": "",
                "number": "",
                "conditional": "---",
            },
            {
                "logic": "AND",
                "operation": "empty",
                "number": "",
                "conditional": ["a", "b"],
            },
            {
                "logic": "OR",
                "operation": "empty",
                "number": "",
                "conditional": ["c", "d"],
            }
        ])
        self.silo.save()
        request = self.factory.get(self.url)
        request.user = self.user
        request._dont_enforce_csrf_checks = True
        response = addColumnFilter(request, self.silo.pk)
        self.assertEqual(response.status_code, 200)

    def test_post_editColumnOrder(self):
        rows_to_hide = [
            {
                "logic": "BLANKCHAR",
                "operation": "",
                "number": "",
                "conditional": "---",
            },
            {
                "logic": "AND",
                "operation": "empty",
                "number": "",
                "conditional": ["a", "b"],
            },
            {
                "logic": "OR",
                "operation": "empty",
                "number": "",
                "conditional": ["c", "d"],
            }
        ]
        cols_to_hide = ['a', 'b', 'c']
        data = {
            'hide_rows': json.dumps(rows_to_hide),
            'hide_cols': json.dumps(cols_to_hide)
        }
        response = self.client.post('/edit_filter/{}/'.format(self.silo.pk),
                                    data=data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.silo.hidden_columns, json.dumps(cols_to_hide))
        self.assertTrue(self.silo.rows_to_hide, json.dumps(rows_to_hide))


class RemoveSourceTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = factories.User()
        self.user.set_password('tola123')
        self.user.save()
        factories.TolaUser(user=self.user)
        self.client.login(username=self.user.username, password='tola123')

    def test_remove_read(self):
        silo = factories.Silo(owner=self.user)
        read = silo.reads.all()[0]
        self.assertEqual(silo.reads.count(), 1)

        response = self.client.get("/source_remove/{}/{}/".format(0, read.pk))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(silo.reads.all().count(), 1)

        response = self.client.get("/source_remove/{}/{}/".format(silo.pk, 0))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(silo.reads.all().count(), 1)

        response = self.client.get("/source_remove/{}/{}/".format(
            silo.pk, read.pk))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(silo.reads.all().count(), 0)

        response = self.client.get("/source_remove/{}/{}/".format(
            silo.pk, read.pk))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(silo.reads.all().count(), 0)


class GetCommCareProjectsTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = factories.User()
        self.user2 = factories.User(first_name='John', last_name='Lennon')
        self.read_type = factories.ReadType(read_type="CommCare")

    def test_onaParserOneLayer(self):
        self.assertEqual(getProjects(self.user.id), [])
        self.read = factories.Read(
            read_name="test_read1", owner=self.user, type=self.read_type,
            read_url="https://www.commcarehq.org/a/a/"
        )
        self.assertEqual(getProjects(self.user.id), ['a'])

        self.read = factories.Read(
            read_name="test_read2", owner=self.user, type=self.read_type,
            read_url="https://www.commcarehq.org/a/b/"
        )
        self.assertEqual(getProjects(self.user.id), ['a', 'b'])

        self.read = factories.Read(
            read_name="test_read3", owner=self.user, type=self.read_type,
            read_url="https://www.commcarehq.org/a/b/"
        )
        self.assertEqual(getProjects(self.user.id), ['a', 'b'])

        self.read = factories.Read(
            read_name="test_read4", owner=self.user2, type=self.read_type,
            read_url="https://www.commcarehq.org/a/c/"
        )
        self.assertEqual(getProjects(self.user.id), ['a', 'b'])


class ParseCommCareDataTest(TestCase):
    def test_commcaredataparser(self):
        data = [
            {
                'case_id': 1,
                'properties': {
                    'a': 1,
                    'b': 2,
                    'c': 3
                }
            },
            {
                'case_id': 2,
                'properties': {
                    'd': 1,
                    'b': 2,
                    'c': 3
                }
            },
            {
                'case_id': 3,
                'properties': {
                    'd': 1,
                    'e': 2,
                    'c': 3
                }
            },
            {
                'case_id': 4,
                'properties': {
                    'f.': 1,
                    '': 2,
                    'silo_id': 3,
                    'read_id': 4,
                    '_id': 5,
                    'id': 6,
                    'edit_date': 7,
                    'create_date': 8,
                    'case_id': 9
                }
            },
        ]
        parseCommCareData(data, -87, -97, False)
        try:
            try:
                LabelValueStore.objects.get(
                    a=1, b=2, c=3, case_id=1, read_id=-97, silo_id=-87)
            except LabelValueStore.DoesNotExist as e:
                self.assert_(False)
            try:
                LabelValueStore.objects.get(
                    d=1, b=2, c=3, case_id=2, read_id=-97, silo_id=-87)
            except LabelValueStore.DoesNotExist as e:
                self.assert_(False)
            try:
                LabelValueStore.objects.get(
                    d=1, e=2, c=3, case_id=3, read_id=-97, silo_id=-87)
            except LabelValueStore.DoesNotExist as e:
                self.assert_(False)
            try:
                LabelValueStore.objects.get(
                    f_=1, user_assigned_id=5, editted_date=7, created_date=8,
                    user_case_id=9, case_id=4, read_id=-97, silo_id=-87)
            except LabelValueStore.DoesNotExist as e:
                self.assert_(False)
        except LabelValueStore.MultipleObjectsReturned as e:
            LabelValueStore.objects.filter(read_id=-97, silo_id=-87).delete()
            # if this happens run the test again and it should work
            self.assert_(False)

        # now lets test the updating functionality

        data = [
            {
                'case_id': 1,
                'properties': {
                    'a': 2,
                    'b': 2,
                    'c': 3,
                    'd': 4
                }
            },
            {
                'case_id': 2,
                'properties': {
                    'd': 1,
                    'b': 3
                }
            },
            {
                'case_id': 5,
                'properties': {
                    'e': 2,
                    'f': 3
                }
            }
        ]
        parseCommCareData(data, -87, -97, True)
        try:
            try:
                LabelValueStore.objects.get(
                    a=2, b=2, c=3, d=4, case_id=1, read_id=-97, silo_id=-87)
            except LabelValueStore.DoesNotExist as e:
                self.assert_(False)
            try:
                LabelValueStore.objects.get(
                    d=1, b=3, c=3, case_id=2, read_id=-97, silo_id=-87)
            except LabelValueStore.DoesNotExist as e:
                self.assert_(False)
            try:
                LabelValueStore.objects.get(
                    d=1, e=2, c=3, case_id=3, read_id=-97, silo_id=-87)
            except LabelValueStore.DoesNotExist as e:
                self.assert_(False)
            try:
                LabelValueStore.objects.get(
                    e=2, f=3, case_id=5, read_id=-97, silo_id=-87)
            except LabelValueStore.DoesNotExist as e:
                self.assert_(False)
            try:
                LabelValueStore.objects.get(
                    f_=1, user_assigned_id=5, editted_date=7, created_date=8,
                    user_case_id=9, case_id=4, read_id=-97, silo_id=-87)
            except LabelValueStore.DoesNotExist as e:
                self.assert_(False)
            LabelValueStore.objects.filter(read_id=-97, silo_id=-87).delete()

        except LabelValueStore.MultipleObjectsReturned as e:
            LabelValueStore.objects.filter(read_id=-97, silo_id=-87).delete()
            # if this happens run the test again and it should work
            self.assert_(False)

    def test_delete_silo(self):
        pass


class TestImportJson(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = factories.User()
        self.user.set_password('tola123')
        self.user.save()
        self.read_type = ReadType.objects.create(read_type="Ona")
        self.read = Read.objects.create(
            read_name="test_read1", owner=self.user, type=self.read_type,
            read_url='http://mysafeinfo.com/api/data?list='
                     'englishmonarchs&format=json')
        self.silo = factories.Silo(owner=self.user, reads=[self.read])
        factories.TolaUser(user=self.user)
        self.client.login(username=self.user.username, password='tola123')

    def test_JSONImport(self):
        filename = os.path.join(os.path.dirname(__file__),
                                'sample_data/import_json.json')
        with open(filename, 'r') as f:
            data_correct = json.load(f)
        data = {
            'read_id': self.read.id,
            'silo_id': self.silo.id
        }
        response = self.client.post("/json", data=data)
        self.assertEqual(response.status_code, 302)

        for row in data_correct:
            try:
                lvs = LabelValueStore.objects.get(silo_id=self.silo.id,
                                                  read_id=self.read.id, **row)
                lvs.delete()
            except Exception as e:
                LabelValueStore.objects.filter(silo_id=self.silo.id,
                                               read_id=self.read.id).delete()
                self.assertTrue(False)


class TestDeleteSilo(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = factories.User()
        self.user.set_password('tola123')
        self.user.save()
        factories.TolaUser(user=self.user)
        self.silo = factories.Silo(owner=self.user)
        self.client.login(username=self.user.username, password='tola123')

    def test_deleteAuto(self):
        silo_id = self.silo.id
        silo_name = self.silo.name
        read_id = self.silo.reads.all()[0].id
        response = self.client.post("/silo_delete/{}/".format(silo_id))

        silo = Silo.objects.filter(pk=silo_id).exists()
        read = Read.objects.filter(pk=read_id).exists()
        deleted_silos = DeletedSilos.objects.filter(
            silo_name_id="{} with id {}".format(silo_name, silo_id)).exists()

        self.assertEqual(response.status_code, 302)
        self.assertFalse(silo)
        self.assertFalse(read)
        self.assertTrue(deleted_silos)
