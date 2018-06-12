from rest_framework import serializers

from django.contrib.auth.models import User

from tola.models import LoggedUser
from silo.models import (Silo, Read, ReadType, Tag, Organization, Country,
                         TolaUser, WorkflowLevel1, WorkflowLevel2)


class PublicSiloSerializer(serializers.HyperlinkedModelSerializer):
    data = serializers.SerializerMethodField()

    class Meta:
        model = Silo
        fields = ('owner', 'name', 'reads', 'description', 'create_date', 'id', 'data','shared','tags','public')

    def get_data(self, obj):
        link = "/api/public_tables/" + str(obj.id) + "/data"
        return self.context['request'].build_absolute_uri(link)


class UserSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = User
        fields = ('url', 'username', 'email', 'is_staff')


class TolaUserSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()

    class Meta:
        model = TolaUser
        fields = '__all__'
        depth = 1


class SiloSerializer(serializers.HyperlinkedModelSerializer):
    data = serializers.SerializerMethodField()
    data_count = serializers.ReadOnlyField()
    owner = UserSerializer()

    class Meta:
        model = Silo
        fields = ('owner', 'name', 'reads', 'description', 'create_date',
                  'id', 'data', 'shared', 'tags', 'public', 'data_count',
                  'columns')
        # removind depth for now, it may be breaking the post method
        # depth =1

    def get_data(self, obj):
        link = "/api/silo/" + str(obj.id) + "/data"
        return self.context['request'].build_absolute_uri(link)


class CustomFormSerializer(serializers.ModelSerializer):
    fields = serializers.JSONField()
    level1_uuid = serializers.CharField(max_length=255)
    tola_user_uuid = serializers.CharField(max_length=255)
    form_uuid = serializers.CharField(max_length=255)

    class Meta:
        model = Silo
        fields = ('id', 'name', 'description', 'fields', 'level1_uuid',
                  'tola_user_uuid', 'form_uuid')


class TagSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Tag
        fields = ('name', 'owner')


class ReadSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Read
        fields = ('pk', 'owner', 'type', 'read_name', 'read_url', 'autopull_frequency', 'autopush_frequency', 'autopull_expiration', 'autopush_expiration')


class ReadTypeSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = ReadType
        fields = ( 'read_type', 'description')


class SiloModelSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField()

    class Meta:
        model = Silo
        fields = ('id', 'name', 'description', 'create_date', 'public')
        depth = 1


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


class WorkflowLevel1Serializer(serializers.ModelSerializer):

    class Meta:
        model = WorkflowLevel1
        fields = '__all__'


class WorkflowLevel2Serializer(serializers.ModelSerializer):

    class Meta:
        model = WorkflowLevel2
        fields = '__all__'
