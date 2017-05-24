from __future__ import unicode_literals

from django.apps import AppConfig



class CommcareConfig(AppConfig):
    name = 'commcare'
    verbose_name = 'CommCare'
    def ready(self):
        from silo.models import ReadType
        ReadType.objects.get_or_create(read_type = "CommCare")
