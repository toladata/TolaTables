import random

from django.utils import timezone

from factory import (DjangoModelFactory, LazyAttribute, SubFactory,
                     post_generation, Iterator)

from silo.models import (
    Country as CountryM,
    LabelValueStore as LabelValueStoreM,
    Organization as OrganizationM,
    Read as ReadM,
    ReadType as ReadTypeM,
    Silo as SiloM,
    Tag as TagM,
    ThirdPartyTokens as ThirdPartyTokensM,
    TolaSites as TolaSitesM,
    TolaUser as TolaUserM,
    WorkflowLevel1 as WorkflowLevel1M,
)
from .user_models import User


class Country(DjangoModelFactory):
    class Meta:
        model = CountryM
        django_get_or_create = ('country', 'code')

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


class WorkflowLevel1(DjangoModelFactory):
    class Meta:
        model = WorkflowLevel1M

    level1_uuid = random.randint(1, 9999)
    name = 'Health and Survival for Syrians in Affected Regions'


class ReadType(DjangoModelFactory):
    class Meta:
        model = ReadTypeM
        django_get_or_create = ('read_type',)

    read_type = Iterator(['CustomForm', 'OneDrive', 'CommCare', 'JSON',
                          'GSheet Import', 'CSV', 'ONA'])


class Read(DjangoModelFactory):
    class Meta:
        model = ReadM

    owner = SubFactory(User)
    type = SubFactory(ReadType)


class TolaSites(DjangoModelFactory):
    class Meta:
        model = TolaSitesM
        django_get_or_create = ('name', 'site_id')

    name = 'Track'
    site_id = '1'


class Tag(DjangoModelFactory):
    class Meta:
        model = TagM
        django_get_or_create = ('name', 'owner')

    name = 'Test'


class Silo(DjangoModelFactory):
    class Meta:
        model = SiloM

    owner = SubFactory(User)
    name = 'Syria Security Incidences'
    description = 'Reports from police and private security agents'
    organization = SubFactory(Organization)
    country = SubFactory(Country, country='Syria', code='SY')
    public = False

    @post_generation
    def reads(self, create, extracted, **kwargs):
        if not create:
            # Simple build, do nothing.
            return

        if type(extracted) is list:
            # A list of reads were passed in, use them
            for reads in extracted:
                self.reads.add(reads)
        else:
            self.reads.add(Read())

    @post_generation
    def tags(self, create, extracted, **kwargs):
        if not create:
            # Simple build, do nothing.
            return

        if extracted:
            # A list of tags were passed in, use them
            for tags in extracted:
                self.tags.add(tags)

        if type(extracted) is list:
            for tag in extracted:
                self.tags.add(tag)
        else:
            self.tags.add(Tag(name='security', owner=self.owner))
            self.tags.add(Tag(name='report', owner=self.owner))


    @post_generation
    def shared(self, create, extracted, **kwargs):
        if not create:
            # Simple build, do nothing.
            return

        if type(extracted) is list:
            for shared in extracted:
                self.shared.add(shared)

    @post_generation
    def workflowlevel1(self, create, extracted, **kwargs):
        if not create:
            # Simple build, do nothing.
            return

        if extracted:
            # A list of program were passed in, use them
            for workflowlevel1 in extracted:
                self.workflowlevel1.add(workflowlevel1)

    @post_generation
    def formulacolumns(self, create, extracted, **kwargs):
        if not create:
            # Simple build, do nothing.
            return

        if extracted:
            # A list of formulacolumns were passed in, use them
            for formulacolumns in extracted:
                self.formulacolumns.add(formulacolumns)


class LabelValueStore(DjangoModelFactory):
    class Meta:
        model = LabelValueStoreM

    create_date = timezone.now()


class ThirdPartyTokens(DjangoModelFactory):
    class Meta:
        model = ThirdPartyTokensM

    user = SubFactory(User)
    token = str(random.randint(1, 9999))
