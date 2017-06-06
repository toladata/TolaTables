from silo.models import Read
#import floppyforms as forms
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Hidden

def get_json_form(excluded_fields):
    class ReadJSONForm(forms.ModelForm):
        def __init__(self, *args, **kwargs):
            super(ReadJSONForm, self).__init__(*args, **kwargs)
            self.helper = FormHelper(self)
            self.helper.layout.append(Hidden('read_id', '{{read_id}}'))
            self.helper.layout.append(Submit('save', 'save'))
            self.fields['file_data'].label = "Upload JSON"
        class Meta:
            model = Read
            exclude = excluded_fields
            widgets = {
                'owner': forms.HiddenInput(),
                'type': forms.HiddenInput(),
                'password': forms.PasswordInput(),}
    return ReadJSONForm
