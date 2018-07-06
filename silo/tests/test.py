# -*- coding: utf-8 -*-
import os
import json

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test import Client
from django.test import RequestFactory
from django.core.exceptions import ObjectDoesNotExist

from commcare.tasks import parseCommCareData
from commcare.util import getProjects
from silo.tasks import process_silo
from silo.forms import get_read_form
from silo.models import (DeletedSilos, LabelValueStore, ReadType, Read, Silo,
                         CeleryTask)
from silo.views import (addColumnFilter, editColumnOrder, newFormulaColumn,
                        showRead, edit_silo, uploadFile, silo_detail)
from tola.util import (addColsToSilo, hideSiloColumns, getColToTypeDict,
                       getSiloColumnNames, cleanKey)

from django.contrib.contenttypes.models import ContentType
from django.utils.encoding import smart_str

from mock import patch
from celery.exceptions import Retry
import factories


class UploadFileTest(TestCase):
    """
    Tests the File Upload Process in several steps.
    - Checks if uploadFile successfully creates a celery task and new silo
    for imported read
    - Checks if process_silo actually imports data
    - Checks what happens if the task fails

    Celery is not used for testing purposes, each step is checked on its own.
    """
    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()
        self.user = factories.User()
        self.upload_csv_url = '/file/'

    def test_upload_file(self):
        """
        Checks if uploadFile successfully creates a celery task and new silo
        for imported read

        uploadFile takes POST request with csv file
        - takes a Read
        - adds read to a silo
        - creates a CeleryTask
        - redirects to silo_detail
        :return:
        """
        read_type = factories.ReadType(read_type="CSV")
        upload_file = open('silo/tests/sample_data/test.csv', 'rb')
        read = factories.Read(
            owner=self.user, type=read_type,
            read_name="TEST UPLOADFILE",  description="unittest",
            file_data=SimpleUploadedFile(upload_file.name, upload_file.read())
        )
        self.assertEqual(Silo.objects.filter(reads=read.pk).count(), 0)
        params = {
            "read_id": read.pk,
            "new_silo": "TEST UPLOADFILE",
        }
        request = self.factory.post(self.upload_csv_url, data=params)
        request.user = self.user
        request._dont_enforce_csrf_checks = True
        response = uploadFile(request, read.pk)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/silo_detail/", response.url)

        # assure new Silo was created
        new_silo = Silo.objects.get(reads=read.pk)
        self.assertEqual(new_silo.name, params["new_silo"])

        # assure CeleryTask was created
        ctask = CeleryTask.objects.get(
            object_id=read.pk,
            content_type=ContentType.objects.get_for_model(Read)
        )

        self.assertNotEqual(ctask.task_id, None)
        self.assertEqual(ctask.task_status, CeleryTask.TASK_CREATED)

    def test_celery_success(self):
        """
        Test if the celery task process_silo actually imports data
        :return:
        """
        silo = factories.Silo(owner=self.user, public=False)

        read_type = factories.ReadType(read_type="CSV")
        upload_file = open('silo/tests/sample_data/test.csv', 'rb')
        read = factories.Read(
            owner=self.user, type=read_type,
            file_data=SimpleUploadedFile(upload_file.name, upload_file.read())
        )

        factories.CeleryTask(task_status=CeleryTask.TASK_CREATED,
                             content_object=read)

        process_done = process_silo(silo.id, read.id)
        silo = Silo.objects.get(pk=silo.id)
        self.assertEqual(getSiloColumnNames(silo.id),
                         ['First_Name', 'Last_Name', 'E-mail'])
        self.assertTrue(process_done)

    def test_celery_failure(self):
        silo = factories.Silo(owner=self.user, public=False)

        read_type = factories.ReadType(read_type="CSV")
        upload_file = open('silo/tests/sample_data/test_broken.csv', 'rb')
        read = factories.Read(
            owner=self.user, type=read_type,
            file_data=SimpleUploadedFile(upload_file.name, upload_file.read())
        )
        task = factories.CeleryTask(content_object=read)

        process_silo(silo.id, read.id)

        ctask = CeleryTask.objects.get(
            object_id=read.id,
            content_type=ContentType.objects.get_for_model(Read)
        )

        self.assertEqual(ctask.task_id, task.task_id)
        self.assertEqual(ctask.task_status, CeleryTask.TASK_FAILED)

    @patch('silo.tasks.process_silo.retry')
    def test_celery_wrong_silo(self, process_silo_retry):
        process_silo_retry.side_effect = Retry()
        silo = factories.Silo(owner=self.user, public=False)

        with self.assertRaises(ObjectDoesNotExist):
            process_silo(silo.id, -1)


class SiloDetailTest(TestCase):
    """
    Test Silo Detail in the following scenarios
    1 - CeleryTask running in the background: no data is shown and info
        is displayed
    2 - CeleryTask Finished: data is shown
    3 - CeleryTask Failed: data is shown and error message is displayed
    """

    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()
        self.user = factories.User()
        self.upload_csv_url = '/file/'
        self.silo_detail_url = "/silo_detail/"

    def test_silo_detail_import_running(self):
        # Create Silo, Read and CeleryTask
        read_type = factories.ReadType(read_type="CSV")
        read = factories.Read(
            owner=self.user, type=read_type,
            read_name="TEST SILO DETAIL", description="unittest"
        )
        silo = factories.Silo(owner=self.user, public=False)
        silo.reads.add(read)
        factories.CeleryTask(content_object=read,
                             task_status=CeleryTask.TASK_IN_PROGRESS)
        factories.TolaUser(user=self.user)

        # Check view

        request = self.factory.get(self.silo_detail_url)
        request.user = self.user

        response = silo_detail(request, silo.pk)
        self.assertContains(
            response,
            '<a href="/show_read/{}" target="_blank">{}</a>'.format(
                read.id, read.read_name)
        )
        self.assertContains(
            response,
            '<span class="btn-sm btn-warning">Import running</span>'
        )
        self.assertContains(response, '<h4>Import process running</h4>')

    def test_silo_detail_import_failed(self):
        # Create Silo, Read and CeleryTask
        read_type = factories.ReadType(read_type="CSV")
        read = factories.Read(
            owner=self.user, type=read_type,
            read_name="TEST SILO FAIL", description="unittest"
        )
        silo = factories.Silo(owner=self.user, public=False)
        silo.reads.add(read)
        factories.CeleryTask(content_object=read,
                             task_status=CeleryTask.TASK_FAILED)
        factories.TolaUser(user=self.user)

        # Check view
        request = self.factory.get(self.silo_detail_url)
        request.user = self.user

        response = silo_detail(request, silo.pk)
        self.assertContains(
            response,
            '<a href="/show_read/{}" target="_blank">{}</a>'.format(
                read.id, read.read_name)
        )
        self.assertContains(
            response,
            '<span class="btn-sm btn-danger">Import Failed</span>'
        )
        self.assertContains(
            response, '<h4 style="color:#ff3019">Import process failed</h4>')

    def test_silo_detail_import_done(self):
        # Create Silo, Read and CeleryTask
        read_type = factories.ReadType(read_type="CSV")
        read = factories.Read(
            owner=self.user, type=read_type,
            read_name="TEST SILO DONE", description="unittest"
        )
        silo = factories.Silo(owner=self.user, public=False)
        silo.reads.add(read)
        factories.CeleryTask(content_object=read,
                             task_status=CeleryTask.TASK_FINISHED)
        factories.TolaUser(user=self.user)
        # Check view
        request = self.factory.get(self.silo_detail_url)
        request.user = self.user

        response = silo_detail(request, silo.pk)
        self.assertContains(
            response,
            '<a href="/show_read/{}" target="_blank">{}</a>'.format(
                read.id, read.read_name)
        )
        self.assertNotContains(
            response, '<span class="btn-sm btn-danger">Import Failed</span>')
        self.assertNotContains(
            response, '<span class="btn-sm btn-warning">Import running</span>')
        self.assertNotContains(
            response, '<h4 style="color:#ff3019">Import process failed</h4>')
        self.assertNotContains(response, '<h4>Import process running</h4>')


class ReadTest(TestCase):
    show_read_url = '/show_read/'
    new_read_url = 'source/new//'

    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()
        self.tola_user = factories.TolaUser()
        factories.ReadType.create_batch(7)

    def test_new_read_post(self):
        read_type = ReadType.objects.get(read_type="ONA")
        upload_file = open('silo/tests/sample_data/test.csv', 'rb')
        params = {
            'owner': self.tola_user.user.pk,
            'type': read_type.pk,
            'read_name': 'TEST READ SOURCE',
            'description': 'TEST DESCRIPTION for test read source',
            'read_url': 'https://www.lclark.edu',
            'resource_id': 'testsssszzz',
            'create_date': '2015-06-24 20:33:47',
            'file_data': upload_file,
        }
        request = self.factory.post(self.new_read_url, data=params)
        request.user = self.tola_user.user

        response = showRead(request, 1)
        if response.status_code == 302:
            if "/read/login" in response.url or "/file/" in response.url:
                self.assertEqual(response.url, response.url)
            else:
                self.assertEqual(response.url, "/silos")
        else:
            self.assertEqual(response.status_code, 200)

        # Now test the show_read view to make sure that I can retrieve the obj
        # that just got created using the POST method above.
        source = Read.objects.get(read_name='TEST READ SOURCE')
        response = self.client.get(self.show_read_url + str(source.pk) + "/")
        self.assertEqual(response.status_code, 302)


# TODO: Adjust tests to work without mongodb as an instance is not available
# TODO: during testing.
class SiloTest(TestCase):
    silo_edit_url = "/silo_edit/"
    upload_csv_url = "/file/"
    silo_detail_url = "/silo_detail/"

    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()
        self.tola_user = factories.TolaUser()
        factories.ReadType.create_batch(7)

    @patch('tola.activity_proxy.get_workflowteams')
    def test_new_silo(self, mock_get_workflowteams):
        mock_get_workflowteams.return_value = []
        # Create a New Silo
        silo = factories.Silo(owner=self.tola_user.user)
        self.assertEqual(silo.pk, 1)

        # Fetch the silo that just got created above
        request = self.factory.get(self.silo_edit_url)
        request.user = self.tola_user.user
        response = edit_silo(request, silo.pk)
        self.assertEqual(response.status_code, 200)

        # update the silo that just got created above
        params = {
            'owner': self.tola_user.user.pk,
            'name': 'Test Silo Updated',
            'description': 'Adding this description in a unit-test.',
        }
        request = self.factory.post(self.silo_edit_url, data=params)
        request.user = self.tola_user.user
        request._dont_enforce_csrf_checks = True
        response = edit_silo(request, silo.pk)
        if response.status_code == 302:
            self.assertEqual(response.url, "/silos/")
        else:
            self.assertEqual(response.status_code, 200)

    @patch('tola.activity_proxy.get_workflowteams')
    def test_new_silodata(self, mock_get_workflowteams):
        mock_get_workflowteams.return_value = []
        read_type = ReadType.objects.get(read_type="CSV")
        upload_file = open('silo/tests/sample_data/test.csv', 'rb')
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

        response = silo_detail(request, silo.pk)
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
        upload_file = open('silo/tests/sample_data/test.csv', 'rb')
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
        excluded_fields = ['create_date', 'edit_date', 'onedrive_file',
                           'onedrive_access_token']
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
        except LabelValueStore.DoesNotExist:
            self.assert_(False)
        try:
            lvs = LabelValueStore.objects.get(a="2", b="2", c="3.3", sum=7.3,
                                              read_id=-1, silo_id=self.silo.pk)
            lvs.delete()
        except LabelValueStore.DoesNotExist:
            self.assert_(False)
        try:
            lvs = LabelValueStore.objects.get(
                a="3", b="2", c="hi", sum="Error", read_id=-1,
                silo_id=self.silo.pk)
            lvs.delete()
        except LabelValueStore.DoesNotExist:
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
            except LabelValueStore.DoesNotExist:
                self.assert_(False)
            try:
                LabelValueStore.objects.get(
                    d=1, b=2, c=3, case_id=2, read_id=-97, silo_id=-87)
            except LabelValueStore.DoesNotExist:
                self.assert_(False)
            try:
                LabelValueStore.objects.get(
                    d=1, e=2, c=3, case_id=3, read_id=-97, silo_id=-87)
            except LabelValueStore.DoesNotExist:
                self.assert_(False)
            try:
                LabelValueStore.objects.get(
                    f_=1, user_assigned_id=5, editted_date=7, created_date=8,
                    user_case_id=9, case_id=4, read_id=-97, silo_id=-87)
            except LabelValueStore.DoesNotExist:
                self.assert_(False)
        except LabelValueStore.MultipleObjectsReturned:
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
            except LabelValueStore.DoesNotExist:
                self.assert_(False)
            try:
                LabelValueStore.objects.get(
                    d=1, b=3, c=3, case_id=2, read_id=-97, silo_id=-87)
            except LabelValueStore.DoesNotExist:
                self.assert_(False)
            try:
                LabelValueStore.objects.get(
                    d=1, e=2, c=3, case_id=3, read_id=-97, silo_id=-87)
            except LabelValueStore.DoesNotExist:
                self.assert_(False)
            try:
                LabelValueStore.objects.get(
                    e=2, f=3, case_id=5, read_id=-97, silo_id=-87)
            except LabelValueStore.DoesNotExist:
                self.assert_(False)
            try:
                LabelValueStore.objects.get(
                    f_=1, user_assigned_id=5, editted_date=7, created_date=8,
                    user_case_id=9, case_id=4, read_id=-97, silo_id=-87)
            except LabelValueStore.DoesNotExist:
                self.assert_(False)
            LabelValueStore.objects.filter(read_id=-97, silo_id=-87).delete()

        except LabelValueStore.MultipleObjectsReturned:
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
            except Exception:
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


class TestCleanKeys(TestCase):
    def setUp(self):
        self.user = factories.User()
        self.silo = factories.Silo(owner=self.user)

    def test_clean_keys(self):
        LabelValueStore.objects(silo_id=self.silo.id).delete()
        lvs = LabelValueStore()
        orig_data = {
            'Header 1': 'r1c1',
            'create_date': 'r1c3',
            'edit_date': 'r1c2',
            '_id': 'r1c4'
        }

        for k, v in orig_data.iteritems():
            key = cleanKey(k)
            val = smart_str(v, strings_only=True)
            key = smart_str(key)
            val = val.strip()
            setattr(lvs, key, val)
        lvs.silo_id = self.silo.id
        lvs.save()

        returned_data = json.loads(LabelValueStore.objects(
            silo_id=self.silo.id).to_json())[0]
        returned_data.pop('_id')

        expected_data = {
            'Header 1': 'r1c1',
            'created_date': 'r1c3',
            'editted_date': 'r1c2',
            'user_assigned_id': 'r1c4',
            'read_id': -1,
            'silo_id': self.silo.id
        }
        self.assertEqual(returned_data, expected_data)
        LabelValueStore.objects(silo_id=self.silo.id).delete()
