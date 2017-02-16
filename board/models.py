from __future__ import unicode_literals
import datetime, time, logging
from django.utils import timezone
from django.utils.timezone import utc
from django.utils.encoding import python_2_unicode_compatible
from django.db import models

from django.contrib.auth.models import User
from silo.models import Silo

class CommonBaseAbstractModel(models.Model):
    created = models.DateTimeField(editable=False, blank=True, null=True)
    updated = models.DateTimeField(editable=False, blank=True, null=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        now_utc = datetime.datetime.utcnow().replace(tzinfo=utc)
        if self.id:
            self.updated = now_utc
        else:
            self.created = now_utc
        super(CommonBaseAbstractModel, self).save(*args, **kwargs)

@python_2_unicode_compatible
class Boardsilo(Silo):
    class Meta:
        proxy=True

    def __str__(self):
        return self.name


    class JSONAPIMeta:
        resource_name = 'boardsilos'

@python_2_unicode_compatible
class Owner(User):
    class Meta:
        proxy=True

    def __str__(self):
        return "%s %s" % (self.first_name, self.last_name)

    class JSONAPIMeta:
        resource_name = 'owners'

@python_2_unicode_compatible
class Board(CommonBaseAbstractModel):
    """
    A Board is essentially a canvas that can hold many graphs/maps.
    """
    owner = models.ForeignKey(Owner, related_name='boards')
    title = models.CharField(max_length = 250, blank=False, null=False)

    def __str__(self):
        return '%s' % self.title

    class JSONAPIMeta:
        resource_name = 'boards'

@python_2_unicode_compatible
class Graph(CommonBaseAbstractModel):
    """
    This is metadata about a graph
    """
    label = models.CharField(max_length = 250, null=False, blank=False)
    thumbnail = models.CharField(max_length=250, null=True, blank=True)
    embercomponent = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return '%s' % self.label

    class JSONAPIMeta:
        resource_name = 'graphs'


@python_2_unicode_compatible
class Graphmodel(CommonBaseAbstractModel):
    """
    This defines a graph's model e.g. a bar chart takes two inputs (x and y axis)
    and their types must be numeric and both are required.
    Entries in this table are NOT defined by user. Instead, they are defined when
    adding support for a new visualization
    """
    graph = models.ForeignKey(Graph, related_name='inputs', null=False, blank=False)
    name = models.CharField(max_length=250, blank=False, null=False)
    label = models.CharField(max_length=250, blank=False, null=False)
    isrequired = models.BooleanField(default=False)
    inputtype = models.CharField(max_length=250, blank=False, null=False)

    def __str__(self):
        return '%s-%s' % (self.graph.label, self.name)

    class JSONAPIMeta:
        resource_name = 'graphmodels'


@python_2_unicode_compatible
class Item(CommonBaseAbstractModel):
    """
    Item represents a single visualization on the Board
    """
    board = models.ForeignKey(Board, related_name='items', null=True, blank=True)
    source = models.ForeignKey(Boardsilo, related_name='items', null=True, blank=True)
    title = models.CharField(max_length = 250, blank=False, null=False)
    widgetcol = models.IntegerField(null=False, blank=False)
    widgetrow = models.IntegerField(null=False, blank=False)
    widgetsizex = models.IntegerField(null=False, blank=False)
    widgetsizey = models.IntegerField(null=False, blank=False)
    graph = models.ForeignKey(Graph, related_name='items', blank=True, null=True)

    def __str__(self):
        return '%s' % self.title

    class JSONAPIMeta:
        resource_name = 'items'


@python_2_unicode_compatible
class Graphinput(CommonBaseAbstractModel):
    """
    User defines what colums in the data represent the necessary inputs
    for the chosen graph.
    """
    graphmodel = models.ForeignKey(Graphmodel, related_name='graphinputs', blank=False, null=False)
    graphmodelvalue = models.CharField(max_length=150, blank=False, null=False)
    aggregationfunction = models.CharField(max_length=20, null=True, blank=True)
    item = models.ForeignKey(Item, related_name='graphinputs', blank=False, null=False)

    def __str__(self):
        return '%s - %s' % (self.graph.label, self.graphinput)

    class JSONAPIMeta:
        resource_name = 'graphinputs'
