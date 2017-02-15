from django.contrib.auth.models import User
#from rest_framework import serializers
from rest_framework_json_api import serializers
from .models import Board, Graph, Graphmodel, Item, Graphinput, Boardsilo, Owner

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
        model = Graphmodel
        fields = ('id', 'graph', 'name', 'label', 'isrequired', 'inputtype')



class ItemSerializer(serializers.ModelSerializer):

    class Meta:
        model = Item
        exclude = ('created', 'updated')


class GraphInputSerializer(serializers.ModelSerializer):

    class Meta:
        model = Graphinput
        exclude = ('created', 'updated')


class BoardSiloSerializer(serializers.ModelSerializer):
    silodata = serializers.SerializerMethodField()
    createddate = serializers.SerializerMethodField()

    class Meta:
        model = Boardsilo
        fields = ('owner', 'name', 'reads', 'description', 'createddate', 'id', 'silodata','shared','tags','public')

    def get_silodata(self, obj):
        link = "/api/silo/" + str(obj.id) + "/data"
        return (self.context['request'].build_absolute_uri(link))

    def get_createddate(self, obj):
        return obj.create_date

class OwnerSerializer(serializers.ModelSerializer):
    firstname = serializers.SerializerMethodField()
    lastname = serializers.SerializerMethodField()

    class Meta:
        model = Owner
        fields = ('id', 'username', 'firstname', 'lastname', 'email')

    def get_firstname(self, obj):
        return obj.first_name

    def get_lastname(self, obj):
        return obj.last_name

