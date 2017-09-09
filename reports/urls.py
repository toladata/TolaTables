import reports.views

from django.conf.urls import *


# place app url patterns here

urlpatterns = [

       #display public custom dashboard
       url(r'^table_list/$', reports.views.listTableDashboards, name='table_dashboard_list'),
       url(r'^table_dashboard/(?P<id>\w+)/$', reports.views.tableDashboard, name='table_dashboard'),

]
