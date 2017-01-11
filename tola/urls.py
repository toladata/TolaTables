from tola import views as tola_views
from silo import views
from silo import gviews_v4
from silo import tola_activity_views
from silo import google_views

from django.contrib import auth
from django.conf.urls import patterns, include, url
from django.views.generic import TemplateView
from django.contrib.auth.models import User
from rest_framework.routers import DefaultRouter
from rest_framework.urlpatterns import format_suffix_patterns
from rest_framework import routers, serializers, viewsets
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.views import login, logout
from silo.api import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

#REST FRAMEWORK
router = routers.DefaultRouter()
router.register(r'silo', SiloViewSet, base_name="silo")
router.register(r'public_tables', PublicSiloViewSet, base_name="public_tables")
router.register(r'users', UserViewSet)
router.register(r'read', ReadViewSet)
router.register(r'readtype', ReadTypeViewSet)
router.register(r'tag', TagViewSet)


urlpatterns =[
    url(r'^api/', include(router.urls)),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),

    url(r'^admin/', include(admin.site.urls)),
    url(r'^$', views.index, name='index'),

    url(r'^source/new/', views.showRead, kwargs={'id': 0}, name='newRead'),
    url(r'^show_read/(?P<id>\w+)/$', views.showRead, name='showRead'),

    url(r'^file/(?P<id>\w+)/$', views.uploadFile, name='uploadFile'),
    url(r'^json', views.getJSON, name='getJSON'),

    url(r'^onalogin/$', views.getOnaForms, name='getOnaForms'),
    url(r'^provider_logout/(?P<provider>\w+)/$', views.providerLogout, name='providerLogout'),
    url(r'^saveAndImportRead/$', views.saveAndImportRead, name='saveAndImportRead'),
    url(r'^toggle_silo_publicity/$', views.toggle_silo_publicity, name='toggle_silo_publicity'),

    url(r'^silos', views.listSilos, name='listSilos'),
    url(r'^silo/(?P<id>\w+)/$', views.siloDetail_OLD, name='siloDetail2'),
    url(r'^silo_detail/(?P<silo_id>\w+)/$', views.siloDetail, name='siloDetail'),
    url(r'^silo_edit/(?P<id>\w+)/$', views.editSilo, name='editSilo'),
    url(r'^silo_delete/(?P<id>\w+)/$', views.deleteSilo, name='deleteSilo'),
    url(r'^add_unique_fields', views.addUniqueFiledsToSilo, name='add_unique_fields_to_silo'),
    url(r'^anonymize_silo/(?P<id>\w+)/$', views.anonymizeTable, name='anonymize_table'),
    url(r'^identifyPII/(?P<silo_id>\w+)/$', views.identifyPII, name='identifyPII'),

    url(r'^merge/(?P<id>\w+)/$', views.mergeForm, name='mergeForm'),
    url(r'^merge_columns', views.mergeColumns, name='mergeColumns'),
    url(r'^doMerge', views.doMerge, name='doMerge'),
    url(r'^updateMergedTable/(?P<pk>\w+)/$', views.updateSiloData, name='updateMergedTable'),

    url(r'^update_column', views.updateEntireColumn, name='updateColumn'),
    url(r'^value_edit/(?P<id>\w+)/$', views.valueEdit, name='valueEdit'),
    url(r'^value_delete/(?P<id>\w+)/$', views.valueDelete, name='valueDelete'),
    url(r'^new_column/(?P<id>\w+)/$', views.newColumn, name='newColumn'),
    url(r'^edit_columns/(?P<id>\w+)/$', views.editColumns, name='editColumns'),
    url(r'^delete_column/(?P<id>\w+)/(?P<column>\w+)/$', views.deleteColumn, name='deleteColumn'),

    url(r'^export_to_activity/(?P<id>\d+)/$', tola_activity_views.export_to_tola_activity, name="acitivity_push"),
    url(r'^export/(?P<id>\w+)/$', views.export_silo, name='export_silo'),
    url(r'^export_to_gsheet/(?P<id>\d+)/$', gviews_v4.export_to_gsheet, name='export_new_gsheet'),
    url(r'^export_to_gsheet/(?P<id>\d+)/$', gviews_v4.export_to_gsheet, name='export_existing_gsheet'),
    url(r'^oauth2callback/$', gviews_v4.oauth2callback, name='oauth2callback'),
    url(r'^import_gsheet/(?P<id>\d+)/$', gviews_v4.import_from_gsheet, name='import_gsheet'),
    url(r'^get_sheets_from_google_spredsheet/$', gviews_v4.get_sheets_from_google_spredsheet, name='get_sheets'),

    url(r'^accounts/login/$', auth.views.login, name='login'),
    url(r'^accounts/logout/$', tola_views.logout_view, name='logout'),

    url(r'^accounts/profile/$', tola_views.profile, name='profile'),

    #Auth backend URL's
    url('', include('django.contrib.auth.urls', namespace='auth')),
    url('', include('social.apps.django_app.urls', namespace='social')),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


