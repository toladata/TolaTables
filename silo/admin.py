from django.contrib import admin
from .models import Silo, Read, ReadType, GoogleCredentialsModel, UniqueFields, MergedSilosFieldMapping, TolaSites, TolaSitesAdmin

admin.site.register(GoogleCredentialsModel)
admin.site.register(Read)
admin.site.register(ReadType)
admin.site.register(UniqueFields)
admin.site.register(MergedSilosFieldMapping)
admin.site.register(TolaSites,TolaSitesAdmin)
admin.site.register(Silo)