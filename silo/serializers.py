from django.forms import widgets
from rest_framework import serializers
from silo.models import Silo, Read, ReadType, Tag, Organization, Country, Workflowlevel1, Workflowlevel2
from tola.models import LoggedUser
from django.contrib.auth.models import User
import json


class PublicSiloSerializer(serializers.HyperlinkedModelSerializer):
    data = serializers.SerializerMethodField()
    class Meta:
        model = Silo
        fields = ('owner', 'name', 'reads', 'description', 'create_date', 'id', 'data','shared','tags','public')

    def get_data(self, obj):
        link = "/api/public_tables/" + str(obj.id) + "/data"
        return (self.context['request'].build_absolute_uri(link))

class SiloSerializer(serializers.HyperlinkedModelSerializer):
    data = serializers.SerializerMethodField()
    data_count = serializers.ReadOnlyField()

    class Meta:
        model = Silo
        fields = ('owner', 'name', 'reads', 'description', 'create_date', 'id', 'data','shared','tags','public', 'data_count')
        depth =1

    def get_data(self, obj):
        link = "/api/silo/" + str(obj.id) + "/data"
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


class OrganizationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Organization
        fields = '__all__'


class CountrySerializer(serializers.ModelSerializer):

    class Meta:
        model = Country
        fields = '__all__'


class Workflowlevel1Serializer(serializers.ModelSerializer):

    class Meta:
        model = Workflowlevel1
        fields = '__all__'


class Workflowlevel2Serializer(serializers.ModelSerializer):

    class Meta:
        model = Workflowlevel2
        fields = '__all__'


class LoggedUserSerializer(serializers.ModelSerializer):

    class Meta:
        model = LoggedUser
        fields = ('username', 'country', 'email')