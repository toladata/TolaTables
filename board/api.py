from rest_framework import viewsets
#from rest_framework_jwt.authentication import JSONWebTokenAuthentication
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated

from rest_framework_json_api.parsers import JSONParser
from rest_framework_json_api.renderers import JSONRenderer

from silo.models import Silo
from .models import Board, Graph, Graphmodel, Item, Graphinput, Owner
from .serializers import BoardSerializer, GraphSerializer, GraphModelSerializer, ItemSerializer, GraphInputSerializer, BoardSiloSerializer, OwnerSerializer


class BoardViewSet(viewsets.ModelViewSet):
    queryset = Board.objects.all()
    serializer_class = BoardSerializer
    #authentication_classes = (JSONWebTokenAuthentication, )
    parser_classes = (JSONParser,)
    renderer_classes = (JSONRenderer,)
    permission_classes = []


class GraphViewSet(viewsets.ModelViewSet):
    queryset = Graph.objects.all()
    serializer_class = GraphSerializer
    parser_classes = (JSONParser,)
    renderer_classes = (JSONRenderer,)
    permission_classes = []


class GraphModelViewSet(viewsets.ModelViewSet):
    queryset = Graphmodel.objects.all()
    serializer_class = GraphModelSerializer
    parser_classes = (JSONParser,)
    renderer_classes = (JSONRenderer,)
    permission_classes = []


class ItemViewSet(viewsets.ModelViewSet):
    queryset = Item.objects.all()
    serializer_class = ItemSerializer
    parser_classes = (JSONParser,)
    renderer_classes = (JSONRenderer,)
    permission_classes = []



class GraphInputViewSet(viewsets.ModelViewSet):
    queryset = Graphinput.objects.all()
    serializer_class = GraphInputSerializer
    parser_classes = (JSONParser,)
    renderer_classes = (JSONRenderer,)
    permission_classes = []


class SiloBoardViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Silo.objects.all()
    serializer_class = BoardSiloSerializer
    parser_classes = (JSONParser,)
    renderer_classes = (JSONRenderer,)
    permission_classes = []


class OwnerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Owner.objects.all()
    serializer_class = OwnerSerializer
    parser_classes = (JSONParser,)
    renderer_classes = (JSONRenderer,)
    permission_classes = []
