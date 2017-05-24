from django.core.urlresolvers import reverse_lazy
from django.forms import ModelForm
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Submit, Reset, HTML, Button, Row, Field, Hidden
from crispy_forms.bootstrap import FormActions
from django.forms.formsets import formset_factory


class CommCareForm(forms.Form):
    username = forms.CharField(max_length=60, required=True)
    password = forms.CharField(required=True, widget=forms.PasswordInput())
    project = forms.CharField(required=True)

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-sm-2'
        self.helper.field_class = 'col-sm-10'
        self.helper.form_method = 'post'
        self.helper.form_action = reverse_lazy('getCommCareForms')
        self.helper.add_input(Submit('submit', 'Submit'))
        self.helper.add_input(Reset('rest', 'Reset', css_class='btn-warning'))
        super(CommCareForm, self).__init__(*args, **kwargs)

class CommCareProjectForm(forms.Form):
    project = forms.CharField(required=True)

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-sm-2'
        self.helper.field_class = 'col-sm-10'
        self.helper.form_method = 'post'
        self.helper.form_action = reverse_lazy('getCommCareForms')
        self.helper.add_input(Submit('submit', 'Submit'))
        self.helper.add_input(Reset('rest', 'Reset', css_class='btn-warning'))
        super(CommCareForm, self).__init__(*args, **kwargs)
