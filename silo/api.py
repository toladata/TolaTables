import json

from django.http import HttpResponseBadRequest, JsonResponse
from django.contrib.auth.models import User

from rest_framework import renderers, viewsets,filters,permissions

from .models import Silo, LabelValueStore
from .serializers import *
from silo.permissions import IsOwnerOrReadOnly
from django.contrib.auth.models import User
from rest_framework.decorators import detail_route, list_route

import django_filters

def silo_data_api(request, id):
    if id <= 0:
        return HttpResponseBadRequest("The silo_id = %s is invalid" % id)

    data = LabelValueStore.objects(silo_id=id).to_json()
    json_data = json.loads(data)
    return JsonResponse(json_data, safe=False)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class SiloViewSet(viewsets.ModelViewSet):
    """
    This viewset automatically provides `list`, `create`, `retrieve`,
    `update` and `destroy` actions.
    """
    queryset = Silo.objects.all()
    serializer_class = SiloSerializer
    lookup_field = 'id'
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,
                          IsOwnerOrReadOnly,)
    filter_fields = ('owner__username','id','tags','public')
    filter_backends = (filters.DjangoFilterBackend,)

    @detail_route()
    def data(self, request, id):
        if id <= 0:
            return HttpResponseBadRequest("The silo_id = %s is invalid" % id)

        data = LabelValueStore.objects(silo_id=id).to_json()
        json_data = json.loads(data)
        return JsonResponse(json_data, safe=False)


class TagViewSet(viewsets.ModelViewSet):
    """
    This viewset automatically provides `list`, `create`, `retrieve`,
    `update` and `destroy` actions.
    """
    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class ReadViewSet(viewsets.ModelViewSet):
    """
    This viewset automatically provides `list`, `create`, `retrieve`,
    `update` and `destroy` actions.
    """
    queryset = Read.objects.all()
    serializer_class = ReadSerializer

class ReadTypeViewSet(viewsets.ModelViewSet):
    """
    This viewset automatically provides `list`, `create`, `retrieve`,
    `update` and `destroy` actions.
    """
    queryset = ReadType.objects.all()
    serializer_class = ReadTypeSerializer

#####-------API Views to Feed Data to Tolawork API requests-----####
'''
    This view responds to the 'GET' request from TolaWork
'''
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response

@api_view(['GET'])
@authentication_classes(())
@permission_classes(())

def tables_api_view(request):
    """
   Get TolaTables Tables owned by a user logged in Tolawork,
    """
    if request.method == 'GET':
        user = request.GET.get('email')
        user_id = User.objects.get(email=user).id

        tables = Silo.objects.filter(owner=user_id).order_by('-create_date')
        serializer = SiloSerializer(tables, many=True)
        return Response(serializer.data)

