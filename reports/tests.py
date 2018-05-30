from django.test import TestCase, RequestFactory
import factories
from rest_framework.test import APIRequestFactory
from reports import views


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

class ReportsViewTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = factories.User()
        self.tola_user = factories.TolaUser(user=self.user)

    def test_list_own_reports(self):
        read = factories.Read(read_name="test_data",
                              owner=self.tola_user.user)

        factories.Silo(name='Test Share Report',
                       owner=self.tola_user.user,
                       reads=[read],
                       public=False,
                       shared=[],
                       share_with_organization=True)

        request = self.factory.get('')
        request.user = self.user
        response = views.list_table_dashboards(request)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Share Report')

    def test_list_reports_shared_with_organization(self):
        read = factories.Read(read_name="test_data",
                              owner=self.tola_user.user)

        factories.Silo(name='Test Share Report',
                       owner=self.tola_user.user,
                       reads=[read],
                       public=False,
                       shared=[],
                       share_with_organization=True)

        request = self.factory.get('')
        request.user = self.tola_user.user
        response = views.list_table_dashboards(request)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Share Report')

    def test_list_reports_shared_with_users_organization(self):
        request_user = factories.User(username='Another User')
        factories.TolaUser(user=request_user,
                           organization=self.tola_user.organization)

        read = factories.Read(read_name="test_data",
                              owner=self.tola_user.user)

        factories.Silo(name='Test Share Report',
                       owner=self.tola_user.user,
                       reads=[read],
                       public=False,
                       shared=[],
                       share_with_organization=True)

        request = self.factory.get('')
        request.user = request_user
        response = views.list_table_dashboards(request)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Share Report')

    def test_list_reports_shared_with_different_organization(self):
        request_user = factories.User(username='Another User')
        factories.TolaUser(user=request_user)

        read = factories.Read(read_name="test_data",
                              owner=self.tola_user.user)

        factories.Silo(name='Test Share Report',
                       owner=self.tola_user.user,
                       reads=[read],
                       public=False,
                       shared=[],
                       share_with_organization=True)
        request = self.factory.get('')
        request.user = request_user
        response = views.list_table_dashboards(request)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Test Share Report')

    def test_list_reports_not_share_with_organization(self):
        request_user = factories.User(username='Another User')
        factories.TolaUser(user=request_user,
                           organization=self.tola_user.organization)

        read = factories.Read(read_name="test_data",
                              owner=self.tola_user.user)

        factories.Silo(name='Test Share Report',
                       owner=self.tola_user.user,
                       reads=[read],
                       public=False,
                       shared=[],
                       share_with_organization=False)

        request = self.factory.get('')
        request.user = request_user
        response = views.list_table_dashboards(request)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Test Share Report')

    def test_list_reports_with_shared_user(self):

        request_user = factories.User(username='Another User')
        read = factories.Read(read_name="test_data",
                              owner=self.tola_user.user)

        factories.Silo(name='Test Share Report',
                       owner=self.tola_user.user,
                       reads=[read],
                       public=False,
                       shared=[request_user],
                       share_with_organization=False)

        request = self.factory.get('')
        request.user = self.user
        response = views.list_table_dashboards(request)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Share Report')

    def test_list_public_reports(self):
        request_user = factories.User(username='Another User')
        factories.TolaUser(user=request_user)

        read = factories.Read(read_name="test_data",
                              owner=self.tola_user.user)

        factories.Silo(name='Test Share Report',
                       owner=self.tola_user.user,
                       reads=[read],
                       public=True,
                       shared=[],
                       share_with_organization=False)

        request = self.factory.get('')
        request.user = request_user
        response = views.list_table_dashboards(request)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Share Report')
