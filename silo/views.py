import datetime
import time
import json
import csv
import base64
import requests
import re
from requests.auth import HTTPDigestAuth
import logging
from operator import and_, or_
from collections import OrderedDict
import pymongo
from pymongo import MongoClient
from bson.objectid import ObjectId
from bson import CodecOptions, SON
from bson.json_util import dumps

from django.core.urlresolvers import reverse, reverse_lazy
from django.http import HttpResponseForbidden,\
    HttpResponseRedirect, HttpResponseNotFound, HttpResponseBadRequest,\
    HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render_to_response, get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.encoding import smart_str, smart_text
from django.utils.text import Truncator
from django.db.models import Max, F, Q
from django.views.decorators.csrf import csrf_protect
from django.template import RequestContext, Context
from django.conf import settings

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count

from silo.custom_csv_dict_reader import CustomDictReader
from .models import GoogleCredentialsModel
from gviews_v4 import import_from_gsheet_helper
from tola.util import siloToDict, combineColumns, importJSON, saveDataToSilo, getSiloColumnNames

from .models import Silo, Read, ReadType, ThirdPartyTokens, LabelValueStore, Tag, UniqueFields, MergedSilosFieldMapping, TolaSites, PIIColumn
from .forms import get_read_form, UploadForm, SiloForm, MongoEditForm, NewColumnForm, EditColumnForm, OnaLoginForm

logger = logging.getLogger("silo")
db = MongoClient(settings.MONGODB_HOST).tola

# To preserve fields order when reading BSON from MONGO
opts = CodecOptions(document_class=SON)
store = db.label_value_store.with_options(codec_options=opts)


def mergeTwoSilos(mapping_data, lsid, rsid, msid):
    """
    @params
    mapping_data: data that describes how mapping is done between two silos
    lsid: Left Silo ID
    rsid: Right Silo ID
    msid: Merge Silo ID
    """
    mappings = json.loads(mapping_data)

    l_unmapped_cols = mappings.pop('left_unmapped_cols')
    r_unampped_cols = mappings.pop('right_unmapped_cols')

    merged_cols = []

    #print("lsid:% rsid:%s msid:%s" % (lsid, rsid, msid))
    l_silo_data = LabelValueStore.objects(silo_id=lsid)

    r_silo_data = LabelValueStore.objects(silo_id=rsid)

    # Loop through the mapped cols and add them to the list of merged_cols
    for k, v in mappings.iteritems():
        col_name = v['right_table_col']
        if col_name == "silo_id" or col_name == "create_date": continue
        if col_name not in merged_cols:
            merged_cols.append(col_name)

    for lef_col in l_unmapped_cols:
        if lef_col not in merged_cols: merged_cols.append(lef_col)

    for right_col in r_unampped_cols:
        if right_col not in merged_cols: merged_cols.append(right_col)

    # retrieve the left silo
    try:
        lsilo = Silo.objects.get(pk=lsid)
    except Silo.DoesNotExist as e:
        msg = "Left Silo does not exist: silo_id=%s" % lsid
        logger.error(msg)
        return {'status': "danger",  'message': msg}

    # retrieve the right silo
    try:
        rsilo = Silo.objects.get(pk=rsid)
    except Silo.DoesNotExist as e:
        msg = "Right Table does not exist: table_id=%s" % rsid
        logger.error(msg)
        return {'status': "danger",  'message': msg}

    # retrieve the merged silo
    try:
        msilo = Silo.objects.get(pk=msid)
    except Silo.DoesNotExist as e:
        msg = "Merged Table does not exist: table_id=%s" % msid
        logger.error(msg)
        return {'status': "danger",  'message': msg}

    # retrieve the unique fields set for the right silo
    r_unique_fields = rsilo.unique_fields.all()

    if not r_unique_fields:
        msg = "The table, [%s], must have a unique column and it should be the same as the one specified in [%s] table." % (rsilo.name, lsilo.name)
        logger.error(msg)
        return {'status': "danger",  'message': msg}

    # retrive the unique fields of the merged_silo
    m_unique_fields = msilo.unique_fields.all()

    # make sure that the unique_fields from right table are in the merged_table
    # by adding them to the merged_cols array.
    for uf in r_unique_fields:
        if uf.name not in merged_cols: merged_cols.append(uf.name)

        #make sure to set the same unique_fields in the merged_table
        if not m_unique_fields.filter(name=uf.name).exists():
            unique_field, created = UniqueFields.objects.get_or_create(name=uf.name, silo=msilo, defaults={"name": uf.name, "silo": msilo})

    # Get the correct set of data from the right table
    for row in r_silo_data:
        merged_row = OrderedDict()
        for k in row:
            # Skip over those columns in the right table that sholdn't be in the merged_table
            if k not in merged_cols: continue
            merged_row[k] = row[k]

        # now set its silo_id to the merged_table id
        merged_row["silo_id"] = msid
        merged_row["create_date"] = timezone.now()

        filter_criteria = {}
        for uf in r_unique_fields:
            try:
                filter_criteria.update({str(uf.name): str(merged_row[uf.name])})
            except KeyError as e:
                # when this excpetion occurs, it means that the col identified
                # as the unique_col is not present in all rows of the right_table
                logger.warning("The field, %s, is not present in table id=%s" % (uf.name, rsid))

        # adding the merged_table_id because the filter criteria should search the merged_table
        filter_criteria.update({'silo_id': msid})

        #this is an upsert operation.; note the upsert=True
        db.label_value_store.update_one(filter_criteria, {"$set": merged_row}, upsert=True)


    # Retrieve the unique_fields set by left table
    l_unique_fields = lsilo.unique_fields.all()
    if not l_unique_fields:
        msg = "The table, [%s], must have a unique column and it should be the same as the one specified in [%s] table." % (lsilo.name, rsilo.name)
        logger.error(msg)
        return {'status': "danger",  'message': msg}

    for uf in l_unique_fields:
        # if there are unique fields that are not in the right table then show error
        if not r_unique_fields.filter(name=uf.name).exists():
            msg = "Both tables (%s, %s) must have the same column set as unique fields" % (lsilo.name, rsilo.name)
            logger.error(msg)
            return {"status": "danger", "message": msg}

    # now loop through left table and apply the mapping
    for row in l_silo_data:
        merged_row = OrderedDict()
        # Loop through the column mappings for each row in left_table.
        for k, v in mappings.iteritems():
            merge_type = v['merge_type']
            left_cols = v['left_table_cols']
            right_col = v['right_table_col']

            # if merge_type is specified then there must be multiple columns in the left_cols array
            if merge_type:
                mapped_value = ''
                for col in left_cols:
                    if merge_type == 'Sum' or merge_type == 'Avg':
                        try:
                            if mapped_value == '':
                                mapped_value = float(row[col])
                            else:
                                mapped_value = float(mapped_value) + float(row[col])
                        except Exception as e:
                            msg = 'Failed to apply %s to column, %s : %s ' % (merge_type, col, e.message)
                            logger.error(msg)
                            return {'status': "danger",  'message': msg}
                    else:
                        mapped_value += ' ' + smart_str(row[col])

                # Now calculate avg if the merge_type was actually "Avg"
                if merge_type == 'Avg':
                    mapped_value = mapped_value / len(left_cols)
            # only one col in left table is mapped to one col in the right table.
            else:
                col = str(left_cols[0])
                if col == "silo_id": continue
                try:
                    mapped_value = row[col]
                except KeyError as e:
                    # When updating data in merged_table at a later time, it is possible
                    # the origianl source tables may have had some columns removed in which
                    # we might get a KeyError so in that case we just skip it.
                    continue

            #right_col is used as in index of merged_row because one or more left cols map to one col in right table
            merged_row[right_col] = mapped_value

        # Get data from left unmapped columns:
        for col in l_unmapped_cols:
            if col in row:
                merged_row[col] = row[col]

        filter_criteria = {}
        for uf in l_unique_fields:
            try:
                filter_criteria.update({str(uf.name): str(merged_row[uf.name])})
            except KeyError:
                # when this excpetion occurs, it means that the col identified
                # as the unique_col is not present in all rows of the left_table
                msg ="The field, %s, is not present in table id=%s" % (uf.name, lsid)
                logger.warning(msg)

        filter_criteria.update({'silo_id': msid})

        # override the silo_id and create_date columns values to make sure they're not set
        # to the values that are in left table or right table
        merged_row["silo_id"] = msid
        merged_row["create_date"] = timezone.now()

        # Now update or insert a row if there is no matching record available
        res = db.label_value_store.update_one(filter_criteria, {"$set": merged_row}, upsert=True)

        # Make sure all rows have the same cols in the merged_silo
    combineColumns(msid)
    return {'status': "success",  'message': "Merged data successfully"}

def appendTwoSilos(mapping_data, lsid, rsid, msid):
    """
    @params
    mapping_data: data that describes how mapping is done between two silos
    lsid: Left Silo ID
    rsid: Right Silo ID
    msid: Merge Silo ID
    """
    mappings = json.loads(mapping_data)

    l_unmapped_cols = mappings.pop('left_unmapped_cols')
    r_unampped_cols = mappings.pop('right_unmapped_cols')

    merged_cols = []

    #print("lsid:% rsid:%s msid:%s" % (lsid, rsid, msid))
    l_silo_data = LabelValueStore.objects(silo_id=lsid)

    r_silo_data = LabelValueStore.objects(silo_id=rsid)

    # Loop through the mapped cols and add them to the list of merged_cols
    for k, v in mappings.iteritems():
        col_name = v['right_table_col']
        if col_name == "silo_id" or col_name == "create_date": continue
        if col_name not in merged_cols:
            merged_cols.append(col_name)

    for lef_col in l_unmapped_cols:
        if lef_col not in merged_cols: merged_cols.append(lef_col)

    for right_col in r_unampped_cols:
        if right_col not in merged_cols: merged_cols.append(right_col)

    # retrieve the left silo
    try:
        lsilo = Silo.objects.get(pk=lsid)
    except Silo.DoesNotExist as e:
        msg = "Table id=%s does not exist." % lsid
        logger.error(msg)
        return {'status': "danger",  'message': msg}

    # retrieve the right silo
    try:
        rsilo = Silo.objects.get(pk=rsid)
    except Silo.DoesNotExist as e:
        msg = "Right Table does not exist: table_id=%s" % rsid
        logger.error(msg)
        return {'status': "danger",  'message': msg}

    # retrieve the merged silo
    try:
        msilo = Silo.objects.get(pk=msid)
    except Silo.DoesNotExist as e:
        msg = "Merged Table does not exist: table_id=%s" % msid
        logger.error(msg)
        return {'status': "danger",  'message': msg}


    # Delete Any existing data from the merged_table
    deleted_res = db.label_value_store.delete_many({"silo_id": msid})

    # Get the correct set of data from the right table
    for row in r_silo_data:
        merged_row = OrderedDict()
        for k in row:
            # Skip over those columns in the right table that sholdn't be in the merged_table
            if k not in merged_cols: continue
            merged_row[k] = row[k]

        # now set its silo_id to the merged_table id
        merged_row["silo_id"] = msid
        merged_row["create_date"] = timezone.now()
        db.label_value_store.insert_one(merged_row)


    # now loop through left table and apply the mapping
    for row in l_silo_data:
        merged_row = OrderedDict()
        # Loop through the column mappings for each row in left_table.
        for k, v in mappings.iteritems():
            merge_type = v['merge_type']
            left_cols = v['left_table_cols']
            right_col = v['right_table_col']

            # if merge_type is specified then there must be multiple columns in the left_cols array
            if merge_type:
                mapped_value = ''
                for col in left_cols:
                    if merge_type == 'Sum' or merge_type == 'Avg':
                        try:
                            if mapped_value == '':
                                mapped_value = float(row[col])
                            else:
                                mapped_value = float(mapped_value) + float(row[col])
                        except Exception as e:
                            msg = 'Failed to apply %s to column, %s : %s ' % (merge_type, col, e.message)
                            logger.error(msg)
                            return {'status': "danger",  'message': msg}
                    else:
                        mapped_value += ' ' + smart_str(row[col])

                # Now calculate avg if the merge_type was actually "Avg"
                if merge_type == 'Avg':
                    mapped_value = mapped_value / len(left_cols)
            # only one col in left table is mapped to one col in the right table.
            else:
                col = str(left_cols[0])
                if col == "silo_id": continue
                try:
                    mapped_value = row[col]
                except KeyError as e:
                    # When updating data in merged_table at a later time, it is possible
                    # the origianl source tables may have had some columns removed in which
                    # we might get a KeyError so in that case we just skip it.
                    continue

            #right_col is used as in index of merged_row because one or more left cols map to one col in right table
            merged_row[right_col] = mapped_value

        # Get data from left unmapped columns:
        for col in l_unmapped_cols:
            if col in row:
                merged_row[col] = row[col]

        merged_row["silo_id"] = msid
        merged_row["create_date"] = timezone.now()

        db.label_value_store.insert_one(merged_row)
    combineColumns(msid)
    return {'status': "success",  'message': "Appended data successfully"}


# Edit existing silo meta data
@csrf_protect
@login_required
def editSilo(request, id):
    """
    Edit the meta data and descirptor for each Table (silo)
    :param request:
    :param id: Unique table ID
    :return: silo edit form
    """
    edited_silo = Silo.objects.get(pk=id)
    if request.method == 'POST':  # If the form has been submitted...
        tags = request.POST.getlist('tags')
        post_data = request.POST.copy()

        #empty the list but do not remove the dictionary element
        if tags: del post_data.getlist('tags')[:]

        for i, t in enumerate(tags):
            if t.isdigit():
                post_data.getlist('tags').append(t)
            else:
                tag, created = Tag.objects.get_or_create(name=t, defaults={'owner': request.user})
                if created:
                    #print("creating tag: %s " % tag)
                    tags[i] = tag.id
                #post_data is a QueryDict in which each element is a list
                post_data.getlist('tags').append(tag.id)

        form = SiloForm(post_data, instance=edited_silo)
        if form.is_valid():
            updated = form.save()
            return HttpResponseRedirect('/silos/')
        else:
            messages.error(request, 'Invalid Form', fail_silently=False)
    else:
        form = SiloForm(instance=edited_silo)
    return render(request, 'silo/edit.html', {
        'form': form, 'silo_id': id, "silo": edited_silo,
    })


@login_required
def saveAndImportRead(request):
    """
    Saves ONA read if not already in the db and then imports its data
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("HTTP method, %s, is not supported" % request.method)

    read_type = ReadType.objects.get(read_type="ONA")
    name = request.POST.get('read_name', None)
    url = request.POST.get('read_url', None)
    owner = request.user
    description = request.POST.get('description', None)
    silo_id = None
    read = None
    silo = None
    provider = "ONA"

    # Fetch the data from ONA
    ona_token = ThirdPartyTokens.objects.get(user=request.user, name=provider)
    response = requests.get(url, headers={'Authorization': 'Token %s' % ona_token.token})
    data = json.loads(response.content)

    if len(data) == 0:
        return HttpResponse("There is not data for the selected form, %s" % name)

    try:
        silo_id = int(request.POST.get("silo_id", None))
        if silo_id == 0: silo_id = None
    except Exception as e:
         return HttpResponse("Silo ID can only be an integer")

    try:
        read, read_created = Read.objects.get_or_create(read_name=name, owner=owner,
            defaults={'read_url': url, 'type': read_type, 'description': description})
        if read_created: read.save()
    except Exception as e:
        return HttpResponse("Invalid name and/or URL")

    existing_silo_cols = []
    new_cols = []
    show_mapping = False

    silo, silo_created = Silo.objects.get_or_create(id=silo_id, defaults={"name": name,
                                      "public": False,
                                      "owner": owner})
    if silo_created or read_created:
        silo.reads.add(read)
    elif read not in silo.reads.all():
        silo.reads.add(read)

    """
    #
    # THIS WILL BE ADDED LATER ONCE THE saveDataToSilo REFACTORING IS COMPLETE!
    #
    # Get all of the unique cols for this silo into an array
    lvs = json.loads(LabelValueStore.objects(silo_id=silo.id).to_json())
    for l in lvs:
        existing_silo_cols.extend(c for c in l.keys() if c not in existing_silo_cols)

    # Get all of the unique cols of the fetched data in a separate array
    for row in data:
        new_cols.extend(c for c in row.keys() if c not in new_cols)

    # Loop through the unique cols of fetched data; if there are cols that do
    # no exist in the existing silo, then show mapping.
    for c in new_cols:
        if c == "silo_id" or c == "create_date" or c == "edit_date" or c == "id": continue
        if c not in existing_silo_cols: show_mapping = True
        if show_mapping == True:
            # store the newly fetched data into a temp table and then show mapping
            params = {'getSourceFrom':existing_silo_cols, 'getSourceTo':new_cols, 'from_silo_id':0, 'to_silo_id':silo.id}
            response = render_to_response("display/merge-column-form-inner.html", params, context_instance=RequestContext(request))
            response['show_mapping'] = '1'
            return response
    """

    # import data into this silo
    res = saveDataToSilo(silo, data)
    return HttpResponse("View table data at <a href='/silo_detail/%s' target='_blank'>See your data</a>" % silo.pk)

@login_required
def getOnaForms(request):
    """
    Get the forms owned or shared with the logged in user
    :param request:
    :return: list of Ona forms paired with action buttons
    """
    data = {}
    auth_success = False
    ona_token = None
    form = None
    provider = "ONA"
    url_user_token = "https://api.ona.io/api/v1/user.json"
    url_user_forms = 'https://api.ona.io/api/v1/data'
    if request.method == 'POST':
        form = OnaLoginForm(request.POST)
        if form.is_valid():
            response = requests.get(url_user_token, auth=HTTPDigestAuth(request.POST['username'], request.POST['password']))
            if response.status_code == 401:
                messages.error(request, "Invalid username or password.")
            elif response.status_code == 200:
                auth_success = True
                token = json.loads(response.content)['api_token']
                ona_token, created = ThirdPartyTokens.objects.get_or_create(user=request.user, name=provider, token=token)
                if created: ona_token.save()
            else:
                messages.error(request, "A %s error has occured: %s " % (response.status_code, response.text))
    else:
        try:
            auth_success = True
            ona_token = ThirdPartyTokens.objects.get(name=provider, user=request.user)
        except Exception as e:
            auth_success = False
            form = OnaLoginForm()

    if ona_token and auth_success:
        onaforms = requests.get(url_user_forms, headers={'Authorization': 'Token %s' % ona_token.token})
        data = json.loads(onaforms.content)

    silos = Silo.objects.filter(owner=request.user)
    return render(request, 'silo/getonaforms.html', {
        'form': form, 'data': data, 'silos': silos
    })

@login_required
def providerLogout(request,provider):

    ona_token = ThirdPartyTokens.objects.get(user=request.user, name=provider)
    ona_token.delete()

    messages.error(request, "You have been logged out of your Ona account.  Any Tables you have created with this account ARE still available, but you must log back in here to update them.")
    return HttpResponseRedirect(request.META['HTTP_REFERER'])


#DELETE-SILO
@csrf_protect
def deleteSilo(request, id):
    owner = Silo.objects.get(id = id).owner

    if str(owner.username) == str(request.user):
        try:
            silo_to_be_deleted = Silo.objects.get(pk=id)
            silo_name = silo_to_be_deleted.name
            lvs = LabelValueStore.objects(silo_id=silo_to_be_deleted.id)
            num_rows_deleted = lvs.delete()
            silo_to_be_deleted.delete()
            messages.success(request, "Silo, %s, with all of its %s rows of data deleted successfully." % (silo_name, num_rows_deleted))
        except Silo.DoesNotExist as e:
            print(e)
        except Exception as es:
            print(es)
        return HttpResponseRedirect("/silos")
    else:
        messages.error(request, "You do not have permission to delete this silo")
        return HttpResponseRedirect(request.META['HTTP_REFERER'])


@login_required
def showRead(request, id):
    """
    Show a read data source and allow user to edit it
    """
    excluded_fields = ['gsheet_id', 'resource_id', 'token', 'create_date', 'edit_date', 'token']
    initial = {'owner': request.user}

    try:
        read_instance = Read.objects.get(pk=id)
        read_type = read_instance.type.read_type
    except Read.DoesNotExist as e:
        read_instance = None
        read_type = request.GET.get("type", "CSV")
        initial['type'] = ReadType.objects.get(read_type=read_type)


    if read_type == "GSheet Import" or read_type == "ONA":
        excluded_fields = excluded_fields + ['username', 'password', 'file_data','autopush_frequency']
    elif read_type == "JSON":
        excluded_fields = excluded_fields + ['file_data','autopush_frequency']
    elif read_type == "Google Spreadsheet":
        excluded_fields = excluded_fields + ['username', 'password', 'file_data', 'autopull_frequency']
    elif read_type == "CSV":
        excluded_fields = excluded_fields + ['username', 'password', 'autopush_frequency', 'autopull_frequency', 'read_url']

    if request.method == 'POST':
        form = get_read_form(excluded_fields)(request.POST, request.FILES, instance=read_instance)
        if form.is_valid():
            read = form.save(commit=False)
            if read.username and read.password:
                basic_auth = base64.encodestring('%s:%s' % (read.username, read.password))[:-1]
                read.token = basic_auth
                read.password = None
            read.save()
            if form.instance.type.read_type == "CSV":
                return HttpResponseRedirect("/file/" + str(read.id) + "/")
            elif form.instance.type.read_type == "JSON":
                return HttpResponseRedirect(reverse_lazy("getJSON")+ "?read_id=%s" % read.id)

            if form.instance.autopull_frequency or form.instance.autopush_frequency:
                messages.info(request, "Your table must have a unique column set for Autopull/Autopush to work.")
            return HttpResponseRedirect(reverse_lazy('listSilos'))
        else:
            messages.error(request, 'Invalid Form', fail_silently=False)
    else:
        form = get_read_form(excluded_fields)(instance=read_instance, initial=initial)
    return render(request, 'read/read.html', {
        'form': form, 'read_id': id,
    })

@login_required
def uploadFile(request, id):
    """
    Upload CSV file and save its data
    """
    if request.method == 'POST':
        form = UploadForm(request.POST)
        if form.is_valid():
            read_obj = Read.objects.get(pk=id)
            today = datetime.date.today()
            today.strftime('%Y-%m-%d')
            today = str(today)

            silo = None
            user = User.objects.get(username__exact=request.user)

            if request.POST.get("new_silo", None):
                silo = Silo(name=request.POST['new_silo'], owner=user, public=False, create_date=today)
                silo.save()
            else:
                silo = Silo.objects.get(id = request.POST["silo_id"])

            silo.reads.add(read_obj)
            silo_id = silo.id

            #create object from JSON String
            #data = csv.reader(read_obj.file_data)
            #reader = csv.DictReader(read_obj.file_data)
            reader = CustomDictReader(read_obj.file_data)
            res = saveDataToSilo(silo, reader)
            return HttpResponseRedirect('/silo_detail/' + str(silo_id) + '/')
        else:
            messages.error(request, "There was a problem with reading the contents of your file" + form.errors)
            #print form.errors

    user = User.objects.get(username__exact=request.user)
    # get all of the silo info to pass to the form
    get_silo = Silo.objects.filter(owner=user)

    # display the form for user to choose a table or ener a new table name to import data into
    return render(request, 'read/file.html', {
        'read_id': id, 'form_action': reverse_lazy("uploadFile", kwargs={"id": id}), 'get_silo': get_silo,
    })


@login_required
def getJSON(request):
    """
    Get JSON feed info from a feed that does not have basic authentication
    :param request:
    :return:
    """
    if request.method == 'POST':
        # retrieve submitted Feed info from database
        read_obj = Read.objects.get(id = request.POST.get("read_id", None))
        remote_user = request.POST.get("user_name", None)
        password = request.POST.get("password", None)
        silo_id = request.POST.get("silo_id", None)
        silo_name = request.POST.get("new_silo", None)
        result = importJSON(read_obj, request.user, remote_user, password, silo_id, silo_name)
        silo_id = str(result[2])
        if result[0] == "error":
            messages.error(request, result[1])
        else:
            messages.success(request, result[1])
        return HttpResponseRedirect('/silo_detail/%s/' % silo_id)
    else:
        silos = Silo.objects.filter(owner=request.user)
        # display the form for user to choose a table or ener a new table name to import data into
        return render(request, 'read/file.html', {
            'form_action': reverse_lazy("getJSON"), 'get_silo': silos
        })
#display
#INDEX
def index(request):
    #if request.COOKIES.get('auth_token', None):

    # get all of the table(silo) info for logged in user and public data
    if request.user.is_authenticated():
        user = User.objects.get(username__exact=request.user)
        get_silos = Silo.objects.filter(owner=user)
        # count all public and private data sets
        count_all = Silo.objects.filter(owner=user).count()
        count_public = Silo.objects.filter(owner=user).filter(public=1).count()
        count_shared = Silo.objects.filter(owner=user).filter(shared=1).count()
        # top 4 data sources and tags
        get_reads = ReadType.objects.annotate(num_type=Count('read')).order_by('-num_type')[:4]
        get_tags = Tag.objects.filter(owner=user).annotate(num_tag=Count('silos')).order_by('-num_tag')[:8]
    else:
        get_silos = None
        # count all public and private data sets
        count_all = Silo.objects.count()
        count_public = Silo.objects.filter(public=1).count()
        count_shared = Silo.objects.filter(shared=1).count()
        # top 4 data sources and tags
        get_reads = ReadType.objects.annotate(num_type=Count('read')).order_by('-num_type')[:4]
        get_tags = Tag.objects.annotate(num_tag=Count('silos')).order_by('-num_tag')[:8]
    get_public = Silo.objects.filter(public=1)
    site = TolaSites.objects.get(site_id=1)
    response = render(request, 'index.html',{'get_silos':get_silos,'get_public':get_public, 'count_all':count_all, 'count_shared':count_shared, 'count_public': count_public, 'get_reads': get_reads, 'get_tags': get_tags, 'site': site})

    if  request.COOKIES.get('auth_token', None) is None and request.user.is_authenticated():
        response.set_cookie('auth_token', user.auth_token)
    return  response


def toggle_silo_publicity(request):
    silo_id = request.GET.get('silo_id', None)
    silo = Silo.objects.get(pk=silo_id)
    silo.public = not silo.public
    silo.save()
    return HttpResponse("Your change has been saved")

#SILOS
@login_required
def listSilos(request):
    """
    Each silo is listed with links to details
    """
    user = User.objects.get(username__exact=request.user)

    #get all of the silos
    own_silos = Silo.objects.filter(owner=user).prefetch_related('reads')

    shared_silos = Silo.objects.filter(shared__id=user.pk).prefetch_related("reads")

    public_silos = Silo.objects.filter(Q(public=True) & ~Q(owner=user)).prefetch_related("reads")
    return render(request, 'display/silos.html',{'own_silos':own_silos, "shared_silos": shared_silos, "public_silos": public_silos})


def addUniqueFiledsToSilo(request):
    if request.method == 'POST':
        unique_cols = request.POST.getlist("fields[]", None)
        silo_id = request.POST.get("silo_id", None)
        if silo_id:
            silo = Silo.objects.get(pk=silo_id)
            silo.unique_fields.all().delete()
            for col in unique_cols:
                unique_field = UniqueFields(name=col, silo=silo)
                unique_field.save()
            if not unique_cols:
                silo.unique_fields.all().delete()
            return HttpResponse("Unique Fields saved")
    return HttpResponse("Only POST requests are processed.")


@login_required
def updateEntireColumn(request):
    silo_id = request.POST.get("silo_id", None)
    silo_id = int(silo_id)
    colname = request.POST.get("update_col", None)
    new_val = request.POST.get("new_val", None)
    if silo_id and colname and new_val:
        db.label_value_store.update_many(
                {"silo_id": silo_id},
                    {
                    "$set": {colname: new_val},
                    },
                False
            )
        messages.success(request, "Successfully, changed the %s column value to %s" % (colname, new_val))

    return HttpResponseRedirect(reverse_lazy('siloDetail', kwargs={'silo_id': silo_id}))


@login_required
def siloDetail(request, silo_id):
    """
    Silo Detail
    """
    silo = Silo.objects.get(pk=silo_id)
    cols = []
    data = []

    if silo.owner == request.user or silo.public == True or request.user in silo.shared.all():
        bsondata = store.find({"silo_id": silo.pk})
        #bsondata = db.label_value_store.find({"silo_id": silo.pk})
        for row in bsondata:
            # Add a column that contains edit/del links for each row in the table
            """
            row[cols[0]]=(
                "<a href='/value_edit/%s'>"
                    "<span class='glyphicon glyphicon-edit' aria-hidden='true'></span>"
                "</a>"
                "&nbsp;"
                "<a href='/value_delete/%s' class='btn-del' title='You are about to delete a record. Are you sure?'>"
                    "<span style='color:red;' class='glyphicon glyphicon-trash' aria-hidden='true'></span>"
                "</a>") % (row["_id"], row['_id'])
            """
            # Using OrderedDict to maintain column orders
            #print(type(row))
            data.append(OrderedDict(row))

            # create a distinct list of column names to be used for datatables in templates
            cols.extend([c for c in row.keys() if c not in cols and
                        #c != "_id" and
                        c != "create_date" and
                        c != "edit_date" and
                        c != "silo_id"])
            break
        # convert bson data to json data using json_utils.dumps from pymongo module
        data = dumps(data)
    else:
        messages.warning(request,"You do not have permission to view this table.")
    return render(request, "display/silo.html", {"silo": silo, "cols": cols})


@login_required
def updateSiloData(request, pk):
    silo = None
    merged_silo_mapping = None
    unique_field_exist = False
    try:
        silo = Silo.objects.get(pk=pk)
    except Silo.DoesNotExist as e:
        messages.error(request,"Table with id=%s does not exist." % pk)

    if silo:
        try:
            merged_silo_mapping = MergedSilosFieldMapping.objects.get(merged_silo = silo.pk)
            left_table_id = merged_silo_mapping.from_silo.pk
            right_table_id = merged_silo_mapping.to_silo.pk
            merge_table_id = merged_silo_mapping.merged_silo.pk
            mapping = merged_silo_mapping.mapping
            mergeType = merged_silo_mapping.merge_type

            if mergeType == "merge":
                res = mergeTwoSilos(mapping, left_table_id, right_table_id, merge_table_id)
            else:
                res = appendTwoSilos(mapping, left_table_id, right_table_id, merge_table_id)
            if res['status'] == "success":
                messages.success(request, res['message'])
            else:
                messages.error(request, res['message'])
        except MergedSilosFieldMapping.DoesNotExist as e:
            unique_field_exist = silo.unique_fields.exists()
            if  unique_field_exist == False:
                lvs = LabelValueStore.objects(silo_id=silo.pk)
                lvs.delete()

            reads = silo.reads.all()
            msgs = importDataFromReads(request, silo, reads)
            if type(msgs) == list:
                for msg in msgs:
                    messages.add_message(request, msg.get("level", "warning"), msg.get("msg", None))
            else:
                messages.add_message(request, msgs[0], msgs[1])

    return HttpResponseRedirect(reverse_lazy('siloDetail', kwargs={'silo_id': pk},))

def importDataFromReads(request, silo, reads):
    for read in reads:
        if read.type.read_type == "ONA":
            ona_token = ThirdPartyTokens.objects.get(user=silo.owner.pk, name="ONA")
            response = requests.get(read.read_url, headers={'Authorization': 'Token %s' % ona_token.token})
            data = json.loads(response.content)
            res = saveDataToSilo(silo, data)
        elif read.type.read_type == "CSV":
            #messages.info(request, "When updating data in a table, its CSV source is ignored.")
            return (messages.INFO, "When updating data in a table, its CSV source is ignored.")
        elif read.type.read_type == "JSON":
            result = importJSON(read, request.user, None, None, silo.pk, None)
            #messages.add_message(request, result[0], result[1])
            return (result[0], result[1])
        elif read.type.read_type == "GSheet Import":
            msgs = import_from_gsheet_helper(request.user, silo.id, None, read.resource_id)
            return msgs
            #for msg in msgs:
            #    messages.add_message(request, msg.get("level", "warning"), msg.get("msg", None))
        elif read.type.read_type == "CommCare":
            commcare_token = None
            try:
                commcare_token = ThirdPartyTokens.objects.get(user=silo.owner.pk, name="CommCare")
            except Exception as e:
                return (messages.ERROR, "You need to login to commcare using an API Key to access this functionality")
            response = requests.get(read.read_url, headers={'Authorization': 'ApiKey %(u)s:%(a)s' % {'u' : commcare_token.username, 'a' : commcare_token.token}})
            if response.status_code == 401:
                commcare_token.delete()
                return(messages.ERROR, "Your usernmane or API Key are incorrect")
            elif response.status_code != 200:
                return(messages.ERROR, "A %s error has occured: %s " % (response.status_code, response.text))
            metadata = json.loads(response.content)
            data=metadata['data']
            res = saveDataToSilo(silo, data)
            #now if their are more pages to the data get them
            url = read.read_url[:-1]
            i = 1
            while metadata['next_page'] !="":
                response = requests.get(url+str(i*50), headers={'Authorization': 'ApiKey %(u)s:%(a)s' % {'u' : commcare_token.username, 'a' : commcare_token.token}})
                metadata = json.loads(response.content)
                data=metadata['data']
                res = saveDataToSilo(silo, data)
                i+=1
            return (messages.SUCCESS, "Update was successful")


#Add a new column on to a silo
@login_required
def newColumn(request,id):
    """
    FORM TO CREATE A NEW COLUMN FOR A SILO
    """
    silo = Silo.objects.get(id=id)
    form = NewColumnForm(initial={'silo_id': silo.id})

    if request.method == 'POST':
        form = NewColumnForm(request.POST)  # A form bound to the POST data
        if form.is_valid():  # All validation rules pass
            label = form.cleaned_data['new_column_name']
            value = form.cleaned_data['default_value']
            #insert a new column into the existing silo
            db.label_value_store.update_many(
                {"silo_id": silo.id},
                    {
                    "$set": {label: value},
                    },
                False
            )
            messages.info(request, 'Your column has been added', fail_silently=False)
        else:
            messages.error(request, 'There was a problem adding your column', fail_silently=False)
            #print form.errors


    return render(request, "silo/new-column-form.html", {'silo':silo,'form': form})

#Add a new column on to a silo
@login_required
def editColumns(request,id):
    """
    FORM TO CREATE A NEW COLUMN FOR A SILO
    """
    silo = Silo.objects.get(id=id)

    if request.method == 'POST':
        form = EditColumnForm(request.POST or None, extra = data)  # A form bound to the POST data
        if form.is_valid():  # All validation rules pass
            for label,value in form.cleaned_data.iteritems():
                #update the column name if it doesn't have delete in it
                if "_delete" not in label and str(label) != str(value) and label != "silo_id" and label != "suds" and label != "id":
                    #update a column in the existing silo
                    db.label_value_store.update_many(
                        {"silo_id": silo.id},
                            {
                            "$rename": {label: value},
                            },
                        False
                    )
                #if we see delete then it's a check box to delete that column
                elif "_delete" in label and value == 1:
                    column = label.replace("_delete", "")
                    db.label_value_store.update_many(
                        {"silo_id": silo.id},
                            {
                            "$unset": {column: value},
                            },
                        False
                    )
            messages.info(request, 'Updates Saved', fail_silently=False)
        else:
            messages.error(request, 'ERROR: There was a problem with your request', fail_silently=False)
            #print form.errors

    data = getSiloColumnNames(id)
    form = EditColumnForm(initial={'silo_id': silo.id}, extra=data)
    return render(request, "silo/edit-column-form.html", {'silo':silo,'form': form})

#Delete a column from a table silo
@login_required
def deleteColumn(request,id,column):
    """
    DELETE A COLUMN FROM A SILO
    """
    silo = Silo.objects.get(id=id)

    #delete a column from the existing table silo
    db.label_value_store.update_many(
        {"silo_id": silo.id},
            {
            "$unset": {column: ""},
            },
        False
    )

    messages.info(request, "Column has been deleted")
    return HttpResponseRedirect(request.META['HTTP_REFERER'])



#SHOW-MERGE FORM
@login_required
def mergeForm(request,id):
    """
    Merge different silos using a multistep column mapping form
    """
    getSource = Silo.objects.get(id=id)
    getSourceTo = Silo.objects.filter(owner=request.user)
    return render(request, "display/merge-form.html", {'getSource':getSource,'getSourceTo':getSourceTo})

#SHOW COLUMNS FOR MERGE FORM
def mergeColumns(request):
    """
    Step 2 in Merge different silos, map columns
    """
    from_silo_id = request.POST["from_silo_id"]
    to_silo_id = request.POST["to_silo_id"]

    lvs = json.loads(LabelValueStore.objects(silo_id__in = [from_silo_id, to_silo_id]).to_json())
    getSourceFrom = []
    getSourceTo = []
    for l in lvs:
        if from_silo_id == str(l['silo_id']):
            getSourceFrom.extend([k for k in l.keys() if k not in getSourceFrom])
        else:
            getSourceTo.extend([k for k in l.keys() if k not in getSourceTo])

    return render(request, "display/merge-column-form.html", {'getSourceFrom':getSourceFrom, 'getSourceTo':getSourceTo, 'from_silo_id':from_silo_id, 'to_silo_id':to_silo_id})



def doMerge(request):

    # get the table_ids.
    left_table_id = request.POST['left_table_id']
    right_table_id = request.POST["right_table_id"]
    mergeType = request.POST.get("tableMergeType", None)
    left_table = None
    right_table = None

    merged_silo_name = request.POST['merged_table_name']

    if not merged_silo_name:
        merged_silo_name = "Merging of %s and %s" % (left_table_id, right_table_id)

    try:
        left_table = Silo.objects.get(id=left_table_id)
    except Silo.DoesNotExist as e:
        return HttpResponse("Could not find left table with id=%s" % left_table_id)

    try:
        right_table = Silo.objects.get(id=right_table_id)
    except Silo.DoesNotExist as e:
        return HttpResponse("Could not find right table with id=%s" % left_table_id)

    data = request.POST.get('columns_data', None)
    if not data:
        return HttpResponse("no columns data passed")

    # Create a new silo
    new_silo = Silo(name=merged_silo_name , public=False, owner=request.user)
    new_silo.save()
    merge_table_id = new_silo.pk

    if mergeType == "merge":
        res = mergeTwoSilos(data, left_table_id, right_table_id, merge_table_id)
    else:
        res = appendTwoSilos(data, left_table_id, right_table_id, merge_table_id)

    try:
        if res['status'] == "danger":
            new_silo.delete()
            return JsonResponse(res)
    except Exception as e:
        pass

    mapping = MergedSilosFieldMapping(from_silo=left_table, to_silo=right_table, merged_silo=new_silo, merge_type=mergeType, mapping=data)
    mapping.save()
    return JsonResponse({'status': "success",  'message': 'The merged table is accessible at <a href="/silo_detail/%s/" target="_blank">Merged Table</a>' % new_silo.pk})


#EDIT A SINGLE VALUE STORE
@login_required
def valueEdit(request,id):
    """
    Edit a value
    """
    doc = LabelValueStore.objects(id=id).to_json()
    data = {}
    jsondoc = json.loads(doc)
    silo_id = None

    for item in jsondoc:
        for k, v in item.iteritems():
            #print("The key and value are ({}) = ({})".format(smart_str(k), smart_str(v)))
            if k == "_id":
                #data[k] = item['_id']['$oid']
                pass
            elif k == "silo_id":
                silo_id = v
            elif k == "edit_date":
                if item['edit_date']:
                    edit_date = datetime.datetime.fromtimestamp(item['edit_date']['$date']/1000)
                    data[k] = edit_date.strftime('%Y-%m-%d %H:%M:%S')
            elif k == "create_date":
                create_date = datetime.datetime.fromtimestamp(item['create_date']['$date']/1000)
                data[k] = create_date.strftime('%Y-%m-%d')
            else:
                k = Truncator(re.sub('\s+', ' ', k).strip()).chars(40)
                data[k] = v
    if request.method == 'POST': # If the form has been submitted...
        form = MongoEditForm(request.POST or None, extra = data) # A form bound to the POST data
        if form.is_valid():
            lvs = LabelValueStore.objects(id=id)[0]
            for lbl, val in form.cleaned_data.iteritems():
                if lbl != "id" and lbl != "silo_id" and lbl != "csrfmiddlewaretoken":
                    setattr(lvs, lbl, val)
            lvs.edit_date = timezone.now()
            lvs.save()
            return HttpResponseRedirect('/value_edit/' + id)
        else:
            print "not valid"
    else:
        form = MongoEditForm(initial={'silo_id': silo_id, 'id': id}, extra=data)

    return render(request, 'read/edit_value.html', {'form': form, 'silo_id': silo_id})

@login_required
def valueDelete(request,id):
    """
    Delete a value
    """
    silo_id = None
    lvs = LabelValueStore.objects(id=id)[0]
    owner = Silo.objects.get(id = lvs.silo_id).owner

    if str(owner.username) == str(request.user):
        silo_id = lvs.silo_id
        lvs.delete()
    else:
        messages.error(request, "You don't have the permission to delete records from this silo")
        return HttpResponseRedirect(request.META['HTTP_REFERER'])

    messages.success(request, "Record deleted successfully")
    return HttpResponseRedirect('/silo_detail/%s/' % silo_id)


def export_silo(request, id):

    silo_name = Silo.objects.get(id=id).name

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="%s.csv"' % silo_name
    writer = csv.writer(response)

    # Loads the bson objects from mongo
    bsondata = store.find({"silo_id": int(id)})
    # Now convert bson to json string using OrderedDict to main fields order
    json_string = dumps(bsondata)
    # Now decode the json string into python object
    silo_data = json.loads(json_string, object_pairs_hook=OrderedDict)
    data = []
    num_cols = 0
    cols = OrderedDict()
    if silo_data:
        num_rows = len(silo_data)

        for row in silo_data:
            for i, col in enumerate(row):
                if col not in cols.keys():
                    num_cols += 1
                    col = col.decode("latin-1").encode("utf8")
                    cols[col] = num_cols

        # Convert OrderedDict to Python list so that it can be written to CSV writer.
        cols = list(cols)
        writer.writerow(list(cols))

        # Populate a 2x2 list structure that corresponds to the number of rows and cols in silo_data
        for i in xrange(num_rows): data += [[0]*num_cols]

        for r, row in enumerate(silo_data):
            for col in row:
                # Map values to column names and place them in the correct position in the data array
                val = row[col]
                if isinstance(val, OrderedDict): val  = val.popitem()
                if isinstance(val, tuple):
                    if val[0] == "$date": val = smart_text(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(val[1]/1000)))
                    if val[0] == "$oid": val = smart_text(val[1])
                #val = val.decode("latin-1").encode("utf8")
                val = smart_text(val).decode("latin-1").encode("utf8")
                data[r][cols.index(col)] = val
            writer.writerow(data[r])
    return response

@login_required
def anonymizeTable(request, id):
    lvs = db.label_value_store.find({"silo_id": int(id)})
    piif_cols = PIIColumn.objects.values_list("fieldname",flat=True).order_by('fieldname')
    fields_to_remove = {}
    for row in lvs:
        for k in row:
            if k in piif_cols:
                if k == "_id" or k == "silo_id" or k == "create_date" or k == "edit_date": continue
                fields_to_remove[str(k)] = ""

    if fields_to_remove:
        res = db.label_value_store.update_many({"silo_id": int(id)}, { "$unset": fields_to_remove})
        messages.success(request, "Table has been annonymized! But do review it again.")
    else:
        messages.info(request, "No PIIF columns were found.")

    return HttpResponseRedirect(reverse_lazy('siloDetail', kwargs={'silo_id': id}))


@login_required
def identifyPII(request, silo_id):
    """
    Identifying Columns with Personally Identifiable Information (PII)
    """
    if request.method == 'GET':
        columns = []
        lvs = db.label_value_store.find({"silo_id": int(silo_id)})
        for d in lvs:
            columns.extend([k for k in d.keys() if k not in columns])
        return render(request, 'display/annonymize_columns.html', {"silo_id": silo_id, "columns": columns})

    columns = request.POST.getlist("cols[]")

    for i, c in enumerate(columns):
        col, created = PIIColumn.objects.get_or_create(fieldname=c, defaults={'owner': request.user})

    return JsonResponse({"status":"success"})
