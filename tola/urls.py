from django.contrib import auth
from django.conf.urls import include, url
from rest_framework import routers
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.views import login
from django.contrib import admin

from util import getImportApps
from silo import views, gviews_v4
from silo.api import *
from tola import views as tola_views

admin.autodiscover()


# REST FRAMEWORK
router = routers.DefaultRouter(trailing_slash=False)
router.register(r'silo', SiloViewSet, base_name="silos")
router.register(r'usersilos', SilosByUser, base_name='usersilos')
router.register(r'public_tables', PublicSiloViewSet, base_name="public_tables")
router.register(r'users', UserViewSet)
router.register(r'read', ReadViewSet, base_name='read')
router.register(r'readtype', ReadTypeViewSet)
router.register(r'tag', TagViewSet)
router.register(r'country', CountryViewSet)
router.register(r'customform', CustomFormViewSet, base_name='customform')
router.register(r'organization', OrganizationViewSet)
router.register(r'tolauser', TolaUserViewSet)
router.register(r'workflowlevel1', WorkflowLevel1ViewSet)
router.register(r'workflowlevel2', WorkflowLevel2ViewSet)


urlpatterns =[
    url(r'^api/', include(router.urls)),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^api/docs/', tola_views.schema_view),

    url(r'^admin/', include(admin.site.urls)),
    url(r'^$', views.IndexView.as_view(), name='index'),

    url(r'^source/new/', views.showRead, kwargs={'id': 0}, name='newRead'),
    url(r'^onedrive', views.oneDrive, name='oneDriveRedirect'),
    url(r'^import_onedrive/(?P<id>\d+)/$', views.oneDriveImport, name='import_onedrive'),
    # url(r'^source/FormulaColumnF/', views.showRead, kwargs={'id': 0}, name='newRead'),

    url(r'^show_read/(?P<id>\w+)/$', views.showRead, name='showRead'),

    url(r'^file/(?P<id>\w+)/$', views.uploadFile, name='uploadFile'),
    url(r'^json', views.getJSON, name='getJSON'),

    url(r'^onalogin/$', views.getOnaForms, name='getOnaForms'),
    url(r'^provider_logout/(?P<provider>\w+)/$', views.providerLogout, name='providerLogout'),
    url(r'^saveAndImportRead/$', views.saveAndImportRead, name='saveAndImportRead'),
    url(r'^toggle_silo_publicity/$', views.toggle_silo_publicity, name='toggle_silo_publicity'),

    url(r'^silos', views.listSilos, name='listSilos'),
    url(r'^silo_detail/(?P<silo_id>\w+)/$', views.siloDetail, name='siloDetail'),
    url(r'^silo_edit/(?P<id>\w+)/$', views.editSilo, name='editSilo'),
    url(r'^silo_delete/(?P<id>\w+)/$', views.deleteSilo, name='deleteSilo'),
    url(r'^add_unique_fields', views.addUniqueFiledsToSilo, name='add_unique_fields_to_silo'),
    url(r'^anonymize_silo/(?P<id>\w+)/$', views.anonymizeTable, name='anonymize_table'),
    url(r'^identifyPII/(?P<silo_id>\w+)/$', views.identifyPII, name='identifyPII'),
    url(r'^source_remove/(?P<silo_id>\w+)/(?P<read_id>\w+)/$', views.removeSource, name='removeSource'),

    url(r'^merge/(?P<id>\w+)/$', views.mergeForm, name='mergeForm'),
    url(r'^merge_columns', views.mergeColumns, name='mergeColumns'),
    url(r'^do_merge', views.do_merge, name='do_merge'),
    url(r'^updateMergedTable/(?P<pk>\w+)/$', views.updateSiloData, name='updateMergedTable'),

    url(r'^update_column', views.updateEntireColumn, name='updateColumn'),
    url(r'^value_edit/(?P<id>\w+)/$', views.valueEdit, name='valueEdit'),
    url(r'^value_delete/(?P<id>\w+)/$', views.valueDelete, name='valueDelete'),
    url(r'^new_column/(?P<id>\w+)/$', views.newColumn, name='newColumn'),
    url(r'^new_formula_column/(?P<pk>\w+)/$', views.newFormulaColumn, name='newFormulaColumn'),
    url(r'^edit_filter/(?P<pk>\w+)/$', views.addColumnFilter, name='editColumnFilter'),
    url(r'^edit_columns/(?P<id>\w+)/$', views.edit_columns, name='editColumns'),
    url(r'^delete_column/(?P<id>\w+)/(?P<column>\w+)/$', views.deleteColumn, name='deleteColumn'),
    url(r'^edit_column_order/(?P<pk>\w+)/$', views.editColumnOrder, name='editColumnOrder'),
    url(r'^set_column_type/(?P<pk>\w+)/$', views.setColumnType, name='setColumnType'),

    url(r'^export_silo_form/(?P<id>\w+)/$', views.export_silo_form, name='export_silo_form'),
    url(r'^export/(?P<id>\w+)/$', views.export_silo, name='export_silo'),

    url(r'^export_to_gsheet/(?P<id>\d+)/$', gviews_v4.export_to_gsheet, name='export_new_gsheet'),
    url(r'^export_to_gsheet/(?P<id>\d+)/$', gviews_v4.export_to_gsheet, name='export_existing_gsheet'),
    url(r'^oauth2callback/$', gviews_v4.oauth2callback, name='oauth2callback'),
    url(r'^import_gsheet/(?P<id>\d+)/$', gviews_v4.import_from_gsheet, name='import_gsheet'),
    url(r'^get_sheets_from_google_spreadsheet/$', gviews_v4.get_sheets_from_google_spreadsheet, name='get_sheets'),

    url(r'^accounts/login/$', auth.views.login, name='login'),
    url(r'^accounts/logout/$', tola_views.logout_view, name='logout'),
    url(r'^accounts/register/$', tola_views.register, name='register'),

    url(r'^accounts/profile/$', tola_views.profile, name='profile'),
    url(r'^board/$', tola_views.BoardView.as_view(), name='board'),

    url(r'^tables_login/$', views.tablesLogin, name='tables_login'),

    url(r'^renew_auto/(?P<read_pk>\d+)/(?P<operation>(pull|push))/$', views.renewAutoJobs, name='renewsAutoJobs'),

    # Auth backend URL's
    url('', include('django.contrib.auth.urls', namespace='auth')),
    url('', include('social_django.urls', namespace='social')),

    # reports and dashboards
    url(r'^reports/', include('reports.urls')),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


#add app domains and add the data types to the read_type.json
folders = getImportApps()
for app in folders:
    url_construct = app + '/'
    url_include = app + '.urls'
    urlpatterns.append(url(url_construct,include(url_include)))
