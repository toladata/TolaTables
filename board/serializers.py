from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Board, Graph, GraphModel, Item, GraphInput

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