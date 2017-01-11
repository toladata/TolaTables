from django.forms import widgets
from rest_framework import serializers
from silo.models import Silo, Read, ReadType, LabelValueStore, Tag
from tola.models import LoggedUser
from django.contrib.auth.models import User
import json


class PublicSiloSerializer(serializers.HyperlinkedModelSerializer):
    data = serializers.SerializerMethodField()
    class Meta:
        model = Silo
        fields = ('owner', 'name', 'reads', 'description', 'create_date', 'id', 'data','shared','tags','public')

    def get_data(self, obj):
        link = "/api/public_tables/" + str(obj.id) + "/data/"
        return (self.context['request'].build_absolute_uri(link))

class SiloSerializer(serializers.HyperlinkedModelSerializer):
    data = serializers.SerializerMethodField()
    class Meta:
        model = Silo
        fields = ('owner', 'name', 'reads', 'description', 'create_date', 'id', 'data','shared','tags','public')
        depth =1

    def get_data(self, obj):
        link = "/api/silo/" + str(obj.id) + "/data/"
        return (self.context['request'].build_absolute_uri(link))

class TagSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Tag
        fields = ('name', 'owner')

class UserSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = User
        fields = ('url', 'username', 'email', 'is_staff')


class ReadSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Read
        fields = ('pk', 'owner', 'type', 'read_name', 'read_url', 'autopull_frequency', 'autopush_frequency')


class ReadTypeSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = ReadType
        fields = ( 'read_type', 'description')


class SiloModelSerializer(serializers.ModelSerializer):

    class Meta:
        model = Silo
        fields = ('name', 'description', 'create_date', 'public')
        depth =1

class LoggedUserSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = LoggedUser
        fields = ('username', 'country', 'email')