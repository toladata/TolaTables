from . import views
from django.conf.urls import url

urlpatterns = [
    url(r'file/(?P<id>\w+)/$', views.file, name='fileupload'),
    url(r'$', views.jsonuploadfile, kwargs={'id': 0}, name='jsonupload'),
]
