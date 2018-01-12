from . import views
from django.conf.urls import url

urlpatterns = [
    # url(r'^$', views.getCommCareAuth, name='getCommCareAuth'),
    # url(r'^passform/', views.getCommCareFormPass, name='getCommCarePass'),
    url(r'^$', views.getCommCareFormPass, name='getCommCarePass'),
    url(r'^logout/$',views.commcareLogout, name='commcareLogout'),
]
