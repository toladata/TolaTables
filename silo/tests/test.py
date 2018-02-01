# -*- coding: utf-8 -*-
from datetime import datetime
import json

from django.contrib import messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.urlresolvers import resolve, reverse
from django.template.loader import render_to_string
from django.test import TestCase
from django.test import Client
from django.test import RequestFactory
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist

from commcare.tasks import parseCommCareData
from commcare.util import getProjects
from silo.forms import get_read_form
from silo.models import (User, DeletedSilos, LabelValueStore, Silo, ReadType,
                         Read)
from silo.views import (addColumnFilter, editColumnOrder, newFormulaColumn,
                        showRead, editSilo, uploadFile, siloDetail)
from tola.util import (addColsToSilo, hideSiloColumns, getColToTypeDict,
                       getSiloColumnNames)

from celery.exceptions import Retry
from mock import patch
from silo.tasks import process_silo
import factories

class CeleryTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()
        self.user = factories.User()

    def test_celery_success(self):
        silo = factories.Silo(owner=self.user, public=False)

        read_type = factories.ReadType(read_type="CSV")
        upload_file = open('test.csv', 'rb')
        read = factories.Read(owner=self.user, type=read_type, file_data=SimpleUploadedFile(upload_file.name, upload_file.read()))

        process_done = process_silo(silo.id, read.id)

        self.assertTrue(process_done)

    @patch('silo.tasks.process_silo_error')
    def test_celery_failure(self, process_silo_error):
        silo = factories.Silo(owner=self.user, public=False)

        read_type = factories.ReadType(read_type="CSV")
        upload_file = open('test_broken.csv', 'rb')
        read = factories.Read(owner=self.user, type=read_type, file_data=SimpleUploadedFile(upload_file.name, upload_file.read()))

        process_silo.apply_async(
            (silo.id, read.id),
            link_error=process_silo_error()
        )
        process_silo_error.assert_called()

    @patch('silo.tasks.process_silo.retry')
    def test_wrong_silo(self, process_silo_retry):
        process_silo_retry.side_effect = Retry()
        silo = factories.Silo(owner=self.user, public=False)

        with self.assertRaises(ObjectDoesNotExist):
            process_silo(silo.id, -1)


class ReadTest(TestCase):
    fixtures = ['../fixtures/read_types.json']
    show_read_url = '/show_read/'
    new_read_url = 'source/new//'

    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="joe", email="joe@email.com", password="tola123")

    def test_new_read_post(self):
        read_type = ReadType.objects.get(read_type="ONA")
        upload_file = open('test.csv', 'rb')
        params = {
            'owner': self.user.pk,
            'type': read_type.pk,
            'read_name': 'TEST READ SOURCE',
            'description': 'TEST DESCRIPTION for test read source',
            'read_url': 'https://www.lclark.edu',
            'resource_id':'testsssszzz',
            'create_date': '2015-06-24 20:33:47',
            'file_data': upload_file,
        }
        request = self.factory.post(self.new_read_url, data = params)
        request.user = self.user

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

# TODO Adjust tests to work without mongodb as an instance is not available during testing.

class SiloTest(TestCase):
    fixtures = ['fixtures/read_types.json']
    silo_edit_url = "/silo_edit/"
    upload_csv_url = "/file/"
    silo_detail_url = "/silo_detail/"

    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="bob", email="bob@email.com", password="tola123")

    def test_new_silo(self):
        # Create a New Silo
        silo = Silo.objects.create(name="Test Silo", owner=self.user,
                                   public=False, create_date=timezone.now())
        self.assertEqual(silo.pk, 1)

        # Fetch the silo that just got created above
        request = self.factory.get(self.silo_edit_url)
        request.user = self.user
        response = editSilo(request, silo.pk)
        self.assertEqual(response.status_code, 200)

        # update the silo that just got created above
        params = {
            'owner': self.user.pk,
            'name': 'Test Silo Updated',
            'description': 'Adding this description in a unit-test.',
        }
        request = self.factory.post(self.silo_edit_url, data = params)
        request.user = self.user
        request._dont_enforce_csrf_checks = True
        response = editSilo(request, silo.pk)
        if response.status_code == 302:
            self.assertEqual(response.url, "/silos/")
        else:
            self.assertEqual(response.status_code, 200)

    def test_new_silodata(self):
        read_type = ReadType.objects.get(read_type="CSV")
        upload_file = open('test.csv', 'rb')
        read = Read.objects.create(owner=self.user, type=read_type,
            read_name="TEST CSV IMPORT", description="unittest", create_date='2015-06-24 20:33:47',
            file_data=SimpleUploadedFile(upload_file.name, upload_file.read())
        )
        params = {
            "read_id": read.pk,
            "new_silo": "Test CSV Import",
        }
        request = self.factory.post(self.upload_csv_url, data = params)
        request.user = self.user
        request._dont_enforce_csrf_checks = True
        response = uploadFile(request, read.pk)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/silo_detail/", response.url)

        silo = Silo.objects.get(name="Test CSV Import")
        request = self.factory.get(self.silo_detail_url)
        request.user = self.user

        response = siloDetail(request, silo.pk)
        self.assertEqual(response.status_code, 200)

        #now delete that silo data cause this uses the custom database
        LabelValueStore.objects.filter(First_Name="Bob", Last_Name="Smith", silo_id="1", read_id="1").delete()
        LabelValueStore.objects.filter(First_Name="John", Last_Name="Doe", silo_id="1", read_id="1").delete()
        LabelValueStore.objects.filter(First_Name="Joe", Last_Name="Schmoe", silo_id="1", read_id="1").delete()
        LabelValueStore.objects.filter(First_Name="جان", Last_Name="ډو", silo_id="1", read_id="1").delete()

    def test_read_form(self):
        read_type = ReadType.objects.get(read_type="CSV")
        upload_file = open('test.csv', 'rb')
        params = {
            'owner': self.user.pk,
            'type': read_type.pk,
            'read_name': 'TEST READ SOURCE',
            'description': 'TEST DESCRIPTION for test read source',
            'read_url': 'https://www.lclark.edu',
            'resource_id':'testsssszzz',
            'create_date': '2015-06-24 20:33:47',
            #'file_data': upload_file,
        }
        file_dict = {'file_data': SimpleUploadedFile(upload_file.name, upload_file.read())}
        #form = ReadForm(params, file_dict)
        excluded_fields = ['create_date', 'edit_date',]
        form = get_read_form(excluded_fields)(params, file_dict)
        self.assertTrue(form.is_valid())

    # def test_delete_data_from_silodata(self):
    #     pass
    #
    # def test_update_data_in_silodata(self):
    #     pass
    #
    # def test_read_data_from_silodata(self):
    #     pass
    #
    # def test_delete_silodata(self):
    #     pass
    #
    # def test_delete_silo(self):
    #     pass

class FormulaColumn(TestCase):
    new_formula_columh_url = "/new_formula_column/"

    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="joe", email="joe@email.com", password="tola123")
        self.silo = self.silo = Silo.objects.create(name="test_silo1",public=0, owner = self.user)
        self.client.login(username='joe', password='tola123')

    def test_getNewFormulaColumn(self):
        request = self.factory.get(self.new_formula_columh_url)
        request.user = self.user
        request._dont_enforce_csrf_checks = True
        response = newFormulaColumn(request, self.silo.pk)
        self.assertEqual(response.status_code, 200)

    def test_postNewFormulaColumn(self):
        response = self.client.post('/new_formula_column/%s/' % str(self.silo.pk), data={'math_operation' : 'sum', 'column_name' : '', 'columns' : []})
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

        response = self.client.post('/new_formula_column/%s/' % str(self.silo.pk), data={'math_operation' : 'sum', 'column_name' : '', 'columns' : ['a', 'b', 'c']})
        self.assertEqual(response.status_code, 302)
        formula_column = self.silo.formulacolumns.get(column_name='sum')
        self.assertEqual(formula_column.operation,'sum')
        self.assertEqual(formula_column.mapping,'["a", "b", "c"]')
        self.assertEqual(formula_column.column_name,'sum')
        self.assertEqual(getSiloColumnNames(self.silo.pk),["sum"])
        self.silo = Silo.objects.get(pk=self.silo.pk)
        self.assertEqual(getColToTypeDict(self.silo).get('sum'),'float')
        try:
            lvs = LabelValueStore.objects.get(a="1", b="2", c="3", sum=6.0, read_id=-1, silo_id = self.silo.pk)
            lvs.delete()
        except LabelValueStore.DoesNotExist as e:
            self.assert_(False)
        try:
            lvs = LabelValueStore.objects.get(a="2", b="2", c="3.3", sum=7.3, read_id=-1, silo_id = self.silo.pk)
            lvs.delete()
        except LabelValueStore.DoesNotExist as e:
            self.assert_(False)
        try:
            lvs = LabelValueStore.objects.get(a="3", b="2", c="hi", sum="Error", read_id=-1, silo_id = self.silo.pk)
            lvs.delete()
        except LabelValueStore.DoesNotExist as e:
            self.assert_(False)


class ColumnOrder(TestCase):
    url = "/edit_column_order/"

    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="joe", email="joe@email.com", password="tola123")
        self.silo = self.silo = Silo.objects.create(name="test_silo1",public=0, owner = self.user)
        self.client.login(username='joe', password='tola123')
    def test_get_editColumnOrder(self):
        request = self.factory.get(self.url)
        request.user = self.user
        request._dont_enforce_csrf_checks = True
        response = editColumnOrder(request, self.silo.pk)
        self.assertEqual(response.status_code, 200)

    def test_post_editColumnOrder(self):
        addColsToSilo(self.silo, ['a','b','c','d','e','f'])
        hideSiloColumns(self.silo, ['b','e'])
        cols_ordered = ['c','f','a','d']
        response = self.client.post('/edit_column_order/%s/' % str(self.silo.pk), data={'columns' : cols_ordered})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(getSiloColumnNames(self.silo.pk), ['c','f','a','d'] )
        response = self.client.post('/edit_column_order/0/', data={'columns' : cols_ordered})
        self.assertEqual(response.status_code, 302)


class ColumnFilter(TestCase):
    url = "/edit_filter/"

    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="joe", email="joe@email.com", password="tola123")
        self.silo = self.silo = Silo.objects.create(name="test_silo1",public=0, owner = self.user)
        self.client.login(username='joe', password='tola123')
    def test_get_editColumnOrder(self):
        addColsToSilo(self.silo, ['a','b','c','d','e','f'])
        hideSiloColumns(self.silo, ['b','e'])
        self.silo.rows_to_hide = json.dumps([
            {
                "logic" : "BLANKCHAR",
                "operation": "",
                "number":"",
                "conditional": "---",
            },
            {
                "logic" : "AND",
                "operation": "empty",
                "number":"",
                "conditional": ["a","b"],
            },
            {
                "logic" : "OR",
                "operation": "empty",
                "number":"",
                "conditional": ["c","d"],
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
                "logic" : "BLANKCHAR",
                "operation": "",
                "number":"",
                "conditional": "---",
            },
            {
                "logic" : "AND",
                "operation": "empty",
                "number":"",
                "conditional": ["a","b"],
            },
            {
                "logic" : "OR",
                "operation": "empty",
                "number":"",
                "conditional": ["c","d"],
            }
        ]
        cols_to_hide = ['a','b','c']
        response = self.client.post('/edit_filter/%s/' % str(self.silo.pk), data={'hide_rows' : json.dumps(rows_to_hide), 'hide_cols' : json.dumps(cols_to_hide)})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.silo.hidden_columns, json.dumps(cols_to_hide))
        self.assertTrue(self.silo.rows_to_hide, json.dumps(rows_to_hide))


class removeSourceTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="joe", email="joe@email.com", password="tola123")
        self.silo = Silo.objects.create(name="test_silo1",public=0, owner = self.user)
        self.read_type = ReadType.objects.create(read_type="Ona")
        self.read = Read.objects.create(read_name="test_read1", owner = self.user, type=self.read_type)
        self.silo.reads.add(self.read)
        self.client.login(username='joe', password='tola123')

    def test_removeRead(self):
        self.assertEqual(self.silo.reads.count(),1)

        response = self.client.get("/source_remove/%s/%s/" % (0, self.read.pk))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.silo.reads.all().count(),1)

        response = self.client.get("/source_remove/%s/%s/" % (self.silo.pk, 0))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.silo.reads.all().count(),1)

        response = self.client.get("/source_remove/%s/%s/" % (self.silo.pk, self.read.pk))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.silo.reads.all().count(),0)

        response = self.client.get("/source_remove/%s/%s/" % (self.silo.pk, self.read.pk))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.silo.reads.all().count(),0)

class GetCommCareProjectsTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="joe", email="joe@email.com", password="tola123")
        self.user2 = User.objects.create_user(username="joe2", email="joe@email.com", password="tola123")
        self.read_type = ReadType.objects.create(read_type="CommCare")

    def test_onaParserOneLayer(self):
        self.assertEqual(getProjects(self.user.id), [])
        self.read = Read.objects.create(read_name="test_read1", owner = self.user, type=self.read_type, read_url="https://www.commcarehq.org/a/a/")
        self.assertEqual(getProjects(self.user.id), ['a'])
        self.read = Read.objects.create(read_name="test_read2", owner = self.user, type=self.read_type, read_url="https://www.commcarehq.org/a/b/")
        self.assertEqual(getProjects(self.user.id), ['a','b'])
        self.read = Read.objects.create(read_name="test_read3", owner = self.user, type=self.read_type, read_url="https://www.commcarehq.org/a/b/")
        self.assertEqual(getProjects(self.user.id), ['a','b'])
        self.read = Read.objects.create(read_name="test_read4", owner = self.user2, type=self.read_type, read_url="https://www.commcarehq.org/a/c/")
        self.assertEqual(getProjects(self.user.id), ['a','b'])

class ParseCommCareDataTest(TestCase):
    def test_commcaredataparser(self):
        data = [
            {
                'case_id' : 1,
                'properties' : {
                    'a' : 1,
                    'b' : 2,
                    'c' : 3
                }
            },
            {
                'case_id' : 2,
                'properties' : {
                    'd' : 1,
                    'b' : 2,
                    'c' : 3
                }
            },
            {
                'case_id' : 3,
                'properties' : {
                    'd' : 1,
                    'e' : 2,
                    'c' : 3
                }
            },
            {
                'case_id' : 4,
                'properties' : {
                    'f.' : 1,
                    '' : 2,
                    'silo_id' : 3,
                    'read_id' : 4,
                    '_id' : 5,
                    'id' : 6,
                    'edit_date' : 7,
                    'create_date' : 8,
                    'case_id' : 9
                }
            },
        ]
        parseCommCareData(data, -87, -97, False)
        try:
            try:
                lvs = LabelValueStore.objects.get(a=1, b=2, c=3, case_id=1, read_id=-97, silo_id = -87)
            except LabelValueStore.DoesNotExist as e:
                self.assert_(False)
            try:
                lvs = LabelValueStore.objects.get(d=1, b=2, c=3, case_id=2, read_id=-97, silo_id = -87)
            except LabelValueStore.DoesNotExist as e:
                self.assert_(False)
            try:
                lvs = LabelValueStore.objects.get(d=1, e=2, c=3, case_id=3, read_id=-97, silo_id = -87)
            except LabelValueStore.DoesNotExist as e:
                self.assert_(False)
            try:
                lvs = LabelValueStore.objects.get(f_=1, user_assigned_id=5, editted_date=7, created_date=8, user_case_id=9, case_id=4, read_id=-97, silo_id = -87)
            except LabelValueStore.DoesNotExist as e:
                self.assert_(False)
        except LabelValueStore.MultipleObjectsReturned as e:
            LabelValueStore.objects.filter(read_id=-97, silo_id = -87).delete()
            #if this happens run the test again and it should work
            self.assert_(False)

        #now lets test the updating functionality

        data = [
            {
                'case_id' : 1,
                'properties' : {
                    'a' : 2,
                    'b' : 2,
                    'c' : 3,
                    'd' : 4
                }
            },
            {
                'case_id' : 2,
                'properties' : {
                    'd' : 1,
                    'b' : 3
                }
            },
            {
                'case_id' : 5,
                'properties' : {
                    'e' : 2,
                    'f' : 3
                }
            }
        ]
        parseCommCareData(data, -87, -97, True)
        try:
            try:
                lvs = LabelValueStore.objects.get(a=2, b=2, c=3, d=4, case_id=1, read_id=-97, silo_id = -87)
            except LabelValueStore.DoesNotExist as e:
                self.assert_(False)
            try:
                lvs = LabelValueStore.objects.get(d=1, b=3, c=3, case_id=2, read_id=-97, silo_id = -87)
            except LabelValueStore.DoesNotExist as e:
                self.assert_(False)
            try:
                lvs = LabelValueStore.objects.get(d=1, e=2, c=3, case_id=3, read_id=-97, silo_id = -87)
            except LabelValueStore.DoesNotExist as e:
                self.assert_(False)
            try:
                lvs = LabelValueStore.objects.get(e=2, f=3, case_id=5, read_id=-97, silo_id = -87)
            except LabelValueStore.DoesNotExist as e:
                self.assert_(False)
            try:
                lvs = LabelValueStore.objects.get(f_=1, user_assigned_id=5, editted_date=7, created_date=8, user_case_id=9, case_id=4, read_id=-97, silo_id = -87)
            except LabelValueStore.DoesNotExist as e:
                self.assert_(False)
            LabelValueStore.objects.filter(read_id=-97, silo_id = -87).delete()

        except LabelValueStore.MultipleObjectsReturned as e:
            LabelValueStore.objects.filter(read_id=-97, silo_id = -87).delete()
            print 'Needed to delete some temporary data, running the tests again should work'
            #if this happens run the test again and it should work
            self.assert_(False)

    def test_delete_silo(self):
        pass


class Test_ImportJson(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="joe", email="joe@email.com", password="tola123")
        self.silo = Silo.objects.create(name="test_silo1",public=0, owner = self.user)
        self.read_type = ReadType.objects.create(read_type="Ona")
        self.read = Read.objects.create(read_name="test_read1", owner = self.user, type=self.read_type, read_url='http://mysafeinfo.com/api/data?list=englishmonarchs&format=json')
        self.client.login(username='joe', password='tola123')
    def test_JSONImport(self):
        data_correct = json.loads('[{"nm":"Edmund lronside","cty":"United Kingdom","hse":"House of Wessex","yrs":"1016"},{"nm":"Cnut","cty":"United Kingdom","hse":"House of Denmark","yrs":"1016-1035"},{"nm":"Harold I Harefoot","cty":"United Kingdom","hse":"House of Denmark","yrs":"1035-1040"},{"nm":"Harthacanut","cty":"United Kingdom","hse":"House of Denmark","yrs":"1040-1042"},{"nm":"Edward the Confessor","cty":"United Kingdom","hse":"House of Wessex","yrs":"1042-1066"},{"nm":"Harold II","cty":"United Kingdom","hse":"House of Wessex","yrs":"1066"},{"nm":"William I","cty":"United Kingdom","hse":"House of Normandy","yrs":"1066-1087"},{"nm":"William II","cty":"United Kingdom","hse":"House of Normandy","yrs":"1087-1100"},{"nm":"Henry I","cty":"United Kingdom","hse":"House of Normandy","yrs":"1100-1135"},{"nm":"Stephen","cty":"United Kingdom","hse":"House of Blois","yrs":"1135-1154"},{"nm":"Henry II","cty":"United Kingdom","hse":"House of Angevin","yrs":"1154-1189"},{"nm":"Richard I","cty":"United Kingdom","hse":"House of Angevin","yrs":"1189-1199"},{"nm":"John","cty":"United Kingdom","hse":"House of Angevin","yrs":"1199-1216"},{"nm":"Henry III","cty":"United Kingdom","hse":"House of Plantagenet","yrs":"1216-1272"},{"nm":"Edward I","cty":"United Kingdom","hse":"House of Plantagenet","yrs":"1272-1307"},{"nm":"Edward II","cty":"United Kingdom","hse":"House of Plantagenet","yrs":"1307-1327"},{"nm":"Edward III","cty":"United Kingdom","hse":"House of Plantagenet","yrs":"1327-1377"},{"nm":"Richard II","cty":"United Kingdom","hse":"House of Plantagenet","yrs":"1377-1399"},{"nm":"Henry IV","cty":"United Kingdom","hse":"House of Lancaster","yrs":"1399-1413"},{"nm":"Henry V","cty":"United Kingdom","hse":"House of Lancaster","yrs":"1413-1422"},{"nm":"Henry VI","cty":"United Kingdom","hse":"House of Lancaster","yrs":"1422-1461"},{"nm":"Edward IV","cty":"United Kingdom","hse":"House of York","yrs":"1461-1483"},{"nm":"Edward V","cty":"United Kingdom","hse":"House of York","yrs":"1483"},{"nm":"Richard III","cty":"United Kingdom","hse":"House of York","yrs":"1483-1485"},{"nm":"Henry VII","cty":"United Kingdom","hse":"House of Tudor","yrs":"1485-1509"},{"nm":"Henry VIII","cty":"United Kingdom","hse":"House of Tudor","yrs":"1509-1547"},{"nm":"Edward VI","cty":"United Kingdom","hse":"House of Tudor","yrs":"1547-1553"},{"nm":"Mary I","cty":"United Kingdom","hse":"House of Tudor","yrs":"1553-1558"},{"nm":"Elizabeth I","cty":"United Kingdom","hse":"House of Tudor","yrs":"1558-1603"},{"nm":"James I","cty":"United Kingdom","hse":"House of Stuart","yrs":"1603-1625"},{"nm":"Charles I","cty":"United Kingdom","hse":"House of Stuart","yrs":"1625-1649"},{"nm":"Commonwealth","cty":"United Kingdom","hse":"Commonwealth","yrs":"1649-1653"},{"nm":"Oliver Cromwell","cty":"United Kingdom","hse":"Commonwealth","yrs":"1653-1658"},{"nm":"Richard Cromwell","cty":"United Kingdom","hse":"Commonwealth","yrs":"1658-1659"},{"nm":"Charles II","cty":"United Kingdom","hse":"House of Stuart","yrs":"1660-1685"},{"nm":"James II","cty":"United Kingdom","hse":"House of Stuart","yrs":"1685-1688"},{"nm":"William III","cty":"United Kingdom","hse":"House of Orange","yrs":"1689-1694"},{"nm":"Anne","cty":"United Kingdom","hse":"House of Stuart","yrs":"1702-1714"},{"nm":"George I","cty":"United Kingdom","hse":"House of Hanover","yrs":"1714-1727"},{"nm":"George II","cty":"United Kingdom","hse":"House of Hanover","yrs":"1727-1760"},{"nm":"George III","cty":"United Kingdom","hse":"House of Hanover","yrs":"1760-1820"},{"nm":"George IV","cty":"United Kingdom","hse":"House of Hanover","yrs":"1820-1830"},{"nm":"William IV","cty":"United Kingdom","hse":"House of Hanover","yrs":"1830-1837"},{"nm":"Victoria","cty":"United Kingdom","hse":"House of Hanover","yrs":"1837-1901"},{"nm":"Edward VII","cty":"United Kingdom","hse":"House of Saxe-Coburg-Gotha","yrs":"1901-1910"},{"nm":"George V","cty":"United Kingdom","hse":"House of Windsor","yrs":"1910-1936"},{"nm":"Edward VIII","cty":"United Kingdom","hse":"House of Windsor","yrs":"1936"},{"nm":"George VI","cty":"United Kingdom","hse":"House of Windsor","yrs":"1936-1952"},{"nm":"Elizabeth II","cty":"United Kingdom","hse":"House of Windsor","yrs":"1952-"},{"nm":"Edward the Elder","cty":"United Kingdom","hse":"House of Wessex","yrs":"899-925"},{"nm":"Athelstan","cty":"United Kingdom","hse":"House of Wessex","yrs":"925-940"},{"nm":"Edmund","cty":"United Kingdom","hse":"House of Wessex","yrs":"940-946"},{"nm":"Edred","cty":"United Kingdom","hse":"House of Wessex","yrs":"946-955"},{"nm":"Edwy","cty":"United Kingdom","hse":"House of Wessex","yrs":"955-959"},{"nm":"Edgar","cty":"United Kingdom","hse":"House of Wessex","yrs":"959-975"},{"nm":"Edward the Martyr","cty":"United Kingdom","hse":"House of Wessex","yrs":"975-978"},{"nm":"Ethelred II the Unready","cty":"United Kingdom","hse":"House of Wessex","yrs":"978-1016"}]')
        response = self.client.post("/json", data={'read_id' : self.read.id, 'silo_id' : self.silo.id})
        self.assertEqual(response.status_code,302)

        for row in data_correct:
            try:
                lvs = LabelValueStore.objects.get(silo_id=self.silo.id, read_id = self.read.id, **row)
                lvs.delete()
            except Exception as e:
                print e
                print row
                LabelValueStore.objects.filter(silo_id=self.silo.id, read_id = self.read.id).delete()
                self.assertTrue(False)


class Test_DeleteSilo(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="joe", email="joe@email.com", password="tola123")
        self.silo = Silo.objects.create(name="test_silo1",public=0, owner = self.user)
        self.read_type = ReadType.objects.create(read_type="Ona")
        self.read = Read.objects.create(read_name="test_read1", owner = self.user, type=self.read_type, read_url='http://mysafeinfo.com/api/data?list=englishmonarchs&format=json')
        self.silo.reads.add(self.read)
        self.client.login(username='joe', password='tola123')
    def test_deleteAuto(self):
        silo_id = self.silo.id
        read_id = self.read.id
        response = self.client.post("/silo_delete/%i/" % silo_id)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Silo.objects.filter(pk=silo_id).exists())
        self.assertFalse(Read.objects.filter(pk=read_id).exists())
        self.assertTrue(DeletedSilos.objects.filter(silo_name_id="test_silo1 with id %i" % silo_id).exists())
