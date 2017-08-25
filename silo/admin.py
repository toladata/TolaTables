from django.contrib import admin
from .models import *

admin.site.register(GoogleCredentialsModel)
admin.site.register(Read)
admin.site.register(ReadType)
admin.site.register(UniqueFields)
admin.site.register(MergedSilosFieldMapping)
admin.site.register(ThirdPartyTokens)
admin.site.register(Tag)


admin.site.register(DeletedSilos, DeletedSilosAdmin)
admin.site.register(Silo, SiloAdmin)
admin.site.register(TolaUser, TolaUserAdmin)
admin.site.register(TolaSites, TolaSitesAdmin)
admin.site.register(PIIColumn, PIIColumnAdmin)
admin.site.register(Country, CountryAdmin)
admin.site.register(Organization, OrganizationAdmin)
admin.site.register(WorkflowLevel1, WorkflowLevel1Admin)
admin.site.register(WorkflowLevel2, WorkflowLevel2Admin)
