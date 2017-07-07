
from silo.models import Read, ReadType
from django.contrib import messages

import json

from celery import group

from .tasks import fetchCommCareData, requestCommCareData, storeCommCareData, addExtraFields

from silo.models import LabelValueStore, ColumnOrderMapping, siloHideFilter
from tola.util import saveDataToSilo
from pymongo import MongoClient
from django.conf import settings


#this gets a list of projects that users have used in the past to import data from commcare
#used in commcare/forms.py
def getProjects():
    reads = Read.objects.filter(type__read_type='CommCare')
    projects = []
    for read in reads:
        projects.append(read.read_url.split('/')[4])
    return list(set(projects))

def useHeaderName(columns, data):
    """
    since the commcare dictionary does not use the proper column names and instead uses column
    idnetifiers this funciton changes the dictionary to use the proper column names
    used in commcoare/views.py for saveCommCareData
    """
    for row in data:
        for column in columns:
            row[column['header']] = row.remove(column['slug'])

def getCommCareCaseData(domain, auth, auth_header, total_cases, silo, read):
    """
    Use fetch and request CommCareData to store all of the case data

    domain -- the domain name used for a commcare project
    auth -- the authorization required
    auth_header -- True = use Header, False = use Digest authorization
    total_cases -- total cases to get
    silo - silo to put the data into
    read -- read that the data is apart of
    """


    RECORDS_PER_REQUEST = 100
    base_url = "https://www.commcarehq.org/a/"+ domain\
                +"/api/v0.5/case/?format=JSON&limit="+str(RECORDS_PER_REQUEST)

    data_raw = fetchCommCareData(base_url, auth, auth_header,\
                    0, total_cases, RECORDS_PER_REQUEST, silo.id, read.id)
    data_collects = data_raw.apply_async()
    data_retrieval = [v.get() for v in data_collects]
    columns = set()
    for data in data_retrieval:
        columns = columns.union(data)
    #correct the columns
    try: columns.remove("")
    except KeyError as e: pass
    try: columns.remove("silo_id")
    except KeyError as e: pass
    try: columns.remove("read_id")
    except KeyError as e: pass
    for column in columns:
        if "." in column:
            columns.remove(column)
            columns.add(column.replace(".", "_"))
        if "$" in column:
            columns.remove(column)
            columns.add(column.replace("$", "USD"))
    try:
        columns.remove("id")
        columns.add("user_assigned_id")
    except KeyError as e: pass
    try:
        columns.remove("_id")
        columns.add("user_assigned_id")
    except KeyError as e: pass
    try:
        columns.remove("edit_date")
        columns.add("editted_date")
    except KeyError as e: pass
    try:
        columns.remove("create_date")
        columns.add("created_date")
    except KeyError as e: pass
    #now mass update all the data in the database

    addExtraFields.delay(list(columns), silo.id)
    try:
        column_order_mapping = ColumnOrderMapping.objects.get(silo_id=silo.id)
        columns = columns.union(json.loads(column_order_mapping.ordering))
        column_order_mapping.ordering = json.dumps(list(columns))
        column_order_mapping.save()
    except ColumnOrderMapping.DoesNotExist as e:
        ColumnOrderMapping.objects.create(silo_id=silo.id,ordering = json.dumps(list(columns)))
    try:
        silo_hide_filter = siloHideFilter.objects.get(silo_id=silo.id)
        hidden_cols = set(json.loads(silo_hide_filter.hiddenColumns))
        hidden_cols = hidden_cols.add("case_id")
        silo_hide_filter.hiddenColumns = json.dumps(list(hidden_cols))
        siloHideFilter.save()
    except siloHideFilter.DoesNotExist as e:
        siloHideFilter.objects.create(silo_id=silo.id, hiddenColumns=json.dumps(["case_id"]), hiddenRows="[]")


    return (messages.SUCCESS, "CommCare cases imported successfully", columns)
