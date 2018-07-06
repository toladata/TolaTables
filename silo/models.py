import uuid

from django.conf import settings
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from mongoengine import DynamicDocument, IntField, DateTimeField
from oauth2client.contrib.django_orm import CredentialsField
from rest_framework.authtoken.models import Token

from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.fields import GenericRelation


class CeleryTask(models.Model):
    TASK_CREATED = 'CREATED'
    TASK_IN_PROGRESS = 'IN_PROGRESS'
    TASK_FINISHED = 'FINISHED'
    TASK_FAILED = 'FAILED'

    TASK_STATUS_CHOICES = (
        (TASK_CREATED, 'CREATED'),
        (TASK_IN_PROGRESS, 'IN_PROGRESS'),
        (TASK_FINISHED, 'FINISHED'),
        (TASK_FAILED, 'FAILED'),
    )

    task_id = models.CharField(max_length=50, blank=True, null=True, default=None, verbose_name='Celery task id')
    task_status = models.CharField(max_length=25, choices=TASK_STATUS_CHOICES, null=True, blank=True,
                                   verbose_name='Celery task status')

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')


# New user created generate a token
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)


class TolaSites(models.Model):
    name = models.CharField(blank=True, null=True, max_length=255)
    agency_name = models.CharField(blank=True, null=True, max_length=255)
    agency_url = models.CharField(blank=True, null=True, max_length=255)
    activity_url = models.CharField(blank=True, null=True, max_length=255)
    tola_report_url = models.CharField(blank=True, null=True, max_length=255)
    tola_activity_user = models.CharField(blank=True, null=True, max_length=255)
    tola_activity_token = models.CharField(blank=True, null=True, max_length=255)
    site = models.ForeignKey(Site)
    privacy_disclaimer = models.TextField(blank=True, null=True)
    created = models.DateTimeField(auto_now=False, blank=True, null=True)
    updated = models.DateTimeField(auto_now=False, blank=True, null=True)

    def __unicode__(self):
        return self.name

    @property
    def countries_list(self):
        return ', '.join([x.code for x in self.countries.all()])

    def save(self, *args, **kwargs):
        ''' On save, update timestamps as appropriate'''
        if kwargs.pop('new_entry', True):
            self.created = timezone.now()
        else:
            self.updated = timezone.now()
        return super(TolaSites, self).save(*args, **kwargs)


class TolaSitesAdmin(admin.ModelAdmin):
    list_display = ('name', 'agency_name')
    display = 'Tola Site'
    list_filter = ('name',)
    search_fields = ('name','agency_name')


class Organization(models.Model):
    organization_uuid = models.CharField(max_length=255, verbose_name='Organization UUID', default=uuid.uuid4, unique=True)
    name = models.CharField("Organization Name", max_length=255, blank=True, default="TolaData")
    description = models.TextField("Description/Notes", max_length=765, null=True, blank=True)
    organization_url = models.CharField(blank=True, null=True, max_length=255)
    level_1_label = models.CharField("Project/Program Organization Level 1 label", default="Program", max_length=255, blank=True)
    level_2_label = models.CharField("Project/Program Organization Level 2 label", default="Project", max_length=255, blank=True)
    level_3_label = models.CharField("Project/Program Organization Level 3 label", default="Component", max_length=255, blank=True)
    level_4_label = models.CharField("Project/Program Organization Level 4 label", default="Activity", max_length=255, blank=True)
    create_date = models.DateTimeField(null=True, blank=True)
    edit_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ('name',)
        verbose_name_plural = "Organizations"

    # on save add create date or update edit date
    def save(self, *args, **kwargs):
        if self.create_date == None:
            self.create_date = timezone.now()
        self.edit_date = timezone.now()
        super(Organization, self).save()

    # displayed in admin templates
    def __unicode__(self):
        return self.name


class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'create_date', 'edit_date')
    display = 'Organization'


class Country(models.Model):
    country = models.CharField("Country Name", max_length=255, blank=True)
    organization = models.ForeignKey(Organization, blank=True, null=True)
    code = models.CharField("2 Letter Country Code", max_length=4, blank=True)
    description = models.TextField("Description/Notes", max_length=765,blank=True)
    latitude = models.CharField("Latitude", max_length=255, null=True, blank=True)
    longitude = models.CharField("Longitude", max_length=255, null=True, blank=True)
    create_date = models.DateTimeField(null=True, blank=True)
    edit_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ('country',)
        verbose_name_plural = "Countries"

    #onsave add create date or update edit date
    def save(self, *args, **kwargs):
        if self.create_date == None:
            self.create_date = timezone.now()
        self.edit_date = timezone.now()
        super(Country, self).save()

    #displayed in admin templates
    def __unicode__(self):
        return self.country


class CountryAdmin(admin.ModelAdmin):
    list_display = ('country', 'create_date', 'edit_date')
    display = 'Country'


class WorkflowLevel1(models.Model):
    country = models.ForeignKey(Country, blank=True, null=True)
    organization = models.ForeignKey(Organization, blank=True, null=True)
    level1_uuid = models.CharField(max_length=255, verbose_name='WorkflowLevel1 UUID', unique=True)
    name = models.CharField("Name", max_length=255, blank=True)
    create_date = models.DateTimeField(null=True, blank=True)
    edit_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ('country',)
        verbose_name_plural = "Workflowlevel 1"

    #onsave add create date or update edit date
    def save(self, *args, **kwargs):
        if self.create_date == None:
            self.create_date = timezone.now()
        self.edit_date = timezone.now()
        super(WorkflowLevel1, self).save()

    #displayed in admin templates
    def __unicode__(self):
        return self.name


class WorkflowLevel1Admin(admin.ModelAdmin):
    list_display = ('country', 'organization', 'name')
    display = 'Workflowlevel 1'


class WorkflowLevel2(models.Model):
    country = models.ForeignKey(Country, blank=True, null=True)
    organization = models.ForeignKey(Organization, blank=True, null=True)
    workflowlevel1 = models.ForeignKey(WorkflowLevel1)
    level2_uuid = models.CharField(max_length=255, verbose_name='WorkflowLevel2 UUID', unique=True)
    name = models.CharField("Name", max_length=255, blank=True)
    activity_id = models.IntegerField("ID", blank=True, null=True)
    create_date = models.DateTimeField(null=True, blank=True)
    edit_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ('country',)
        verbose_name_plural = "Workflowlevel 2"

    #onsave add create date or update edit date
    def save(self, *args, **kwargs):
        if self.create_date == None:
            self.create_date = timezone.now()
        self.edit_date = timezone.now()
        super(WorkflowLevel2, self).save()

    #displayed in admin templates
    def __unicode__(self):
        return self.name


class WorkflowLevel2Admin(admin.ModelAdmin):
    list_display = ('country', 'organization', 'name')
    display = 'Workflowlevel 2'


TITLE_CHOICES = (
    ('mr', 'Mr.'),
    ('mrs', 'Mrs.'),
    ('ms', 'Ms.'),
)


class TolaUser(models.Model):
    tola_user_uuid = models.CharField(max_length=255, verbose_name='TolaUser UUID', default=uuid.uuid4, unique=True)
    title = models.CharField(blank=True, null=True, max_length=3, choices=TITLE_CHOICES)
    organization = models.ForeignKey(Organization, blank=True, null=True)
    name = models.CharField("Given Name", blank=True, null=True, max_length=100)
    employee_number = models.IntegerField("Employee Number", blank=True, null=True)
    user = models.OneToOneField(User, unique=True, related_name='tola_user')
    country = models.ForeignKey(Country, blank=True, null=True)
    workflowlevel1 = models.ForeignKey(WorkflowLevel1, blank=True, null=True)
    tables_api_token = models.CharField(blank=True, null=True, max_length=255)
    activity_api_token = models.CharField(blank=True, null=True, max_length=255)
    privacy_disclaimer_accepted = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now=False, blank=True, null=True)
    updated = models.DateTimeField(auto_now=False, blank=True, null=True)

    def __unicode__(self):
        return self.name if self.name is not None else '-'

    def save(self, *args, **kwargs):
        ''' On save, update timestamps as appropriate'''
        if kwargs.pop('new_entry', True):
            self.created = timezone.now()
        else:
            self.updated = timezone.now()
        return super(TolaUser, self).save(*args, **kwargs)


class TolaUserAdmin(admin.ModelAdmin):
    list_display = ('name', 'country')
    display = 'Tola User'
    list_filter = ('country',)
    search_fields = ('name','country__country','title')


class GoogleCredentialsModel(models.Model):
    id = models.OneToOneField(User, primary_key=True, related_name='google_credentials')
    credential = CredentialsField()


class ThirdPartyTokens(models.Model):
    user = models.ForeignKey(User, related_name="tokens")
    name = models.CharField(max_length=60)
    username = models.CharField(max_length=60, null=True)
    token = models.CharField(max_length=255)
    create_date = models.DateTimeField(null=True, blank=True, auto_now=False, auto_now_add=True)
    edit_date = models.DateTimeField(null=True, blank=True, auto_now=True, auto_now_add=False)


#READ MODELS
class ReadType(models.Model):
    read_type = models.CharField(max_length=135, blank=True)
    description = models.CharField(max_length=765, blank=True)
    create_date = models.DateTimeField(null=True, blank=True)
    edit_date = models.DateTimeField(null=True, blank=True)

    def __unicode__(self):
        return self.read_type


class ReadTypeAdmin(admin.ModelAdmin):
    list_display = ('read_type','description','create_date','edit_date')
    display = 'Read Type'


class Read(models.Model):
    FREQUENCY_DISABLED = 'DISABLED'
    FREQUENCY_DAILY = 'daily'
    FREQUENCY_WEEKLY = 'weekly'
    FREQUENCY_CHOICES = (
        (FREQUENCY_DISABLED, 'Disabled'),
        (FREQUENCY_DAILY, 'Daily'),
        (FREQUENCY_WEEKLY, 'Weekly'),
    )

    owner = models.ForeignKey(User)
    type = models.ForeignKey(ReadType)
    read_name = models.CharField(max_length=100, blank=True, default='', verbose_name='source name') #RemoteEndPoint = name
    description = models.TextField(null=True, blank=True)
    read_url = models.CharField(max_length=250, blank=True, default='', verbose_name='source url')
    resource_id = models.CharField(max_length=200, null=True, blank=True)
    gsheet_id = models.CharField(max_length=200, null=True, blank=True) # sheetid within google spreadsheet
    onedrive_file = models.CharField(max_length=200, null=True, blank=True) # File within OneDrive
    username = models.CharField(max_length=20, null=True, blank=True, help_text="Enter username only if the data at this source is protected by a login")
    password = models.CharField(max_length=40, null=True, blank=True, help_text="Enter password only if the data at this source is protected by a login")
    token = models.CharField(max_length=254, null=True, blank=True)
    file_data = models.FileField("Upload CSV File", upload_to='uploads', blank=True, null=True)
    autopull_frequency = models.CharField(max_length=25, choices=FREQUENCY_CHOICES, null=True, blank=True)
    autopush_frequency = models.CharField(max_length=25, choices=FREQUENCY_CHOICES, null=True, blank=True)
    autopull_expiration = models.DateTimeField(null=True, blank=True)
    autopush_expiration = models.DateTimeField(null=True, blank=True)
    create_date = models.DateTimeField(null=True, blank=True, auto_now=False, auto_now_add=True)
    edit_date = models.DateTimeField(null=True, blank=True, auto_now=True, auto_now_add=False)

    tasks = GenericRelation(CeleryTask, related_query_name='reads')

    class Meta:
        ordering = ('create_date',)

    def save(self, *args, **kwargs):
        super(Read, self).save(*args, **kwargs)

    def __unicode__(self):
        return self.read_name


class ReadAdmin(admin.ModelAdmin):
    list_display = ('owner','read_name','read_url','description','create_date')
    display = 'Read Data Feeds'


class Tag(models.Model):
    name = models.CharField(max_length=100)
    owner = models.ForeignKey(User, related_name='tags')
    created = models.DateTimeField(auto_now=False, auto_now_add=True)
    updated = models.DateTimeField(auto_now=True, auto_now_add=False)
    # silos = reverse relation Silo.tags

    def __str__(self):
        return self.name

    def __unicode__(self):
        return self.name


class FormulaColumn(models.Model):
    mapping = models.TextField() #stores a json document for mapping
    operation = models.TextField()
    column_name = models.TextField()


# Create your models here.
class Silo(models.Model):
    owner = models.ForeignKey(User)
    name = models.CharField(max_length=255, blank=False, null=False)
    reads = models.ManyToManyField(Read, related_name='silos')
    tags = models.ManyToManyField(Tag, related_name='silos', blank=True)
    shared = models.ManyToManyField(User, related_name='silos', blank=True)
    share_with_organization = models.BooleanField(default=False)
    description = models.CharField(max_length=255, blank=True, null=True)
    organization = models.ForeignKey(Organization, blank=True, null=True)
    country = models.ForeignKey(Country, blank=True, null=True)
    workflowlevel1 = models.ManyToManyField(WorkflowLevel1, blank=True)
    public = models.BooleanField()
    form_uuid = models.CharField(max_length=255, verbose_name='CustomForm UUID', null=True, blank=True)
    create_date = models.DateTimeField(null=True, blank=True)

    formulacolumns = models.ManyToManyField(FormulaColumn, related_name='silos', blank=True)
    columns = models.TextField(default = "[]") #stores a json string of json objects
    # json objects stores in the format of  {'name' : <col_name>, 'type' : <col_type>}

    hidden_columns = models.TextField(default = "[]") #stores a Json string
    rows_to_hide = models.TextField(default = "[]")
    #Format of hidden rows:
    #   [{"logic":<or, and, defineblank>,
    #   "operation" : <empty, nempty, gt, etc>,
    #   "conditional": [<list of rows to apply condition or the blank character>],
    #   "number" : <number to perform operation>]}]
    #   default blank characters: not exists, ""

    class Meta:
        ordering = ('create_date',)

    def save(self, *args, **kwargs):
        super(Silo, self).save(*args, **kwargs)

    def __unicode__(self):
        return self.name

    @property
    def tag_list(self):
        return ', '.join([x.name for x in self.tags.all()])

    def read_list(self):
        return ', '.join([x.reads.name for x in self.tags.all()])

    @property
    def data_count(self):
        return LabelValueStore.objects(silo_id=self.id).count()


class Dashboard(models.Model):
    table = models.ForeignKey(Silo)
    name = models.CharField(max_length=255)
    map_lat = models.CharField(max_length=100, blank=True, null=True)
    map_long = models.CharField(max_length=100, blank=True, null=True)
    map_zoom = models.CharField(max_length=10, blank=True, null=True)
    column_charts = models.TextField(default="[]")
    owner = models.ForeignKey(User, related_name='dashboard')
    created = models.DateTimeField(auto_now=False, auto_now_add=True)
    updated = models.DateTimeField(auto_now=True, auto_now_add=False)

    def __str__(self):
        return self.name

    def __unicode__(self):
        return self.name


class DeletedSilos(models.Model):
    user = models.ForeignKey(User)
    deleted_time = models.DateTimeField()
    silo_name_id = models.CharField(max_length=255)
    silo_description = models.CharField(max_length=255,blank=True,null=True)


class DeletedSilosAdmin(admin.ModelAdmin):
    list_display = ('user', 'silo_name_id', 'silo_description','deleted_time')
    search_fields = ('user__last_name','user__first_name','silo_name_id')
    display = 'Data Feeds'


class SiloAdmin(admin.ModelAdmin):
    list_display = ('owner', 'name', 'description', 'public','create_date')
    search_fields = ('owner__last_name','owner__first_name','name')
    list_filter = ('owner__last_name','public')
    display = 'Data Feeds'


class PIIColumn(models.Model):
    """
    Personally Identifiable Information Column is a column with data, which
    can be used to personally identify someone.
    """
    owner = models.ForeignKey(User)
    fieldname = models.CharField(blank=True, null=True, max_length=255)
    create_date = models.DateTimeField(auto_now_add=True, editable=False)


class PIIColumnAdmin(admin.ModelAdmin):
    list_display = ('owner', 'fieldname', 'create_date')
    search_fields = ('owner', 'fieldname')
    display = 'PIIF Columns'


class MergedSilosFieldMapping(models.Model):
    MERGE = 'merge'
    APPEND = 'append'
    MERGE_CHOICES = (
        (MERGE, 'Merge'),
        (APPEND, 'Append'),
    )
    from_silo = models.ForeignKey(Silo, related_name='from_mappings')
    to_silo = models.ForeignKey(Silo, related_name='to_mappings')
    merged_silo = models.OneToOneField(Silo, related_name='merged_silo_mappings')
    merge_type = models.CharField(max_length=60, choices=MERGE_CHOICES, null=True, blank=True)
    mapping = models.TextField()
    create_date = models.DateTimeField(auto_now=False, auto_now_add=True)

    def __str__(self):
        return "Table I (%s) and Table II (%s) merged to create Table III (%s)" % (self.from_silo, self.to_silo, self.merged_silo)

    def __unicode__(self):
        return "Table I (%s) and Table II (%s) merged to create Table III (%s)" % (self.from_silo, self.to_silo, self.merged_silo)


class UniqueFields(models.Model):
    name = models.CharField(max_length=254)
    silo = models.ForeignKey(Silo, related_name='unique_fields')
    created = models.DateTimeField(auto_now=False, auto_now_add=True)

    def __str__(self):
        return self.name

    def __unicode__(self):
        return self.name


class LabelValueStore(DynamicDocument):
    silo_id = IntField()
    read_id = IntField(default=-1)
    create_date = DateTimeField(help_text='date created')
    edit_date = DateTimeField(help_text='date editted')
