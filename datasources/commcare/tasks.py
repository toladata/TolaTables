# Create your tasks here
from __future__ import absolute_import, unicode_literals
from celery import shared_task, group, chain
from django.utils import timezone

from requests.auth import HTTPDigestAuth

from django.conf import settings
from pymongo import MongoClient
from pymongo.operations import UpdateMany


import requests
import json
import time

@shared_task(trail=True)
def fetchCommCareData(url, auth, auth_header, start, end, step, silo_id, read_id) :
    """
    This function will call the appointed functions to retrieve the commcare data

    url -- the base url
    auth -- the authorization required
    auth_header -- True = use Header, False = use Digest authorization
    start -- What record to start at
    end -- what record to end at
    step -- # of records to get in one request
    """
    return group(requestCommCareData.s(url, offset, auth, auth_header, silo_id, read_id) \
            for offset in xrange(start,end,step))

@shared_task(trail=True)
def requestCommCareData(url, offset, auth, auth_header, silo_id, read_id):
    """
    This function will retrieve the appointed page of commcare data and return the data in an array

    url -- the base url
    offset -- to get the records starting at n
    auth -- the authorization required
    auth_header -- True = use Header, False = use Digest authorization
    """
    url = url + "&offset=" + str(offset)
    if auth_header:
        response = requests.get(url, headers=auth)
    else:
        response = requests.get(url, auth=HTTPDigestAuth(auth['u'],auth['p']))
    if response.status_code == 200:
        data = json.loads(response.content)
    elif response.status_code == 429:
        time.sleep(1)
        return requestCommCareData(url, offset, auth, auth_header, silo_id, read_id)
    else:
        #add something to this future error code stopping everything with throw exception
        time.sleep(1)
        return requestCommCareData(url, offset, auth, auth_header, silo_id, read_id)

    #now get the properties of each data
    return parseCommCareData(data['objects'], silo_id, read_id)



@shared_task()
def parseCommCareData(data, silo_id, read_id):
    data_properties = []
    data_columns = set()
    for entry in data:
        data_properties.append(entry['properties'])
        data_columns.update(entry['properties'].keys())
    storeCommCareData(data_properties, silo_id, read_id)
    return list(data_columns)

@shared_task()
def storeCommCareData(data, silo_id, read_id):

    data_refined = []
    for row in data:
        try: row.pop("")
        except KeyError as e: pass
        try: row.pop("silo_id")
        except KeyError as e: pass
        try: row.pop("read_id")
        except KeyError as e: pass
        for column in row:
            if "." in column:
                row[column.replace(".", "_").replace("$", "USD")] = row.pop(column)
            if "$" in column:
                row[column.replace("$", "USD")] = row.pop(column)
        try: row["user_assigned_id"] = row.pop("id")
        except KeyError as e: pass
        try: row["user_assigned_id"] = row.pop("_id")
        except KeyError as e: pass
        try: row["editted_date"] = row.pop("edit_date")
        except KeyError as e: pass
        try: row["created_date"] = row.pop("create_date")
        except KeyError as e: pass
        row["silo_id"] = silo_id
        row["read_id"] = read_id
        row["create_date"] = timezone.now()

        data_refined.append(row)
    db = MongoClient(settings.MONGODB_HOST).tola
    db.label_value_store.insert(data_refined)

@shared_task()
def addExtraFields(columns, silo_id):
    db = MongoClient(settings.MONGODB_HOST).tola
    mongo_request = []
    db.label_value_store.create_index('silo_id')
    for column in columns:
        db.label_value_store.create_index('column')
        mongo_request.append(UpdateMany(
            {
                "silo_id" : silo_id,
                column : {"$not" : {"$exists" : "true"}}\
            }, #filter
            {"$set" : {column : ""}} #update
        ))
    db.label_value_store.bulk_write(mongo_request)
