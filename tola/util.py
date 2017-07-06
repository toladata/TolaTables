import unicodedata
import datetime
import urllib2
import json
import base64
import requests

from django.utils.encoding import smart_text
from django.utils import timezone
from django.utils.encoding import smart_str, smart_unicode
from django.conf import settings
from django.contrib.auth.models import User

from silo.models import Read, Silo, LabelValueStore, TolaUser, Country, ColumnType, ThirdPartyTokens, FormulaColumnMapping, ColumnOrderMapping, siloHideFilter
from django.contrib import messages
import pymongo
from bson.objectid import ObjectId
from pymongo import MongoClient

from os import walk, listdir
from django.apps import apps

from collections import Counter

def mean(lst):
    return float(sum(lst))/len(lst)

def median(lst):
    lst = sorted(lst)
    n = len(lst)
    if n < 1:
            return None
    if n % 2 == 1:
            return lst[n//2]
    else:
            return sum(lst[n//2-1:n//2+1])/2.0

def mode(lst):
    return max(set(lst), key=lst.count)

def parseMathInstruction(operation):
    if operation == "sum":
        return sum
    elif operation == "mean":
        return mean
    elif operation == "median":
       return median
    elif operation == "mode":
       return mode
    elif operation == "max":
       return max
    elif operation == "min":
       return min
    else:
        return (messages.ERROR, "Tried to perform invalid operation: %s" % operation)

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


def saveDataToSilo(silo, data, read = -1, user = None):
    """
    This saves data to the silo

    Keyword arguments:
    silo -- the silo object, which is meta data for its labe_value_store
    data -- a python list of dictionaries. stored in MONGODB
    read -- the read object
    user -- an optional parameter to use if its necessary to retrieve from ThirdPartyTokens
    """
    if read.type.read_type == "ONA" and user:
        saveOnaDataToSilo(silo,data,read,user)


    read_source_id = read.id
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
            lvs.read_id = read_source_id
        except LabelValueStore.DoesNotExist as e:
            lvs = LabelValueStore()
            lvs.silo_id = silo.pk
            lvs.create_date = timezone.now()
            lvs.read_id = read_source_id
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
            setattr(lvs, key.replace(".", "_").replace("$", "USD").replace(u'\u2026', ""), val)
            counter += 1
        formula_columns = FormulaColumnMapping.objects.filter(silo_id=silo.id)
        for column in formula_columns:
            calculation_to_do = parseMathInstruction(column.operation)
            columns_to_calculate_from = json.loads(column.mapping)
            numbers = []
            try:
                for col in columns_to_calculate_from:
                    numbers.append(int(lvs[col]))
                setattr(lvs,column.column_name,calculation_to_do(numbers))
            except ValueError as operation:
                setattr(lvs,column.column_name,calculation_to_do("Error"))
        lvs.save()

    combineColumns(silo.pk)
    res = {"skipped_rows": skipped_rows, "num_rows": counter}
    return res


#IMPORT JSON DATA
def importJSON(read_obj, user, remote_user = None, password = None, silo_id = None, silo_name = None, return_data = False):
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

        #if the caller of this function does not want to the data to go into the silo yet
        if return_data:
            return data

        skipped_rows = saveDataToSilo(silo, data, read_obj)
        return (messages.SUCCESS, "Data imported successfully.", str(silo_id))
    except Exception as e:
        if return_data:
            return None
        return (messages.ERROR, "An error has occured: %s" % e, str(silo_id))

def getSiloColumnNames(id):
    lvs = LabelValueStore.objects.filter(silo_id=id).first()
    cols = []
    try:
        order = ColumnOrderMapping.objects.get(silo_id=id)
        cols.extend(json.loads(order.ordering))
    except ColumnOrderMapping.DoesNotExist as e:
        pass


    try:
        cols.extend([col for col in lvs if col not in cols and col not in {'id','silo_id','read_id','create_date','edit_date','editted_date'}])
    except TypeError as e:
        return []
    try:
        hide_columns =  siloHideFilter.objects.get(silo_id=id)
        hide_columns = set(json.loads(hide_columns.hiddenColumns))
        cols = [col for col in cols if col not in hide_columns]
    except siloHideFilter.DoesNotExist as e:
        pass
    return cols

def user_to_tola(backend, user, response, *args, **kwargs):

    # Add a google auth user to the tola profile
    default_country = Country.objects.first()
    userprofile, created = TolaUser.objects.get_or_create(
        user = user)

    userprofile.country = default_country

    userprofile.name = response.get('displayName')

    userprofile.email = response.get('emails["value"]')

    userprofile.save()


#gets the list of apps to import data
def getImportApps():
    return settings.DATASOURCE_APPS

#gets the list of apps to import data by their verbose name
def getImportAppsVerbose():
    folders = getImportApps()
    apps = [[folder,folder] for folder in folders]
    for app in apps:
        filepath = settings.SITE_ROOT + "/datasources/" + app[0] + "/apps.py"
        f = open(filepath,"r")
        for i, line in enumerate(f):
            if i > 100:
                break
            if 'verbose_name' in line:
                word = line.split('\'')[1::2]
                app[1] = word[0]
                break
    return apps

def ona_parse_type_group(data, form_data, parent_name, silo, read):
    """
    if data is a type group this replaces the compound key names with their labels

    Keyword arguments:
    data -- ona data that needs changing
    form_data -- the children of an ONA object of type group
    parent_name -- the name of the parent of the ona object
    """
    for field in form_data:


        if field["type"] == "group":
            ona_parse_type_group(data,field['children'],parent_name + field['name']+"/",silo,read)
        else:
            for entry in data:
                if field['type'] == "repeat":
                    ona_parse_type_repeat(entry[parent_name + field['name']],\
                                        field['children'],\
                                        parent_name + field['name']+"/",silo,read)
                if 'label' in field:
                    try:
                        entry[field['label']] = entry.pop(parent_name + field['name'])
                    except KeyError as e:
                        pass

        #add an asociation between a column, label and its type to the columnType database
        name = ""
        if 'label' in field:
            name = field['label']
        else:
            name = field['name']

        try:
            ct = ColumnType.objects.get(silo_id=silo.pk,\
                                        read_id=read.pk,\
                                        column_name=name,\
                                        column_source_name=field['name'],\
                                        column_type=field['type'])
            setattr(ct, "edit_date", timezone.now())
        except ColumnType.DoesNotExist as e:
            ct = ColumnType(silo_id=silo.pk,\
                            read_id=read.pk,\
                            create_date=timezone.now(),\
                            column_name=name,\
                            column_source_name=field['name'],\
                            column_type=field['type'])
            ct.save()
        except ColumnType.MultipleObjectsReturned as e:
            continue

def ona_parse_type_repeat(data, form_data, parent_name, silo, read):
    """
    if data is of type repeat this replaces the compound key names apropriate column headers
    This function in finding apropriate column headers also clears out any "${}" type objects

    Keyword arguments:
    data -- the subset of ona data that needs changing
    form_data -- the children of an ONA object of type repeat
    parent_name -- the name of the parent of the ona object
    """
    for field in form_data:
        if field["type"] == "group":
            ona_parse_type_group(data,field['children'],parent_name + field['name']+"/",silo,read)
        else:
            for entry in data:
                if field['type'] == "repeat":
                    ona_parse_type_repeat(entry[parent_name + field['name']],\
                                        field['children'],\
                                        parent_name + field['name']+"/",silo,read)
                if 'label' in field:
                    entry[field['label']] = entry.pop(parent_name + field['name'])

def saveOnaDataToSilo(silo, data, read, user):
    """
    This saves data to the silo specifically for ONA.
    ONA column type and label comes separetely so this function provides the medium layer for integration
    This function also stores an association between a column name and a column type in the columnType database

    Keyword arguments:
    silo -- the silo object, which is meta data for its labe_value_store
    data -- a python list of dictionaries. stored in MONGODB
    form_metadata -- a python dictionary from ONA storing column names labels and types
    read -- a read object
    """
    #If in the future the ONA data needs to be adjusted to remove undesirable fields it can be done here
    ona_token = ThirdPartyTokens.objects.get(user=user, name="ONA")
    url = "https://api.ona.io/api/v1/forms/"+ read.read_url.split('/')[6] +"/form.json"
    response = requests.get(url, headers={'Authorization': 'Token %s' % ona_token.token})
    form_metadata = json.loads(response.content)


    #if this is true than the data isn't a form so proceed to saveDataToSilo normally
    if "detail" in form_metadata:
        return
    else:
        ona_parse_type_group(data,form_metadata['children'],"",silo,read)
        return

def calculateFormulaColumn(lvs,operation,columns,formula_column_name):
    """
    This function calculates the math operation for a queryset of label_value_store using defined
    columns


    lvs -- a queryset of label_value_store objects
    operation -- the math operation to perform
    columns -- a list of columns to use in the math operation
    formula_column_name -- name of the column that holds the math done
    """

    if not columns or len(columns) == 0:
        return (messages.ERROR, "No columns were selected for operation")

    calc = parseMathInstruction(operation)
    if type(calc) == tuple:
        return calc

    calc_fails = []
    for i, entry in enumerate(lvs):
        try:
            values_to_calc = []
            for col in columns:
                values_to_calc.append(int(entry[col]))
            calculation = calc(values_to_calc)
            setattr(entry,formula_column_name,calculation)
            entry.edit_date = timezone.now()
            entry.save()
        except ValueError as operation:
            setattr(entry,formula_column_name,"Error")
            entry.edit_date = timezone.now()
            entry.save()
            calc_fails.append(i)
    if len(calc_fails) == 0:
        return (messages.SUCCESS, "Successfully performed operations")
    return (messages.WARNING, "Non-numberic data detected in rows %s" % str(calc_fails))

def makeQueryForHiddenRow(row_filter):
    """
    This function takes a JSON object in the format generated from when a row filter is added and
    returns a JSON formatted query to be able to plugged into the json format
    """
    query = {}
    empty = [""]
    #find and add any extra empty characters
    for condition in row_filter:
        if condition.get("logic","") == "BLANKCHAR":
            empty.append(condition.get("conditional", ""))
    #now add to the query
    for condition in row_filter:
        #this does string comparisons
        num_to_compare = condition.get("number","")
        #specify the part of the dictionary to add to
        if condition.get("logic","") == "AND":
            to_add = query
        elif condition.get("logic","") == "OR":
            try:
                to_add = query["$or"]
            except KeyError as e:
                query["$or"] = {}
                to_add = query["$or"]
        for column in condition.get("conditional",[]):
            print condition.get("operation")
            if condition.get("operation","") == "empty":
                try:
                    to_add[column]["$not"]["$exists"] = "true"
                except KeyError as e:
                    to_add[column] = {}
                    try:
                        to_add[column]["$not"]["$exists"] = "true"
                    except KeyError as e:
                        to_add[column]["$not"] = {}
                        to_add[column]["$not"]["$exists"] = "true"
                try:
                    to_add[column]["$not"]["$not"]["$in"] = empty
                except KeyError as e:
                    to_add[column]["$not"]["$not"] = {}
                    to_add[column]["$not"]["$not"]["$in"] = empty
            elif condition.get("operation","") == "nempty":
                try:
                    to_add[column]["$exists"] = "true"
                except KeyError as e:
                    to_add[column] = {}
                    to_add[column]["$exists"] = "true"
                try:
                    to_add[column]["$not"]["$in"] = empty
                except KeyError as e:
                    to_add[column]["$not"] = {}
                    to_add[column]["$not"]["$in"] = empty
            elif condition.get("operation","") in {"gt", "lt", "gte", "lte", "eq"}:
                try:
                    to_add[column]['$' + condition.get("operation")] = num_to_compare
                except KeyError as e:
                    to_add[column] = {}
                    to_add[column]['$' + condition.get("operation")] = num_to_compare
            elif condition.get("operation","") == "neq":
                try:
                    to_add[column]['$ne'] = num_to_compare
                except KeyError as e:
                    to_add[column] = {}
                    to_add[column]['$ne'] = num_to_compare

    #conver the $or area to be properly formatted for a query
    or_items = query.get("$or", {})
    if len(or_items) > 0:
        query["$or"] = []
        for k, v in or_items.iteritems():
            query["$or"].append({k:v})

    query = json.dumps(query)
    return query

def getNewestDataDate(silo_id):
    """
    finds the newest date of data in a silo
    """
    db = MongoClient(settings.MONGODB_HOST).tola
    newest_record = db.label_value_store.find({'silo_id' : silo_id}).sort([("create_date", -1)]).limit(1)

    return newest_record[0]['create_date']
