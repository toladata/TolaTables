from django.test import TestCase
from django.test import Client
from django.test import RequestFactory


from commcare.util import *
from commcare.views import *
from commcare.tasks import *

from tola.util import *
from silo.views import *
from silo.models import *

# Create your tests here.

class getCommCareProjectsTest(TestCase):
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

class parseCommCareDataTest(TestCase):
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
                'case_id' : 3,
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
            lvs = LabelValueStore.objects.get(f_=1, user_assigned_id=5, editted_date=7, created_date=8, user_case_id=9, case_id=3, read_id=-97, silo_id = -87)
        except LabelValueStore.DoesNotExist as e:
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
            }
        ]
        parseCommCareData(data, -87, -97, False)
