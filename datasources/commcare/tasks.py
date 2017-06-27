# Create your tasks here
from __future__ import absolute_import, unicode_literals
from celery import shared_task, group, chain
from django.utils import timezone

from requests.auth import HTTPDigestAuth

from django.conf import settings
from pymongo import MongoClient

import requests
import json
import time

@shared_task(trail=True)
def fetchCommCareData(url, auth, auth_header, start, end, step) :
    """
    This function will call the appointed functions to retrieve the commcare data

    url -- the base url
    auth -- the authorization required
    auth_header -- True = use Header, False = use Digest authorization
    start -- What record to start at
    end -- what record to end at
    step -- # of records to get in one request
    """
    return group(chain(requestCommCareData.s(url, offset, auth, auth_header), \
            parseCommCareData.s()) \
            for offset in xrange(start,end,step))

@shared_task(trail=True)
def requestCommCareData(url, offset, auth, auth_header):
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
        return requestCommCareData(url, offset, auth, auth_header)
    else:
        #add something to this future error code stopping everything with throw exception
        time.sleep(1)
        return requestCommCareData(url, offset, auth, auth_header)

    #now get the properties of each data
    return data['objects']



@shared_task()
def parseCommCareData(data):
    data_properties = []
    data_columns = set()
    for entry in data:
        data_properties.append(entry['properties'])
        data_columns.update(entry['properties'].keys())
    return (list(data_columns), data_properties)

@shared_task()
def storeCommCareData(data, columns_set, silo_id, read_id):

    data_refined = []
    for row in data:
        try: row.pop("")
        except KeyError as e: pass
        try: row.pop("silo_id")
        except KeyError as e: pass
        try: row.pop("read_id")
        except KeyError as e: pass
        columns_data = {
            "silo_id" : silo_id,
            "read_id" : read_id,
            "create_date" : timezone.now()
        }
        for column in columns_set:
            try:
                columns_data[column.replace(".", "_").replace("$", "USD")] = \
                            row[column.replace(".", "_").replace("$", "USD")]
            except KeyError as e:
                columns_data[column.replace(".", "_").replace("$", "USD")] = ""
        try: columns_data["user_assigned_id"] = columns_data.pop("id")
        except KeyError as e: pass
        try: columns_data["user_assigned_id"] = columns_data.pop("_id")
        except KeyError as e: pass
        try: columns_data["editted_date"] = columns_data.pop("edit_date")
        except KeyError as e: pass
        try: columns_data["created_date"] = columns_data.pop("create_date")
        except KeyError as e: pass
        data_refined.append(columns_data)
    db = MongoClient(settings.MONGODB_HOST).tola
    db.label_value_store.insert(data_refined)
