from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Board, Graph, GraphModel, Item, GraphInput
from silo.models import Silo

class BoardSerializer(serializers.ModelSerializer):

    class Meta:
        model = Board
        fields = ('id', 'owner', 'title')


class GraphSerializer(serializers.ModelSerializer):

    class Meta:
        model = Graph
        fields = ('id', 'label', 'thumbnail', 'embercomponent')


class GraphModelSerializer(serializers.ModelSerializer):

    class Meta:
        model = GraphModel
        fields = ('id', 'graph', 'name', 'label', 'isrequired', 'inputtype')



class ItemSerializer(serializers.ModelSerializer):

    class Meta:
        model = Item
        exclude = ('created', 'updated')


class GraphInputSerializer(serializers.ModelSerializer):

    class Meta:
        model = GraphInput
        exclude = ('created', 'updated')


class SiloSerializer(serializers.ModelSerializer):
    data = serializers.SerializerMethodField()
    class Meta:
        model = Silo
        fields = ('owner', 'name', 'reads', 'description', 'create_date', 'id', 'data','shared','tags','public')
        depth =1

    def get_data(self, obj):
        link = "/api/silo/" + str(obj.id) + "/data"
        return (self.context['request'].build_absolute_uri(link))