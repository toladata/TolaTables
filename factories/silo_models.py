import random
from factory import DjangoModelFactory, LazyAttribute, SubFactory

from silo.models import (
    Country as CountryM,
    Organization as OrganizationM,
    ReadType as ReadTypeM,
    TolaUser as TolaUserM,
    WorkflowLevel1 as WorkflowLevel1M,
)
from .user_models import User


class Country(DjangoModelFactory):
    class Meta:
        model = CountryM

    country = 'Afghanistan'
    code = 'AF'


class Organization(DjangoModelFactory):
    class Meta:
        model = OrganizationM

    name = 'Tola Org'


class TolaUser(DjangoModelFactory):
    class Meta:
        model = TolaUserM

    user = SubFactory(User)
    name = LazyAttribute(lambda o: o.user.first_name + " " + o.user.last_name)
    organization = SubFactory(Organization)
    country = SubFactory(Country, country='Germany', code='DE')
    tola_user_uuid = random.randint(1, 9999)


class WorkflowLevel1(DjangoModelFactory):
    class Meta:
        model = WorkflowLevel1M

    level1_uuid = random.randint(1, 9999)
    name = 'Health and Survival for Syrians in Affected Regions'


class ReadType(DjangoModelFactory):
    class Meta:
        model = ReadTypeM

    read_type = 'CustomForm'
