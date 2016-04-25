from tola import views as tola_views
from silo import views
from silo import tola_activity_views
from silo import google_views

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
router.register(r'silo', SiloViewSet)
router.register(r'users', UserViewSet)
router.register(r'read', ReadViewSet)
router.register(r'readtype', ReadTypeViewSet)
router.register(r'tag', TagViewSet)


urlpatterns =[
                        #rest framework
                        url(r'^api/', include(router.urls)),
                        url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
                        url(r'^api/silodata/(?P<id>[0-9]+)/$', silo_data_api, name='silo-detail'),

                        #index
                        url(r'^$', views.index, name='index'),

                        #base template for layout
                        url(r'^$', TemplateView.as_view(template_name='base.html')),

                        #rest Custom Feed
                        url(r'^api/custom/(?P<id>[0-9]+)/$', views.customFeed, name='customFeed'),

                        #enable admin documentation:
                        url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

                        #enable the admin:
                        url(r'^admin/', include(admin.site.urls)),

                        #home
                        url(r'^home', views.listSilos, name='listSilos'),

                        #read init form
                        url(r'^source/new/', views.showRead, kwargs={'id': 0}, name='newRead'),
                        url(r'^show_read/(?P<id>\w+)/$', views.showRead, name='showRead'),

                        #upload form
                        url(r'^file/(?P<id>\w+)/$', views.uploadFile, name='uploadFile'),

                        #getJSON data
                        url(r'^json', views.getJSON, name='getJSON'),

                        #login data
                        url(r'^onalogin/$', views.getOnaForms, name='getOnaForms'),
                        url(r'^provider_logout/(?P<provider>\w+)/$', views.providerLogout, name='providerLogout'),
                        url(r'^saveAndImportRead/$', views.saveAndImportRead, name='saveAndImportRead'),
                        url(r'^tolacon/$', views.tolaCon, name='tolacon'),
                        url(r'^toggle_silo_publicity/$', views.toggle_silo_publicity, name='toggle_silo_publicity'),

                        ###DISPLAY
                        #list all silos
                        url(r'^silos', views.listSilos, name='listSilos'),
                        url(r'^add_unique_fields', views.addUniqueFiledsToSilo, name='add_unique_fields_to_silo'),

                        #merge form
                        url(r'^merge/(?P<id>\w+)/$', views.mergeForm, name='mergeForm'),

                        #merge select columns
                        url(r'^merge_columns', views.mergeColumns, name='mergeColumns'),
                        url(r'^doMerge', views.doMerge, name='doMerge'),
                        url(r'^updateMergedTable/(?P<pk>\w+)/$', views.updateMergeSilo, name='updateMergedTable'),

                        #view silo detail
                        url(r'^silo_detail/(?P<id>\w+)/$', views.siloDetail, name='siloDetail'),

                        url(r'^update_column', views.updateEntireColumn, name='updateColumn'),

                        #edit single silo value
                        url(r'^value_edit/(?P<id>\w+)/$', views.valueEdit, name='valueEdit'),

                        #delete single silo value
                        url(r'^value_delete/(?P<id>\w+)/$', views.valueDelete, name='valueDelete'),

                        #edit silo
                        url(r'^silo_edit/(?P<id>\w+)/$', views.editSilo, name='editSilo'),

                        #delete a silo
                        url(r'^silo_delete/(?P<id>\w+)/$', views.deleteSilo, name='deleteSilo'),

                        #new silo column
                        url(r'^new_column/(?P<id>\w+)/$', views.newColumn, name='newColumn'),

                        #edit silo columns
                        url(r'^edit_columns/(?P<id>\w+)/$', views.editColumns, name='editColumns'),

                        #delete silo column
                        url(r'^delete_column/(?P<id>\w+)/(?P<column>\w+)/$', views.deleteColumn, name='deleteColumn'),

                        ###FEED
                        url(r'^export_to_activity/(?P<id>\d+)/$', tola_activity_views.export_to_tola_activity, name="acitivity_push"),
                        url(r'^export/(?P<id>\w+)/$', views.export_silo, name='export_silo'),
                        url(r'^export_new_gsheet/(?P<id>\d+)/$', google_views.export_new_gsheet, name='export_new_gsheet'),
                        url(r'^export_gsheet/(?P<id>\d+)/$', google_views.export_gsheet, name='export_existing_gsheet'),
                        url(r'^oauth2callback/$', google_views.oauth2callback, name='oauth2callback'),
                        url(r'^import_gsheet/(?P<id>\d+)/$', google_views.import_gsheet, name='import_gsheet'),

                        #create a feed
                        url(r'^create_feed', views.createFeed, name='createFeed'),

                        #local login COmment out local login for now
                        #url(r'^login/$', 'django.contrib.auth.views.login', name='login'),
                        #url(r'^accounts/login/$', 'django.contrib.auth.views.login', name='login'),
                        url(r'^accounts/login/$', 'django.contrib.auth.views.login', name='login'),
                        url(r'^accounts/logout/$', tola_views.logout_view, name='logout'),

                        #accounts
                        url(r'^accounts/profile/$', tola_views.profile, name='profile'),
                        #url(r'^accounts/register/$', 'tola.views.register', name='register'),

                        #Auth backend URL's
                        url('', include('django.contrib.auth.urls', namespace='auth')),
                        url('', include('social.apps.django_app.urls', namespace='social')),

                        #FAQ, Contact etc..
                        url(r'^contact', tola_views.contact, name='contact'),
                        url(r'^faq', tola_views.faq, name='faq'),
                        url(r'^documentation', tola_views.documentation, name='documentation'),


]  + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

