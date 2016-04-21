from django.contrib import admin
from .models import *

admin.site.register(GoogleCredentialsModel)
admin.site.register(Read)
admin.site.register(ReadType)
admin.site.register(UniqueFields)
admin.site.register(MergedSilosFieldMapping)
admin.site.register(ThirdPartyTokens)
admin.site.register(Tag)

admin.site.register(Silo, SiloAdmin)
admin.site.register(TolaUser, TolaUserAdmin)
admin.site.register(TolaSites, TolaSitesAdmin)