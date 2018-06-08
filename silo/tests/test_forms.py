# -*- coding: utf-8 -*-
from django.test import TestCase

from mock import patch

import factories
from silo import forms


class SiloFormTest(TestCase):
    def setUp(self):
        self.user = factories.User()
        self.tola_user = factories.TolaUser(user=self.user)

    def test_form_form_fields(self):
        form_fields = ['name', 'description', 'tags', 'shared',
                       'share_with_organization', 'owner', 'workflowlevel1']
        form = forms.SiloForm()

        self.assertItemsEqual(form_fields, form.fields.keys())

    def test_form_no_data(self):
        silo = factories.Silo()
        data = {}
        form = forms.SiloForm(data=data, instance=silo)

        self.assertTrue(form.has_changed())
        self.assertEqual(form.data, {})

    def test_form_with_data(self):
        silo = factories.Silo()
        data = {'name': 'This is the new name'}
        form = forms.SiloForm(data=data, instance=silo)

        self.assertTrue(form.has_changed())
        self.assertEqual(form.data, data)

    @patch('tola.activity_proxy.get_workflowteams')
    def test_form_with_wfl1(self, mock_get_workflowteams):
        wfl1 = factories.WorkflowLevel1()

        workflowteams = [{'workflowlevel1': wfl1.__dict__}]
        mock_get_workflowteams.return_value = workflowteams
        form = forms.SiloForm(user=self.user)

        item = form.fields.__getitem__('workflowlevel1')
        queryset = item._queryset

        self.assertEqual(queryset.count(), 1)
        self.assertTrue(queryset.filter(pk=wfl1.id).exists())

    @patch('tola.activity_proxy.get_workflowteams')
    @patch('tola.activity_proxy.get_by_url')
    def test_form_without_wfl1(self, mock_get_by_url, mock_get_workflowteams):
        workflowteams = [{'workflowlevel1': ''}]
        mock_get_workflowteams.return_value = workflowteams
        mock_get_by_url.return_value = []
        form = forms.SiloForm(user=self.user)

        item = form.fields.__getitem__('workflowlevel1')
        queryset = item._queryset

        self.assertEqual(queryset.count(), 0)

    @patch('tola.activity_proxy.get_workflowteams')
    def test_form_validate_success_with_form_user(self,
                                                  mock_get_workflowteams):
        mock_get_workflowteams.return_value = []
        silo = factories.Silo(owner=self.user)
        data = {
            'name': silo.name,
            'owner': silo.owner.id,
        }
        form = forms.SiloForm(user=self.user, data=data, instance=silo)

        self.assertTrue(form.is_valid())

    def test_form_validate_success_without_form_user_and_shared(self):
        silo = factories.Silo(owner=self.user)
        data = {
            'name': silo.name,
            'owner': silo.owner.id,
        }
        form = forms.SiloForm(data=data, instance=silo)

        self.assertTrue(form.is_valid())

    @patch('tola.activity_proxy.get_workflowteams')
    def test_form_validate_success_shared(self, mock_get_workflowteams):
        mock_get_workflowteams.return_value = []
        user = factories.User(first_name='Homer', last_name='Simpson')
        factories.TolaUser(
            user=user, organization=self.tola_user.organization)
        silo = factories.Silo(owner=self.user)

        data = {
            'name': silo.name,
            'owner': silo.owner.id,
            'shared': [user.id],
        }
        form = forms.SiloForm(user=self.user, data=data, instance=silo)

        self.assertTrue(form.is_valid())

    @patch('tola.activity_proxy.get_workflowteams')
    def test_form_validate_fail_shared_diff_org(self, mock_get_workflowteams):
        mock_get_workflowteams.return_value = []
        user = factories.User(first_name='Homer', last_name='Simpson')
        factories.TolaUser(user=user)
        silo = factories.Silo(owner=self.user)

        data = {
            'name': silo.name,
            'owner': silo.owner.id,
            'shared': [user.id],
        }
        form = forms.SiloForm(user=self.user, data=data, instance=silo)

        self.assertFalse(form.is_valid())

    @patch('tola.activity_proxy.get_workflowteams')
    def test_form_validate_fail_shared_with_owner(self,
                                                  mock_get_workflowteams):
        mock_get_workflowteams.return_value = []
        silo = factories.Silo(owner=self.user)
        data = {
            'name': silo.name,
            'owner': silo.owner.id,
            'shared': [silo.owner.id],
        }
        # with user
        form = forms.SiloForm(user=self.user, data=data, instance=silo)
        self.assertFalse(form.is_valid())

        # without user
        form = forms.SiloForm(data=data, instance=silo)
        self.assertFalse(form.is_valid())

    @patch('tola.activity_proxy.get_workflowteams')
    def test_form_validate_fail_without_owner(self, mock_get_workflowteams):
        mock_get_workflowteams.return_value = []
        silo = factories.Silo(owner=self.user)
        data = {
            'name': silo.name,
            'shared': [self.user.id],
        }

        form = forms.SiloForm(user=self.user, data=data, instance=silo)
        self.assertFalse(form.is_valid())

    @patch('tola.activity_proxy.get_workflowteams')
    def test_form_validate_fail_without_form_user(self,
                                                  mock_get_workflowteams):
        mock_get_workflowteams.return_value = []
        user = factories.User(first_name='Homer', last_name='Simpson')
        factories.TolaUser(
            user=user, organization=self.tola_user.organization)
        silo = factories.Silo(owner=self.user)

        data = {
            'name': silo.name,
            'owner': silo.owner.id,
            'shared': [user.id],
        }
        form = forms.SiloForm(data=data, instance=silo)
        self.assertFalse(form.is_valid())

    @patch('tola.activity_proxy.get_workflowteams')
    def test_form_validate_success_change_owner(self,
                                                mock_get_workflowteams):
        mock_get_workflowteams.return_value = []
        user = factories.User(first_name='Homer', last_name='Simpson')
        factories.TolaUser(
            user=user, organization=self.tola_user.organization)
        silo = factories.Silo(owner=self.user)

        data = {
            'name': silo.name,
            'owner': user.id,
        }
        form = forms.SiloForm(user=self.user, data=data, instance=silo)
        self.assertTrue(form.is_valid())

    @patch('tola.activity_proxy.get_workflowteams')
    def test_form_validate_fail_change_owner(self,
                                             mock_get_workflowteams):
        mock_get_workflowteams.return_value = []
        user = factories.User(first_name='Homer', last_name='Simpson')
        factories.TolaUser(
            user=user, organization=self.tola_user.organization)

        another_user = factories.User(username='Another User')
        factories.TolaUser(user=another_user)

        silo = factories.Silo(owner=self.user)

        data = {
            'name': silo.name,
            'owner': another_user,
            'shared': [user.id],
        }
        form = forms.SiloForm(user=another_user, data=data, instance=silo)
        self.assertFalse(form.is_valid())

    @patch('tola.activity_proxy.get_workflowteams')
    def test_form_validate_fail_owner_from_diff_org(self,
                                                    mock_get_workflowteams):
        mock_get_workflowteams.return_value = []
        user = factories.User(first_name='Homer', last_name='Simpson')
        factories.TolaUser(user=user,
                           organization=self.tola_user.organization)
        another_user = factories.User(username='Another User')
        factories.TolaUser(user=another_user)
        silo = factories.Silo(owner=self.user)

        data = {
            'name': silo.name,
            'owner': another_user.id,
            'shared': [user.id],
        }
        form = forms.SiloForm(user=self.user, data=data, instance=silo)

        self.assertFalse(form.is_valid())
