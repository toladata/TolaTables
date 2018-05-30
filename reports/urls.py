import reports.views

from django.conf.urls import *


# place app url patterns here

urlpatterns = [
       #display public custom dashboard
       url(r'^table_list/$', reports.views.list_table_dashboards,
           name='table_dashboard_list'),
       url(r'^table_dashboard/(?P<id>\w+)/$',
           reports.views.table_dashboard, name='table_dashboard'),
]
