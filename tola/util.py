import urllib2
import json
import base64
import requests
import cgi
from collections import OrderedDict
from bson import ObjectId
import logging
from django.utils import timezone
from django.conf import settings

from silo.models import Silo, LabelValueStore, ThirdPartyTokens
from django.contrib import messages
from pymongo import MongoClient

from collections import deque


logger = logging.getLogger("tola")


class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return {u'$oid': str(o)}
        return json.JSONEncoder.default(self, o)


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
        raise TypeError(operation)


def save_data_to_silo(silo, data, read=-1, user=None):
    """
    This saves data to the silo

    Keyword arguments:
    silo -- the silo object, which is meta data for its labe_value_store
    data -- a python list of dictionaries. stored in MONGODB
    read -- the read object, optional only for backwards compatability
    user -- an optional parameter to use if its necessary to retrieve
            from ThirdPartyTokens
    """
    try:
        if read.type.read_type == "ONA" and user:
            saveOnaDataToSilo(silo, data, read, user)
        read_source_id = read.id
    except AttributeError:
        read_source_id = read
    unique_fields = silo.unique_fields.all()
    skipped_rows = set()
    counter = 0
    keys = []
    try:
        keys = data.fieldnames
        keys = [cleanKey(key) for key in keys]
    except AttributeError as e:
        logger.warning(e)

    for counter, row in enumerate(data):
        # resetting filter_criteria for each row
        filter_criteria = {}
        for uf in unique_fields:
            try:
                filter_criteria.update({str(uf.name): str(row[uf.name])})
            except KeyError as e:
                # when this excpetion occurs, it means that the col identified
                # as the unique_col is not present in the fetched dataset
                logger.info(e)

        # if filter_criteria is set, then update it with current silo_id
        # else set filter_criteria to some non-existent key and value so
        # that it triggers a DoesNotExist exception in order to create a new
        # document instead of updating an existing one.
        if filter_criteria:
            filter_criteria.update({'silo_id': silo.id})

            try:
                lvs = LabelValueStore.objects.get(**filter_criteria)
                setattr(lvs, "edit_date", timezone.now())
                lvs.read_id = read_source_id
            except LabelValueStore.DoesNotExist:
                lvs = LabelValueStore()
                lvs.silo_id = silo.pk
                lvs.create_date = timezone.now()
                lvs.read_id = read_source_id
            except LabelValueStore.MultipleObjectsReturned:
                for k, v in filter_criteria.iteritems():
                    skipped_rows.add("{}={}".format(str(k), str(v)))
                continue
        else:
            lvs = LabelValueStore()

            lvs.silo_id = silo.pk
            lvs.create_date = timezone.now()
            lvs.read_id = read_source_id

        row = clean_data_obj(row)

        for key, val in row.iteritems():
            if not isinstance(key, tuple):
                if key not in keys:
                    keys.append(key)
                setattr(lvs, key, val)

        counter += 1
        lvs = calculateFormulaCell(lvs, silo)
        lvs.save()

    addColsToSilo(silo, keys)
    res = {"skipped_rows": skipped_rows, "num_rows": counter}
    return res


def clean_data_obj(obj):
    """
    Clean the data object given in the call. It casts the values to the right
    type to be stored in the database.
    :param obj: dict | list | string
    :return: dict
    """
    if not isinstance(obj, (dict, list, OrderedDict)):

        try:
            obj = json.loads(obj)
        except (ValueError, TypeError):
            if isinstance(obj, str) or isinstance(obj, unicode):
                obj = cgi.escape(obj)
        return obj

    if isinstance(obj, list):
        return [clean_data_obj(v) for v in obj]

    return {cleanKey(k): clean_data_obj(v) for k, v in obj.items()}


def cleanKey(key):
    if key == "" or key is None or key == "silo_id":
        return key
    elif key == "id" or key == "_id":
        key = "user_assigned_id"
    elif key == "edit_date":
        key = "editted_date"
    elif key == "create_date":
        key = "created_date"
    key = ' '.join(key.split())
    key = key.replace(".", "_").replace("$", "USD")
    try:
        key = key.replace(u'\u2026', "")
    except UnicodeDecodeError:
        key = key.decode('utf8').replace(u'\u2026', "").encode('utf8')

    # Mongoengine doesn't seem to be able to save keys with leading underscores
    # The underscore in sys_ makes collisions with user defined headers
    # less likely
    if key.startswith('_'):
        key = 'sys_'+key

    return key


# IMPORT JSON DATA
def importJSON(read_obj, user, remote_user=None, password=None, silo_id=None,
               silo_name=None, return_data=False):
    try:
        request2 = urllib2.Request(read_obj.read_url)
        # If the read_obj has token then use it; otherwise, check login info
        if read_obj.token:
            request2.add_header("Authorization", "Basic %s" % read_obj.token)
        elif remote_user and password:
            base64string = base64.encodestring('{0}:{1}'.format(remote_user,
                                                                password))[:-1]
            request2.add_header("Authorization", "Basic %s" % base64string)
        else:
            pass
        # retrieve JSON data from formhub via auth info
        json_file = urllib2.urlopen(request2)

        if silo_name:
            silo = Silo(name=silo_name, owner=user, public=False,
                        create_date=timezone.now())
            silo.save()
        else:
            silo = Silo.objects.get(id=silo_id)

        silo.reads.add(read_obj)
        silo_id = silo.id

        # create object from JSON String
        data = json.load(json_file)
        json_file.close()

        # if the caller of this function does not want to the data to go into
        #  the silo yet
        if return_data:
            return data

        save_data_to_silo(silo, data, read_obj)
        return messages.SUCCESS, "Data imported successfully.", str(silo_id)
    except Exception as e:
        if return_data:
            return None
        return messages.ERROR, "An error has occured: %s" % e, str(silo_id)


def getSiloColumnNames(id):
    """
    takes silo_id and returns the shown columns in order in O(n)
    """
    silo = Silo.objects.get(pk=id)
    cols_raw = json.loads(silo.columns)
    hidden_cols = set(json.loads(silo.hidden_columns))
    hidden_cols = hidden_cols.union(['id', 'silo_id', 'read_id', 'create_date',
                                     'edit_date', 'editted_date'])

    cols_final = deque()
    for col in cols_raw:
        col_name = col if isinstance(col, basestring) else col.get('name')

        if col_name not in hidden_cols:
            cols_final.append(col_name)

    return list(cols_final)


def getCompleteSiloColumnNames(id):
    """
    This gets all the column names including the hidden ones in order

    id -- silo_id
    """
    silo = Silo.objects.get(pk=id)
    return [x if isinstance(x, basestring) else x.get('name')
            for x in json.loads(silo.columns)]


def addColsToSilo(silo, columns, col_types={}):
    """
    This adds columns to a silo object while preserving order in O(n)

    silo -- a silo object
    columns -- an iterable containing columns to add
    """
    # make sure there are no duplicate columns
    columns_set = set(columns)
    if len(columns_set) != len(columns):
        raise ValueError('Duplicate columns are not allowed')
    silo_cols = json.loads(silo.columns)
    # this is done to decrease lookup time from n to 1
    silo_cols_set = set([x['name'] for x in silo_cols])
    silo_cols.extend([{'name': x, 'type': col_types.get(x, 'string')}
                      for x in columns if x not in silo_cols_set])
    silo.columns = json.dumps(silo_cols)
    silo.save()


def deleteSiloColumns(silo, columns):
    """
    delete a list of columns from a silos column list in O(n)
    """
    cols_old = json.loads(silo.columns)
    columns = set(columns)

    cols_final = deque()
    for col in cols_old:
        if col['name'] not in columns:
            cols_final.append(col)

    silo.columns = json.dumps(list(cols_final))
    unhideSiloColumns(silo, columns)
    silo.save()


def hideSiloColumns(silo, cols):
    """
    take a list of columns and add it to be hidden
    """
    hidden_cols = set(json.loads(silo.hidden_columns))
    hidden_cols = hidden_cols.union(cols)
    silo.hidden_columns = json.dumps(list(hidden_cols))
    silo.save()


def unhideSiloColumns(silo, cols):
    """
    take a list of columns and unhides it
    """
    hidden_cols = set(json.loads(silo.hidden_columns))
    hidden_cols = hidden_cols.difference(cols)
    silo.hidden_columns = json.dumps(list(hidden_cols))
    silo.save()


def getColToTypeDict(silo):
    """
    Returns key value pairs of the name of a column to its type in O(n)
    """
    columns = json.loads(silo.columns)
    if len(columns) > 0 and not isinstance(columns[0], basestring):
        column_types = {x['name']: x['type'] for x in columns}
    else:
        column_types = {x: 'string' for x in columns}
    return column_types


# gets the list of apps to import data
def getImportApps():
    return settings.DATASOURCE_APPS


# gets the list of apps to import data by their verbose name
def getImportAppsVerbose():
    folders = getImportApps()
    apps = [[folder, folder] for folder in folders]
    for app in apps:
        filepath = settings.SITE_ROOT + "/datasources/" + app[0] + "/apps.py"
        f = open(filepath, "r")
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
    if data is a type group this replaces the compound key names with their
    labels

    Keyword arguments:
    data -- ona data that needs changing
    form_data -- the children of an ONA object of type group
    parent_name -- the name of the parent of the ona object
    """

    for field in form_data:
        entry_name = parent_name + field['name']
        if field["type"] == "group":
            ona_parse_type_group(data, field['children'], entry_name + "/",
                                 silo, read)
        else:
            warnings = set()
            for entry in data:
                if field['type'] == "repeat":
                    ona_parse_type_repeat(entry.get(entry_name, []),
                                          field['children'], entry_name + "/",
                                          silo, read)
                if 'label' in field:
                    try:
                        entry[field['label']] = entry.pop(entry_name)
                    except KeyError as e:
                        warnings.add("Keyerror for silo %s, %s" % (silo.pk, e))
                    except TypeError:
                        pass
            for warn in warnings:
                logger.warning(warn)


def ona_parse_type_repeat(data, form_data, parent_name, silo, read):
    """
    if data is of type repeat this replaces the compound key names apropriate
    column headers. This function in finding apropriate column headers also
    clears out any "${}" type objects

    Keyword arguments:
    data -- the subset of ona data that needs changing
    form_data -- the children of an ONA object of type repeat
    parent_name -- the name of the parent of the ona object
    """
    warnings = set()
    for field in form_data:
        entry_name = parent_name + field['name']
        if field["type"] == "group":
            ona_parse_type_group(data, field['children'], entry_name + "/",
                                 silo, read)
        else:
            for entry in data:
                if field['type'] == "repeat":
                    ona_parse_type_repeat(entry.get(entry_name, []),
                                          field['children'], entry_name + "/",
                                          silo, read)
                if 'label' in field:
                    try:
                        entry[field['label']] = entry.pop(entry_name)
                    except KeyError as e:
                        warnings.add("Warn: ona_parse_type_repeat for silo {0}"
                                     ", {1}".format(silo.pk, e))
    for warn in warnings:
        logger.warning(warn)


def saveOnaDataToSilo(silo, data, read, user):
    """
    This saves data to the silo specifically for ONA.
    ONA column type and label comes separetely so this function provides
    the medium layer for integration.
    This function also stores an association between a column name and a
    column type in the columnType database

    Keyword arguments:
    silo -- the silo object, which is meta data for its labe_value_store
    data -- a python list of dictionaries. stored in MONGODB
    form_metadata -- a python dictionary from ONA storing column names
    labels and types
    read -- a read object
    """
    # If in the future the ONA data needs to be adjusted to remove
    # undesirable fields it can be done here
    ona_token = ThirdPartyTokens.objects.get(user=user, name="ONA")
    url = "https://api.ona.io/api/v1/forms/{}/form.json".format(
        read.read_url.split('/')[6])
    response = requests.get(url, headers={'Authorization': 'Token {}'.format(
        ona_token.token)})
    form_metadata = json.loads(response.content)

    # if this is true than the data isn't a form so proceed to
    # save_data_to_silo normally
    if "detail" in form_metadata:
        return
    else:
        ona_parse_type_group(data, form_metadata['children'], "", silo, read)
        return


def calculateFormulaColumn(lvs, operation, columns, formula_column_name):
    """
    This function calculates the math operation for a queryset of
    abel_value_store using defined columns

    lvs -- a queryset of label_value_store objects
    operation -- the math operation to perform
    columns -- a list of columns to use in the math operation
    formula_column_name -- name of the column that holds the math done
    """

    if not columns or len(columns) == 0:
        return messages.ERROR, "No columns were selected for operation"

    calc = parseMathInstruction(operation)
    if type(calc) == tuple:
        return calc

    calc_fails = []
    for i, entry in enumerate(lvs):
        entry = calculateFormula(entry, calc, columns, formula_column_name)
        if entry[1]:
            entry[0].save()
        else:
            entry[0].save()
            calc_fails.append(i)
    if len(calc_fails) == 0:
        return messages.SUCCESS, "Successfully performed operations"
    return messages.WARNING, "Non-numeric data detected in rows {}".format(
        calc_fails)


def calculateFormula(entry, calc, columns, formula_column_name):
    """
    This function calculates a math operation for a single query

    entry -- a query of label_value_store objects
    calc -- a function pointer to the math operation to perform
    columns -- a list of columns to use in the math operation
    formula_column_name -- name of the column that holds the math done
    """
    try:
        values_to_calc = []
        for col in columns:
            values_to_calc.append(float(entry[col]))
        calculation = calc(values_to_calc)
        setattr(entry, formula_column_name, round(calculation, 4))
        entry.edit_date = timezone.now()
        success = True
    except (ValueError, KeyError) as operation:
        logger.warning(operation)
        setattr(entry, formula_column_name, "Error")
        entry.edit_date = timezone.now()
        success = False
    return entry, success


def calculateFormulaCell(entry, silo):
    """
    calculates all the formula for a given entry

    entry -- a query of label_value_store objects
    silo -- a silo object

    returns entry
    """
    formula_columns = silo.formulacolumns.all()
    for column in formula_columns:
        calculation_to_do = parseMathInstruction(column.operation)
        entry = calculateFormula(entry, calculation_to_do,
                                 json.loads(column.mapping),
                                 column.column_name)
        entry = entry[0]
    return entry


def makeQueryForHiddenRow(row_filter):
    """
    This function takes arrays of dictionaries in the format generated
    from when a row filter is added and returns a JSON formatted query
    to be able to plugged into the json format
    """
    query = {}
    empty = [""]
    # find and add any extra empty characters
    for condition in row_filter:
        if condition.get("logic", "") == "BLANKCHAR":
            empty.append(condition.get("conditional", ""))
    # now add to the query
    for condition in row_filter:
        # this does string comparisons
        num_to_compare = [condition.get("number", "")]
        try:
            num_to_compare.append(float(condition.get("number", "")))
            num_to_compare.append(int(condition.get("number", "")))
        except Exception as e:
            logger.warning(e)
        # specify the part of the dictionary to add to
        if condition.get("logic", "") == "AND":
            to_add = query
        elif condition.get("logic", "") == "OR":
            try:
                to_add = query["$or"]
            except KeyError:
                query["$or"] = {}
                to_add = query["$or"]
        for column in condition.get("conditional", []):
            if condition.get("operation", "") == "empty":
                try:
                    to_add[column]["$not"]["$exists"] = "true"
                except KeyError:
                    to_add[column] = {}
                    try:
                        to_add[column]["$not"]["$exists"] = "true"
                    except KeyError:
                        to_add[column]["$not"] = {}
                        to_add[column]["$not"]["$exists"] = "true"
                try:
                    to_add[column]["$not"]["$not"]["$in"] = empty
                except KeyError:
                    to_add[column]["$not"]["$not"] = {}
                    to_add[column]["$not"]["$not"]["$in"] = empty
            elif condition.get("operation", "") == "nempty":
                try:
                    to_add[column]["$exists"] = "true"
                except KeyError:
                    to_add[column] = {}
                    to_add[column]["$exists"] = "true"
                try:
                    to_add[column]["$not"]["$in"] = empty
                except KeyError:
                    to_add[column]["$not"] = {}
                    to_add[column]["$not"]["$in"] = empty
            elif condition.get("operation", "") == "eq":
                try:
                    to_add[column]['$in'].extend(num_to_compare)
                except KeyError:
                    to_add[column] = {}
                    try:
                        to_add[column]['$in'].extend(num_to_compare)
                    except KeyError:
                        to_add[column]['$in'] = num_to_compare
            elif condition.get("operation", "") == "neq":
                try:
                    to_add[column]['$nin'].extend(num_to_compare)
                except KeyError:
                    to_add[column] = {}
                    try:
                        to_add[column]['$nin'].extend(num_to_compare)
                    except KeyError:
                        to_add[column]['$nin'] = num_to_compare

    # convert the $or area to be properly formatted for a query
    or_items = query.get("$or", {})
    if len(or_items) > 0:
        query["$or"] = []
        for k, v in or_items.iteritems():
            query["$or"].append({k: v})

    query = json.dumps(query)
    return query


def getNewestDataDate(silo_id):
    """
    finds the newest date of data in a silo
    """
    client = MongoClient(settings.MONGO_URI)
    db = client.get_database(settings.MONGODB_DATABASES['default']['name'])
    newest_record = db.label_value_store.find({'silo_id': silo_id}).sort(
        [("create_date", -1)]).limit(1)

    return newest_record[0]['create_date']


# to convert floating point strings to integers
def strToInt(string):
    return int(float(string))


def setSiloColumnType(silo_pk, column, column_type):
    # TO DO: check for acceptable column type
    if column_type == 'int':
        cast_fnct = strToInt
        parse_cmd = 'parseInt'
    elif column_type == 'double':
        cast_fnct = float
        parse_cmd = 'parseFloat'
    elif column_type == 'string':
        cast_fnct = str
    else:
        raise TypeError(column_type)

    # TO DO: check if all entries could comply

    client = MongoClient(settings.MONGO_URI)
    db = client.get_database(settings.MONGODB_DATABASES['default']['name'])
    bulk = db.label_value_store.initialize_ordered_bulk_op()

    if (db.label_value_store.find({'silo_id': silo_pk, column: {'$not': {
            '$exists': True}}}).count() > 0):
        return messages.ERROR, 'Faluire to set column type due to not all ' \
                               'rows having designated column'

    # find a non castable row for int/float
    if column_type in ('int', 'float'):
        res = db.label_value_store.map_reduce(
            "function() { emit(isNaN({0}(this.{1})), this.{2}); }".format(
                parse_cmd, column, column),
            "function(key, value) {return value.toString();}",
            {'inline': 1},
            query={'silo_id': silo_pk}
        )
        if len(res['results']) > 1:
            unparsed_rows = [x for x in res['results'] if x['_id']]
            return messages.ERROR, '{0} is/are not parsable to {1}'.format(
                unparsed_rows[0]['value'], column_type)

    # change type in mysql database
    silo = Silo.objects.get(pk=silo_pk)
    silo_cols = json.loads(silo.columns)
    for col in silo_cols:
        if col['name'] == column:
            col['type'] = column_type
            break
    silo.columns = json.dumps(silo_cols)
    silo.save()

    counter = 0
    for data in db.label_value_store.find({'silo_id': silo_pk}):
        updoc = {
            "$set": {}
        }
        updoc["$set"][column] = cast_fnct(data[column])
        # queue the update
        bulk.find({'_id': data['_id']}).update(updoc)
        counter += 1
        # Drain and re-initialize every 1000 update statements
        if counter % 1000 == 0:
            bulk.execute()
            bulk = db.label_value_store.initialize_ordered_bulk_op()

    # Add the rest in the queue
    if counter % 1000 != 0:
        bulk.execute()

    return messages.SUCCESS, 'All success columns parsed succesfully'
