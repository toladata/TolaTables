from rest_framework import viewsets
from rest_framework_json_api.views import ModelViewSet
#from rest_framework_jwt.authentication import JSONWebTokenAuthentication
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated

from rest_framework_json_api.parsers import JSONParser
from rest_framework_json_api.renderers import JSONRenderer
from rest_framework_json_api.metadata import JSONAPIMetadata
from silo.models import Silo
from .models import Board, Graph, Graphmodel, Item, Graphinput, Owner
from .serializers import BoardSerializer, GraphSerializer, GraphModelSerializer, ItemSerializer, GraphInputSerializer, BoardSiloSerializer, OwnerSerializer

from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework import exceptions
from rest_framework import viewsets
import rest_framework.parsers
import rest_framework.renderers
import rest_framework_json_api.metadata
import rest_framework_json_api.parsers
import rest_framework_json_api.renderers
from rest_framework_json_api.views import RelationshipView


from rest_framework_json_api.utils import format_drf_errors

HTTP_422_UNPROCESSABLE_ENTITY = 422

class JsonApiViewSet(viewsets.ModelViewSet):
    """
    Configuring DRF-jsonapi from within a class so that it can be used alongside
    vanilla DRF API views.
    """
    parser_classes = [
        rest_framework_json_api.parsers.JSONParser,
        rest_framework.parsers.FormParser,
        rest_framework.parsers.MultiPartParser,
    ]
    renderer_classes = [
        rest_framework_json_api.renderers.JSONRenderer,
        rest_framework.renderers.BrowsableAPIRenderer,
    ]
    metadata_class = rest_framework_json_api.metadata.JSONAPIMetadata

    def handle_exception(self, exc):
        if isinstance(exc, exceptions.ValidationError):
            # some require that validation errors return 422 status
            # for example ember-data (isInvalid method on adapter)
            exc.status_code = HTTP_422_UNPROCESSABLE_ENTITY
        # exception handler can't be set on class so you have to
        # override the error response in this method
        response = super(JsonApiViewSet, self).handle_exception(exc)
        context = self.get_exception_handler_context()
        return format_drf_errors(response, context, exc)


class BoardViewSet(JsonApiViewSet):
    queryset = Board.objects.all()
    serializer_class = BoardSerializer
    authentication_classes = (BasicAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)


class GraphViewSet(JsonApiViewSet):
    queryset = Graph.objects.all()
    serializer_class = GraphSerializer
    permission_classes = (IsAuthenticated,)


class GraphModelViewSet(JsonApiViewSet):
    queryset = Graphmodel.objects.all()
    serializer_class = GraphModelSerializer
    authentication_classes = (BasicAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)


class ItemViewSet(JsonApiViewSet):
    queryset = Item.objects.all()
    serializer_class = ItemSerializer
    authentication_classes = (BasicAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)



class GraphInputViewSet(JsonApiViewSet):
    queryset = Graphinput.objects.all()
    serializer_class = GraphInputSerializer
    authentication_classes = (BasicAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)


class SiloBoardViewSet(JsonApiViewSet):
    queryset = Silo.objects.all()
    serializer_class = BoardSiloSerializer
    authentication_classes = (BasicAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)


class OwnerViewSet(JsonApiViewSet):
    queryset = Owner.objects.all()
    serializer_class = OwnerSerializer
    authentication_classes = (BasicAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)

