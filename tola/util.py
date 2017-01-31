import unicodedata
import datetime
import urllib2
import json
import base64
from django.utils.encoding import smart_text
from django.utils import timezone
from django.utils.encoding import smart_str, smart_unicode
from django.conf import settings
from django.contrib.auth.models import User

from silo.models import Read, Silo, LabelValueStore, TolaUser, Country
from django.contrib import messages
import pymongo
from bson.objectid import ObjectId
from pymongo import MongoClient

def combineColumns(silo_id):
    client = MongoClient(settings.MONGODB_HOST)
    db = client.tola
    lvs = json.loads(LabelValueStore.objects(silo_id = silo_id).to_json())
    cols = []
    for l in lvs:
        cols.extend([k for k in l.keys() if k not in cols])

    for l in lvs:
        for c in cols:
            if c not in l.keys():
                db.label_value_store.update_one(
                    {"_id": ObjectId(l['_id']['$oid'])},
                    {"$set": {c: ''}},
                    False
                )
    return True

#CREATE NEW DATA DICTIONARY OBJECT
def siloToDict(silo):
    parsed_data = {}
    key_value = 1
    for d in silo:
        label = unicodedata.normalize('NFKD', d.field.name).encode('ascii','ignore')
        value = unicodedata.normalize('NFKD', d.char_store).encode('ascii','ignore')
        row = unicodedata.normalize('NFKD', d.row_number).encode('ascii','ignore')
        parsed_data[key_value] = {label : value}

        key_value += 1

    return parsed_data


def saveDataToSilo(silo, data):
    """
    This saves data to the silo

    Keyword arguments:
    silo -- the silo object, which is meta data for its labe_value_store
    data -- a python list of dictionaries. stored in MONGODB
    """
    unique_fields = silo.unique_fields.all()
    skipped_rows = set()
    enc = "latin-1"
    for counter, row in enumerate(data):
        # reseting filter_criteria for each row
        filter_criteria = {}
        for uf in unique_fields:
            try:
                filter_criteria.update({str(uf.name): str(row[uf.name])})
            except KeyError:
                # when this excpetion occurs, it means that the col identified
                # as the unique_col is not present in the fetched dataset
                pass

        # if filter_criteria is set, then update it with current silo_id
        # else set filter_criteria to some non-existent key and value so
        # that it triggers a DoesNotExist exception in order to create a new
        # document instead of updating an existing one.
        if filter_criteria:
            filter_criteria.update({'silo_id': silo.id})
        else:
            filter_criteria.update({"nonexistentkey":"NEVER0101010101010NEVER"})

        try:
            lvs = LabelValueStore.objects.get(**filter_criteria)
            #print("updating")
            setattr(lvs, "edit_date", timezone.now())
        except LabelValueStore.DoesNotExist as e:
            lvs = LabelValueStore()
            lvs.silo_id = silo.pk
            lvs.create_date = timezone.now()
            #print("creating")
        except LabelValueStore.MultipleObjectsReturned as e:
            for k,v in filter_criteria.iteritems():
                skipped_rows.add("%s=%s" % (k,v))
            #print("skipping")
            continue

        counter = 0
        # set the fields in the curernt document and save it
        for key, val in row.iteritems():
            if key == "" or key is None or key == "silo_id": continue
            elif key == "id" or key == "_id": key = "user_assigned_id"
            elif key == "edit_date": key = "editted_date"
            elif key == "create_date": key = "created_date"
            if type(val) == str or type(val) == unicode:
                val = smart_str(val, strings_only=True)
            setattr(lvs, key.replace(".", "_").replace("$", "USD"), val)
            counter += 1
        lvs.save()

    combineColumns(silo.pk)
    res = {"skipped_rows": skipped_rows, "num_rows": counter}
    return res


#IMPORT JSON DATA
def importJSON(read_obj, user, remote_user = None, password = None, silo_id = None, silo_name = None):
    # set date time stamp
    today = datetime.date.today()
    today.strftime('%Y-%m-%d')
    today = str(today)
    try:
        request2 = urllib2.Request(read_obj.read_url)
        # If the read_obj has token then use it; otherwise, check for login info.
        if read_obj.token:
            request2.add_header("Authorization", "Basic %s" % read_obj.token)
        elif remote_user and password:
            base64string = base64.encodestring('%s:%s' % (remote_user, password))[:-1]
            request2.add_header("Authorization", "Basic %s" % base64string)
        else:
            pass
        #retrieve JSON data from formhub via auth info
        json_file = urllib2.urlopen(request2)
        silo = None

        if silo_name:
            silo = Silo(name=silo_name, owner=user, public=False, create_date=today)
            silo.save()
        else:
            silo = Silo.objects.get(id = silo_id)

        silo.reads.add(read_obj)
        silo_id = silo.id

        #create object from JSON String
        data = json.load(json_file)
        json_file.close()

        skipped_rows = saveDataToSilo(silo, data)
        return (messages.SUCCESS, "Data imported successfully.", str(silo_id))
    except Exception as e:
        return (messages.ERROR, "An error has occured: %s" % e, str(silo_id))

def getSiloColumnNames(id):
    lvs = LabelValueStore.objects(silo_id=id).to_json()
    data = {}
    jsonlvs = json.loads(lvs)
    for item in jsonlvs:
        for k, v in item.iteritems():
            #print("The key and value are ({}) = ({})".format(k, v))
            if k == "_id" or k == "edit_date" or k == "create_date" or k == "silo_id":
                continue
            else:
                data[k] = v
    return data

def user_to_tola(backend, user, response, *args, **kwargs):

    # Add a google auth user to the tola profile
    default_country = Country.objects.first()
    userprofile, created = TolaUser.objects.get_or_create(
        user = user)

    userprofile.country = default_country

    userprofile.name = response.get('displayName')

    userprofile.email = response.get('emails["value"]')

    userprofile.save()