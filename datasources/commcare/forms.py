from django.core.urlresolvers import reverse_lazy
from django.forms import ModelForm
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Submit, Reset, HTML, Button, Row, Field, Hidden
from crispy_forms.bootstrap import FormActions
from django.forms.formsets import formset_factory

from django.utils.safestring import mark_safe

from .util import getProjects


#diplaying a charfield that is also a list
class ListTextWidget(forms.TextInput):
    def __init__(self, data_list, name, *args, **kwargs):
        super(ListTextWidget, self).__init__(*args, **kwargs)
        self._name = name
        self._list = data_list
        self.attrs.update({'list':'list__%s' % self._name})

    def render(self, name, value, attrs=None):
        text_html = super(ListTextWidget, self).render(name, value, attrs=attrs)
        data_list = '<datalist id="list__%s">' % self._name
        for item in self._list:
            data_list += '<option value="%s">' % item
        data_list += '</datalist>'

        return (text_html + data_list)



class CommCarePassForm(forms.Form):
    username = forms.CharField(max_length=60, required=True)
    password = forms.CharField(required=True, widget=forms.PasswordInput())
    project = forms.CharField(required=True, help_text=mark_safe("This is the name of the project you are importing from. Press the down arrow to see the name of past projects you have imported from. To see the name of your CommCare projects go to CommCare <a href='https://www.commcarehq.org/account/projects/#'>settings then click my projects</a>"))
    silo = forms.ChoiceField(required=True)


    def __init__(self, *args, **kwargs):
        choices = kwargs.pop('choices')
        user_id = kwargs.pop('user_id')
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-sm-2'
        self.helper.field_class = 'col-sm-10'
        self.helper.form_method = 'post'
        self.helper.form_action = reverse_lazy('getCommCarePass')
        self.helper.add_input(Submit('submit', 'Submit'))
        self.helper.add_input(Reset('rest', 'Reset', css_class='btn-warning'))
        super(CommCarePassForm, self).__init__(*args, **kwargs)
        self.fields['project'].widget = ListTextWidget(data_list=getProjects(user_id), name='projects')
        self.fields['silo'].choices = choices


class CommCareProjectForm(forms.Form):
    project = forms.CharField(required=True, help_text=mark_safe("This is the name of the project you are importing from. Press the down arrow to see the name of past projects you have imported from. The projects your account has access to are listed in your CommCare <a href='https://www.commcarehq.org/account/projects/' target='_blank'>settings</a> under my projects.<br/>If you are not getting access it could be because your project has a different name then what you as a user can see. To see your projects true name go to CommCare <a href='https://www.commcarehq.org/account/projects/' target='_blank'>settings</a>"))
    silo = forms.ChoiceField(required=True)


    def __init__(self, *args, **kwargs):
        choices = kwargs.pop('choices')
        user_id = kwargs.pop('user_id')
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-sm-2'
        self.helper.field_class = 'col-sm-10'
        self.helper.form_method = 'post'
        self.helper.form_action = reverse_lazy('getCommCareAuth')
        self.helper.add_input(Submit('submit', 'Submit'))
        self.helper.add_input(Reset('rest', 'Reset', css_class='btn-warning'))
        super(CommCareProjectForm, self).__init__(*args, **kwargs)
        self.fields['project'].widget = ListTextWidget(data_list=getProjects(user_id), name='projects')
        self.fields['silo'].choices = choices



class CommCareAuthForm(CommCareProjectForm):
    username = forms.CharField(max_length=60, required=True)
    auth_token = forms.CharField(required=True, widget=forms.PasswordInput(), help_text=mark_safe("This gives tola access to your CommCare reports. Your api key can be found in your CommCare <a href='https://www.commcarehq.org/account/settings/' target='_blank'>settings</a>"))

    def __init__(self, *args, **kwargs):
        super(CommCareAuthForm, self).__init__(*args, **kwargs)
        self.fields.keyOrder = [
            'username',
            'auth_token',
            'project',
            'silo']
        self.fields['auth_token'].label = 'API Key'
