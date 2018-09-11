import datetime
import time
import requests
import csv
import base64
import re
import logging
import json
from collections import OrderedDict
from requests.auth import HTTPDigestAuth
import tempfile
import uuid

from pymongo import MongoClient

from django.conf import settings
from django.core import files
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponseBadRequest,\
    HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.encoding import smart_str, smart_text
from django.db.models import Q
from django.views.decorators.csrf import csrf_protect
from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin

from gviews_v4 import import_from_gsheet_helper
from silo.custom_csv_dict_reader import CustomDictReader
from tola.util import importJSON, save_data_to_silo, getSiloColumnNames, \
    parseMathInstruction, calculateFormulaColumn, makeQueryForHiddenRow, \
    getNewestDataDate, addColsToSilo, deleteSiloColumns, hideSiloColumns,  \
    getCompleteSiloColumnNames, setSiloColumnType, getColToTypeDict

from commcare.tasks import fetchCommCareData
from .serializers import *
from .models import Silo, Read, ReadType, ThirdPartyTokens, LabelValueStore, \
    Tag, UniqueFields, MergedSilosFieldMapping, TolaSites, PIIColumn, \
    DeletedSilos, FormulaColumn, CeleryTask
from .forms import get_read_form, UploadForm, SiloForm, MongoEditForm, \
    NewColumnForm, EditColumnForm, OnaLoginForm
from .tasks import process_silo

from django.contrib.contenttypes.models import ContentType
from social_django.models import UserSocialAuth
from tola.activity_proxy import get_workflowlevel1s

logger = logging.getLogger("silo")
client = MongoClient(settings.MONGO_URI)
db = client.get_default_database()
ROLE_VIEW_ONLY = 'ViewOnly'


class IndexView(LoginRequiredMixin, View):
    template_name = 'index.html'

    def _get_context_data(self, request):
        # Because of the M2M 'tags' field we can't make it more performant
        # selecting just the values we want.
        silos_user = list(Silo.objects.prefetch_related('tags', 'shared').\
            filter(owner=request.user))
        silos_user_public_total = len([s for s in silos_user if s.public])
        silos_user_shared_total = len([s for s in silos_user if s.shared.all()])
        silos_public = Silo.objects.prefetch_related('tags').filter(public=1).\
            exclude(owner=request.user)
        readtypes = ReadType.objects.all().values_list('read_type', flat=True)
        # tags = Tag.objects.filter(owner=request.user).\
        #            annotate(times_tagged=Count('silos')).\
        #            values('name', 'times_tagged').order_by('-times_tagged')[:8]
        site_name = TolaSites.objects.values_list('name', flat=True).get(site_id=1)

        context = {
            'silos_user': silos_user,
            'silos_user_public_total': silos_user_public_total,
            'silos_user_shared_total': silos_user_shared_total,
            'silos_public': silos_public,
            'readtypes': readtypes,
            # 'tags': tags,
            'site_name': site_name,
        }
        return context

    def get(self, request, *args, **kwargs):
        context = self._get_context_data(request)
        response = render(request, self.template_name, context)
        if (request.COOKIES.get('auth_token', None) is None and
                request.user.is_authenticated):
            response.set_cookie('auth_token', request.user.auth_token)
        # if logged in redirect user to there list of tables
        return redirect('/silos')


def tablesLogin(request):
    return render(request, 'tables_login.html')


# fix now that not all mongo rows need to have the same column
def merge_two_silos(mapping_data, lsid, rsid, msid):
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
        msg = "Right Silo does not exist: silo_id=%s" % rsid
        logger.error(msg)
        return {'status': "danger",  'message': msg}

    # retrieve the merged silo
    try:
        msilo = Silo.objects.get(pk=msid)
        merged_cols.sort()
        addColsToSilo(msilo, merged_cols)
    except Silo.DoesNotExist as e:
        msg = "Merged Silo does not exist: silo_id=%s" % msid
        logger.error(msg)
        return {'status': "danger",  'message': msg}

    # retrieve the unique fields set for the right silo
    r_unique_fields = rsilo.unique_fields.all()

    if not r_unique_fields:
        msg = "The silo, [%s], must have a unique column and it should be " \
              "the same as the one specified in [%s] silo." % (rsilo.name,
                                                               lsilo.name)
        logger.error(msg)
        return {'status': "danger",  'message': msg}

    # retrieve the unique fields of the merged_silo
    m_unique_fields = msilo.unique_fields.all()

    # make sure that the unique_fields from right table are in the merged_table
    # by adding them to the merged_cols array.
    for uf in r_unique_fields:
        if uf.name not in merged_cols: merged_cols.append(uf.name)

        # make sure to set the same unique_fields in the merged_table
        if not m_unique_fields.filter(name=uf.name).exists():
            UniqueFields.objects.get_or_create(
                name=uf.name, silo=msilo,
                defaults={"name": uf.name, "silo": msilo})

    # Get the correct set of data from the right table
    for row in r_silo_data:
        merged_row = OrderedDict()
        for k in row:
            # Skip over those columns in the right table that
            # shouldn't be in the merged_table
            if k not in merged_cols: continue
            merged_row[k] = row[k]

        # now set its silo_id to the merged_table id
        merged_row["silo_id"] = msid
        merged_row["create_date"] = timezone.now()

        filter_criteria = {}
        for uf in r_unique_fields:
            try:
                filter_criteria.update({str(uf.name): merged_row[uf.name]})
            except KeyError as e:
                # when this exception occurs, it means that the col identified
                # as the unique_col is not present in
                # all rows of the right_table
                logger.warning("The field, %s, is not present in table id=%s"
                               % (uf.name, rsid))

        # adding the merged_table_id because the filter criteria should
        # search the merged_table
        filter_criteria.update({'silo_id': msid})

        # this is an upsert operation.; note the upsert=True
        db.label_value_store.update_one(filter_criteria,
                                        {"$set": merged_row}, upsert=True)

    # Retrieve the unique_fields set by left table
    l_unique_fields = lsilo.unique_fields.all()
    if not l_unique_fields:
        msg = "The silo, [%s], must have a unique column and it should be " \
              "the same as the one specified in [%s] silo."\
              % (lsilo.name, rsilo.name)
        logger.error(msg)
        return {'status': "danger",  'message': msg}

    for uf in l_unique_fields:
        # if there are unique fields that are not in the right table
        # then show error
        if not r_unique_fields.filter(name=uf.name).exists():
            msg = "Both silos (%s, %s) must have the same column set as " \
                  "unique fields" % (lsilo.name, rsilo.name)
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

            # if merge_type is specified then there must be multiple columns
            # in the left_cols array
            if merge_type:
                mapped_value = ''
                for col in left_cols:
                    if merge_type == 'Sum' or merge_type == 'Avg':
                        try:
                            if mapped_value == '':
                                mapped_value = float(row[col])
                            else:
                                mapped_value = float(mapped_value) \
                                               + float(row[col])
                        except Exception as e:
                            msg = 'Failed to apply %s to column, %s : %s '\
                                  % (merge_type, col, e.message)
                            logger.error(msg)
                            return {'status': "danger",  'message': msg}
                    else:
                        mapped_value += ' ' + smart_str(row[col])

                # Now calculate avg if the merge_type was actually "Avg"
                if merge_type == 'Avg':
                    mapped_value = mapped_value / len(left_cols)
            # only one col in left table is mapped to one col
            #  in the right table.
            else:
                col = str(left_cols[0])
                if col == "silo_id": continue
                try:
                    mapped_value = row[col]
                except KeyError as e:
                    # When updating data in merged_table at a later time, it is
                    # possible the original source tables may have had some
                    # columns removed in which we might get a KeyError so in
                    # that case we just skip it.
                    continue

            # right_col is used as in index of merged_row because one or more
            #  left cols map to one col in right table
            merged_row[right_col] = mapped_value

        # Get data from left unmapped columns:
        for col in l_unmapped_cols:
            if col in row:
                merged_row[col] = row[col]

        filter_criteria = {}
        for uf in l_unique_fields:
            try:
                filter_criteria.update({str(uf.name): merged_row[uf.name]})
            except KeyError:
                # when this exception occurs, it means that the col identified
                # as the unique_col is not present in all rows of the left_table
                msg = "The field, %s, is not present in table id=%s"\
                      % (uf.name, lsid)
                logger.warning(msg)

        filter_criteria.update({'silo_id': msid})

        # override the silo_id and create_date columns values to make sure
        # they're not set to the values that are in left table or right table
        merged_row["silo_id"] = msid
        merged_row["create_date"] = timezone.now()

        # Now update or insert a row if there is no matching record available
        db.label_value_store.update_one(filter_criteria,
                                        {"$set": merged_row}, upsert=True)

    return {'status': "success",  'message': "Merged data successfully"}


# fix now that not all mongo rows need to have the same column
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
        merged_cols.sort()
        addColsToSilo(msilo, merged_cols)
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
    return {'status': "success",  'message': "Appended data successfully"}


# Edit existing silo meta data
@csrf_protect
@login_required
def edit_silo(request, id):
    """
    Edit the meta data and description for each Table (silo)
    :param request:
    :param id: Unique table ID
    :return: silo edit form
    """

    edited_silo = Silo.objects.get(pk=id)
    user_wfl1s = get_workflowlevel1s(request.user)
    request_user_org = None
    owner_user_org = None

    if(hasattr(request.user, 'tola_user') and
            hasattr(edited_silo.owner, 'tola_user')):
        request_user_org = request.user.tola_user.organization
        owner_user_org = edited_silo.owner.tola_user.organization

    is_silo_shared_with_user = Silo.objects.filter(
        Q(pk=id, shared__id=request.user.pk) |
        Q(pk=id, workflowlevel1__level1_uuid__in=user_wfl1s)).exists()

    if not (edited_silo.owner == request.user or edited_silo.public
            or is_silo_shared_with_user
            or (edited_silo.share_with_organization
                and request_user_org == owner_user_org)):
        return render(request, '404.html', status=404)

    if request.method == 'POST':  # If the form has been submitted...
        tags = request.POST.getlist('tags')
        post_data = request.POST.copy()

        if tags:
            post_data.pop('tags')

        for i, t in enumerate(tags):
            if t.isdigit():
                post_data.appendlist('tags', t)
            else:
                tag, created = Tag.objects.get_or_create(
                    name=t, defaults={'owner': request.user})
                if created:
                    tags[i] = tag.id

                post_data.appendlist('tags', tag.id)

        form = SiloForm(user=request.user, data=post_data,
                        instance=edited_silo)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect('/silos/')
        else:
            messages.error(request, 'Invalid Form', fail_silently=False)
    else:
        form = SiloForm(user=request.user, instance=edited_silo)
    return render(request, 'silo/edit.html', {
        'form': form, 'silo_id': id, "silo": edited_silo,
    })


@login_required
def saveAndImportRead(request):
    """
    Saves ONA read if not already in the db and then imports its data
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("HTTP method, {}, is not supported".
                                      format(request.method))

    read_type = ReadType.objects.get(read_type="ONA")
    name = request.POST.get('read_name', None)
    url = request.POST.get('read_url', None)
    silo_name = request.POST.get('silo_name', None)
    owner = request.user
    description = request.POST.get('description', None)
    provider = 'ONA'

    # Fetch the data from ONA
    ona_token = ThirdPartyTokens.objects.get(user=request.user, name=provider)
    header = {
        'Authorization': 'Token {}'.format(ona_token.token)
    }
    response = requests.get(url, headers=header)
    data = json.loads(response.content)

    if len(data) == 0:
        return HttpResponse('There is not data for the selected form, '
                            '{}'.format(name))

    try:
        silo_id = int(request.POST.get('silo_id', None))
        if silo_id == 0:
            silo_id = None
    except Exception as e:
        return HttpResponse('Silo ID can only be an integer')

    try:
        read, read_created = Read.objects.get_or_create(
            read_name=name,
            owner=owner,
            defaults={
                'read_url': url,
                'type': read_type,
                'description': description
            }
        )
        if read_created:
            read.save()
    except Exception as e:
        return HttpResponse('Invalid name and/or URL')

    silo, silo_created = Silo.objects.get_or_create(
        id=silo_id,
        defaults={
            'name': silo_name,
            'public': False,
            'owner': owner
        }
    )

    if silo_created or read_created:
        silo.reads.add(read)
    elif read not in silo.reads.all():
        silo.reads.add(read)

    # import data into this silo
    save_data_to_silo(silo, data, read, request.user)
    silo_detail_url = reverse_lazy('silo_detail', args=[silo.pk])
    return HttpResponse(silo_detail_url)


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
    has_data = False
    url_user_token = "https://api.ona.io/api/v1/user.json"
    url_user_forms = 'https://api.ona.io/api/v1/data'
    if request.method == 'POST':
        form = OnaLoginForm(request.POST)
        if form.is_valid():
            response = requests.get(url_user_token, auth=HTTPDigestAuth(
                request.POST['username'], request.POST['password']))
            if response.status_code == 401:
                messages.error(request, "Invalid username or password.")
            elif response.status_code == 200:
                auth_success = True
                token = json.loads(response.content)['api_token']
                ona_token, created = ThirdPartyTokens.objects.get_or_create(
                    user=request.user, name=provider, token=token)
                if created:
                    ona_token.save()
            else:
                messages.error(request, "A {} error has occured: {} ".format(
                    response.status_code, response.text))
    else:
        try:
            auth_success = True
            ona_token = ThirdPartyTokens.objects.get(name=provider,
                                                     user=request.user)
        except Exception as e:
            auth_success = False
            form = OnaLoginForm()

    if ona_token and auth_success:
        header = {
                'Authorization': 'Token {}'.format(ona_token.token)
        }
        onaforms = requests.get(url_user_forms, headers=header)
        data = json.loads(onaforms.content)
        # check for records (very slow) may need to cache somehow or
        # request count from Ona API endpoint
        for x in data:
            data_count = 0
            ona_data = requests.get(x['url'], headers=header)
            data_to_count = json.loads(ona_data.content)
            # check for existing read source
            try:
                check_read = Read.objects.all().filter(read_url=x['url'])
                if check_read:
                    x['silo'] = check_read
            except Read.DoesNotExist:
                x['silo'] = None
            # do count
            for y in data_to_count:
                data_count = data_count + 1
            x['count'] = data_count
        if data:
            has_data = True

    silos = Silo.objects.filter(owner=request.user)
    return render(request, 'silo/getonaforms.html', {
        'form': form, 'data': data, 'silos': silos, 'has_data': has_data
    })


@login_required
def providerLogout(request,provider):

    ona_token = ThirdPartyTokens.objects.get(user=request.user, name=provider)
    ona_token.delete()

    messages.error(request, "You have been logged out of your Ona account.  Any Tables you have created with this account ARE still available, but you must log back in here to update them.")
    return HttpResponseRedirect(request.META['HTTP_REFERER'])


# DELETE-SILO
@csrf_protect
def deleteSilo(request, id):
    owner = Silo.objects.get(id = id).owner

    if str(owner.username) == str(request.user):
        try:
            silo_to_be_deleted = Silo.objects.get(pk=id)
            silo_name = silo_to_be_deleted.name
            DeletedSilos.objects.get_or_create(user=request.user,\
                                            deleted_time=timezone.now(),\
                                            silo_name_id=silo_name+" with id "+id,\
                                            silo_description=silo_to_be_deleted.description)
            lvs = LabelValueStore.objects(silo_id=silo_to_be_deleted.id)
            num_rows_deleted = lvs.delete()

            #look through each of the reads and delete them if this was their only silo
            reads = silo_to_be_deleted.reads.all()
            for read in reads:
                if Silo.objects.filter(reads__pk=read.id).count() == 1:
                    read.delete()

            silo_to_be_deleted.delete()
            messages.success(request, "Silo, %s, with all of its %s rows of data deleted successfully." % (silo_name, num_rows_deleted))

        except Silo.DoesNotExist as e:
            print(e)
        #except Exception as es:
            #print(es)
        return HttpResponseRedirect("/silos")
    else:
        messages.error(request, "You do not have permission to delete this silo")
        return HttpResponseRedirect(request.META['HTTP_REFERER'])


@login_required
def showRead(request, id):
    """
    Show a read data source and allow user to edit it
    """
    excluded_fields = ['gsheet_id', 'resource_id', 'token', 'create_date',
                       'edit_date', 'token', 'autopush_expiration',
                       'autopull_expiration']
    initial = {'owner': request.user}
    data = None
    onedrive_redirect_uri = settings.ONEDRIVE_REDIRECT_URI
    onedrive_client_id = settings.ONEDRIVE_CLIENT_ID

    try:
        read_instance = Read.objects.get(pk=id)
        read_type = read_instance.type.read_type
    except Read.DoesNotExist as e:
        read_instance = None
        if request.method == 'POST':
            read_type_id = request.POST.get("type")
            rt = ReadType.objects.get(id=read_type_id)
        else:
            read_type_name = request.GET.get("type", "CSV")
            rt = ReadType.objects.get(read_type=read_type_name)

        initial['type'] = rt
        read_type = rt.read_type

    try:
        get_tables = Silo.objects.all().filter(reads__id=id)
    except Silo.DoesNotExist:
        get_tables = None

    if read_type == "GSheet Import" or read_type == "ONA":
        excluded_fields = excluded_fields + ['username', 'password',
                                             'file_data',
                                             'autopush_frequency',
                                             'onedrive_access_token',
                                             'onedrive_file']
    elif read_type == "JSON":
        excluded_fields = excluded_fields + ['file_data',
                                             'onedrive_access_token',
                                             'onedrive_file',
                                             'autopush_frequency']
    elif read_type == "Google Spreadsheet":
        excluded_fields = excluded_fields + ['username', 'password',
                                             'file_data',
                                             'autopull_frequency',
                                             'onedrive_access_token',
                                             'onedrive_file']
    elif read_type == "CSV":
        excluded_fields = excluded_fields + ['username', 'password',
                                             'autopush_frequency',
                                             'autopull_frequency',
                                             'read_url',
                                             'onedrive_access_token',
                                             'onedrive_file']
    elif read_type == "OneDrive":
        excluded_fields = excluded_fields + ['username', 'password',
                                             'file_data',
                                             'autopush_frequency',
                                             'autopull_frequency', 'read_url']

    if request.method == 'POST':
        form = get_read_form(excluded_fields)(request.POST, request.FILES,
                                              instance=read_instance)

        if form.is_valid():
            read = form.save(commit=False)
            if read.username and read.password:
                basic_auth = base64.encodestring('%s:%s' % (read.username,
                                                            read.password)
                                                 )[:-1]
                read.token = basic_auth
                read.password = None
            if form.instance.autopull_frequency:
                read.autopull_expiration = datetime.datetime.now() + \
                                           datetime.timedelta(days=170)
            if form.instance.autopush_frequency:
                read.autopush_expiration = datetime.datetime.now() + \
                                           datetime.timedelta(days=170)

            read.save()
            if form.instance.type.read_type == "CSV":
                return HttpResponseRedirect("/file/" + str(read.id) + "/")
            elif form.instance.type.read_type == "JSON":
                return HttpResponseRedirect(reverse_lazy("getJSON") +
                                            "?read_id=%s" % read.id)
            if form.instance.type.read_type == "OneDrive":
                extra_data = {"token_type": "Bearer", "access_token":
                    form.cleaned_data["onedrive_access_token"]}

                social_auth, created = UserSocialAuth.objects.get_or_create(
                        provider='microsoft-graph', user=request.user)
                social_auth.extra_data = extra_data
                social_auth.uid = str(uuid.uuid4())
                social_auth.save()

                return HttpResponseRedirect("/import_onedrive/" + str(
                    read.id) + "/")

            if form.instance.autopull_frequency or \
                    form.instance.autopush_frequency:
                messages.info(request,
                              "Your table must have a unique column set for "
                              "Autopull/Autopush to work.")
            return HttpResponseRedirect(reverse_lazy('list_silos'))
        else:
            messages.error(request, 'Invalid Form', fail_silently=False)
    else:
        form = get_read_form(excluded_fields)(instance=read_instance,
                                              initial=initial)

    return render(request, 'read/read.html', {
        'form': form,
        'read_id': id,
        'data': data,
        'get_tables': get_tables,
        'redirect_uri': onedrive_redirect_uri,
        'client_id': onedrive_client_id,
    })


@login_required
def oneDriveImport(request, id):
    """
    Import a file from OneDrive
    :param request:
    :return: HttpResponseRedirect to the imported file
    """
    read_obj = Read.objects.get(pk=id)

    user = User.objects.get(username__exact=request.user)
    social = user.social_auth.get(provider='microsoft-graph')
    access_token = social.extra_data['access_token']

    request_meta = requests.get(
        'https://graph.microsoft.com/v1.0/me/drive/items/' +
        read_obj.onedrive_file,
        headers={
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json',
            'Authorization': 'Bearer ' + access_token
        }
    )
    if request_meta.status_code == 401:
        logout(request)
        return redirect('/')

    request_content = requests.get(
        'https://graph.microsoft.com/v1.0/me/drive/items/' +
        read_obj.onedrive_file+'/content',
        headers={
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json',
            'Authorization': 'Bearer ' + access_token
        }
    )
    file_content = request_content.content
    file_meta = request_meta.json()
    tmp = tempfile.NamedTemporaryFile()
    tmp.write(file_content)

    read_obj.file_data = files.File(tmp, name=file_meta["name"])
    read_obj.save()

    return HttpResponseRedirect("/file/" + str(id) + "/")


@login_required
def oneDrive(request):
    """
    Get the forms owned or shared with the logged in user
    :param request:
    :return: list of Ona forms paired with action buttons
    """
    return render(request, 'silo/onedrive.html', {})


@login_required
def uploadFile(request, id):
    """
    Upload CSV file and save its data
    """
    if request.method == 'POST':
        form = UploadForm(request.POST)
        if form.is_valid():
            read_obj = Read.objects.get(pk=id)
            user = User.objects.get(username__exact=request.user)
            if request.POST.get("new_silo", None):
                silo = Silo(name=request.POST['new_silo'], owner=user,
                            public=False, create_date=timezone.now())
                silo.save()
            else:
                silo = Silo.objects.get(id = request.POST["silo_id"])

            silo.reads.add(read_obj)
            silo_id = silo.id

            task = CeleryTask.objects.create(task_id=None,
                              task_status=None,
                              content_object=read_obj)

            async_res = process_silo.apply_async(
                        (silo.id, read_obj.id)
            )

            task.task_id = async_res.id
            task.task_status = CeleryTask.TASK_CREATED
            task.save()

            return HttpResponseRedirect('/silo_detail/' + str(silo_id) + '/')
        else:
            messages.error(request, "There was a problem with reading the contents of your file" + form.errors)

    user = User.objects.get(username__exact=request.user)
    # get all of the silo info to pass to the form
    get_silo = Silo.objects.filter(owner=user)

    # display the form for user to choose a table or enter a new table name to import data into
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


def toggle_silo_publicity(request):
    silo_id = request.GET.get('silo_id', None)
    silo = Silo.objects.get(pk=silo_id)

    if silo.owner == request.user:
        silo.public = not silo.public
        silo.save()
        return HttpResponse('Your change has been saved', status=200)
    else:
        return HttpResponse('You can not  change publicity of this table',
                            status=403)


# SILOS
@login_required
def list_silos(request):
    """
    Each silo is listed with links to details
    """
    user = User.objects.get(username__exact=request.user)
    user_wfl1s = get_workflowlevel1s(user)

    # get all of the silos
    own_silos = Silo.objects.filter(owner=user).prefetch_related('reads')

    shared_silos = Silo.objects.filter(
        Q(shared__id=user.pk) |
        Q(share_with_organization=True,
          owner__tola_user__organization=user.tola_user.organization) |
        Q(workflowlevel1__level1_uuid__in=user_wfl1s)).\
        exclude(owner=user).prefetch_related("reads")

    public_silos = Silo.objects.filter(
        Q(public=True) & ~Q(owner=user)).prefetch_related("reads")

    return render(request,
                  'display/silos.html',
                  {
                      'own_silos':own_silos,
                      "shared_silos": shared_silos,
                      "public_silos": public_silos
                  })


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

                # The partialFilterExpression flag is not available until MongoDB 3.2.
                # The exception should probably eventually be made more specific (i.e. for maxed out indexes)
                # try:
                #     db.label_value_store.create_index(col, partialFilterExpression = {'silo_id' : silo.id})
                # except Exception as e:
                #     logger.warning("Failed to create a unique column index: %s" % (e))

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

    return HttpResponseRedirect(reverse_lazy('silo_detail', kwargs={'silo_id': silo_id}))


@login_required
def silo_detail(request, silo_id):
    """
    Silo Detail
    """

    silo = Silo.objects.get(pk=silo_id)
    user_wfl1s = get_workflowlevel1s(request.user)
    cols = []
    query = makeQueryForHiddenRow(json.loads(silo.rows_to_hide))

    """
    Note:    There is a chance a service gets stuck in "tasks_running" if a
    service worker terminates unexpectedly and the task id
    could not be removed from the task.
    """

    tasks_running = Read.objects.filter(
        silos=silo.id,
        tasks__task_status__in=[CeleryTask.TASK_CREATED,
                                CeleryTask.TASK_IN_PROGRESS]).count()

    tasks_failed = Read.objects.filter(
        silos=silo.id,
        tasks__task_status=CeleryTask.TASK_FAILED).count()

    silo_read_ids = Read.objects.filter(silos=silo.id).values_list('id',
                                                                   flat=True)

    celery_tasks = CeleryTask.objects.filter(
        object_id__in=silo_read_ids,
        content_type=ContentType.objects.get_for_model(Read)
    ).values_list('object_id', 'task_id', 'task_status')

    tasks = map(
        lambda t: {'read_id': t[0], 'task_id': t[1], 'task_status': t[2]},
        celery_tasks
    )

    request_user_org = None
    owner_user_org = None
    if hasattr(request.user, 'tola_user') and hasattr(silo.owner, 'tola_user'):
        request_user_org = request.user.tola_user.organization
        owner_user_org = silo.owner.tola_user.organization

    is_silo_shared_with_user = Silo.objects.filter(
        Q(pk=silo_id, shared__id=request.user.pk) |
        Q(pk=silo_id, workflowlevel1__level1_uuid__in=user_wfl1s)).exists()

    if (silo.owner == request.user or silo.public
            or is_silo_shared_with_user
            or (silo.share_with_organization
                and request_user_org == owner_user_org)):
        cols.append('_id')
        cols.append('id')
        cols.extend(getSiloColumnNames(silo_id))
    else:
        messages.error(request,
                       "You do not have permission to view this table.")
    return render(
        request,
        "display/silo.html",
        {
            "silo": silo,
            "cols": cols,
            "query": query,
            "tasks_running": tasks_running,
            "tasks_failed": tasks_failed,
            "tasks": tasks
        }
    )


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
            #if the data table is merged then updating means trying to remerge to get updated data
            left_table_id = merged_silo_mapping.from_silo.pk
            right_table_id = merged_silo_mapping.to_silo.pk
            merge_table_id = merged_silo_mapping.merged_silo.pk
            mapping = merged_silo_mapping.mapping
            mergeType = merged_silo_mapping.merge_type

            if mergeType == "merge":
                res = merge_two_silos(mapping, left_table_id, right_table_id, merge_table_id)
            else:
                res = appendTwoSilos(mapping, left_table_id, right_table_id, merge_table_id)
            if res['status'] == "success":
                messages.success(request, res['message'])
            else:
                messages.error(request, res['message'])
        except MergedSilosFieldMapping.DoesNotExist as e:
            #get a list of reads from the silo
            reads = silo.reads.all()
            data = [[],[]]
            msgs = []
            sources_to_delete = []

            #Get data from each of the reads and store it as the appropriate array
            for read in reads:
                import_response = importDataFromRead(request,silo,read)
                if import_response[2]:
                    msgs.append(import_response[2])
                if import_response[1] == 1:
                    data[1].append(import_response[0])
                    data[0].append(read)
                    sources_to_delete.append(read.id)


            #from ones where we got data delete those records
            unique_field_exist = silo.unique_fields.exists()
            #Unique field means keep the data and update as necessary (which is already implimented so its not necessary to delete anything)
            if  unique_field_exist == False:
                lvs = LabelValueStore.objects(silo_id=silo.pk,__raw__={"read_id" : { "$exists" : "true", "$in" : sources_to_delete }})
                lvs.delete()

            #put in the new records
            for x in range(0,len(data[0])):
                for entry in data[1][x]:
                    save_data_to_silo(silo,entry,data[0][x],request.user)
            for read in reads:
                if read.type.read_type == "GSheet Import":
                    greturn = import_from_gsheet_helper(request.user, silo.id, None, read.resource_id, None, True)
                    if type(greturn) == tuple:
                        greturn[1][:] = [d for d in greturn[1] if d.get('silo_id') == None]
                        for ret in greturn[1]:
                            msgs.append((ret.get('level'),ret.get('msg')))
                        #delete data associated with old read if there's no unique column
                        if unique_field_exist == False:
                            lvss_to_delete = LabelValueStore.objects(silo_id=silo.pk,__raw__={"read_id" : { "$exists" : "true", "$in" : [read.id] }})
                            lvss_to_delete.delete()
                        #read the data
                        for lvs in greturn[0]:
                            lvs.save()
                    else:
                        greturn[:] = [d for d in greturn if d.get('silo_id') == None]
                        for ret in greturn:
                            if ret.get('level') == messages.SUCCESS:
                                msgs.append((ret.get('level'),"Google spreadsheet has been successfully updated"))
                            else:
                                msgs.append((ret.get('level'),ret.get('msg')))
            for msg in msgs:
                messages.add_message(request, msg[0], msg[1])

            #delete legacy objects
            lvss = LabelValueStore.objects(silo_id=silo.pk,__raw__={ "$or" : [{"read_id" : {"$not" : { "$exists" : "true" }}}, {"read_id" : {"$in" : [-1,""]} } ]})

    return HttpResponseRedirect(reverse_lazy('silo_detail', kwargs={'silo_id': pk},))


#return tuple: (list of list of dictionaries[[{}]] data, 0=falure 1=success 2=N/A, messages)
def importDataFromRead(request, silo, read):
    if read.type.read_type == "ONA":
        ona_token = ThirdPartyTokens.objects.get(user=silo.owner.pk, name="ONA")
        response = requests.get(read.read_url, headers={'Authorization': 'Token %s' % ona_token.token})
        data = json.loads(response.content)
        return ([data], 1, (messages.SUCCESS, "ONA has been successfully updated"))
    elif read.type.read_type == "CSV":
        return (None,2,(messages.INFO, "When updating data in a table, its CSV source is ignored."))
    elif read.type.read_type == "JSON":
        if read.read_url != "":
            data = importJSON(read, request.user, None, None, silo.pk, None, True)
            #messages.add_message(request, result[0], result[1])
            if data:
                return ([data],1,(messages.SUCCESS, "Your JSON feed has been successfully updated"))
            return (None,0,(messages.ERROR, "Their was an error with updating yoru JSON feed data"))
        else:
            return (None,2,(messages.INFO, "When updating data in a table, its JSON file data is ignored."))
    elif read.type.read_type == "GSheet Import":
        #as the google sheet import already performs the update functionality so when its time to input the data again google spreadsheet update will be called
        return (None,2,None)
    elif read.type.read_type == "Google Spreadsheet":
        #as the google sheet import already performs the update functionality so when its time to input the data again google spreadsheet update will be called
        return (None,2,None)
    elif read.type.read_type == "CommCare":
        commcare_token = None
        try:
            commcare_token = ThirdPartyTokens.objects.get(user=silo.owner.pk, name="CommCare")
        except Exception as e:
            return (None,0,(messages.ERROR, "You need to login to commcare using an API Key to access this functionality"))
        last_data_retrieved = str(getNewestDataDate(silo.id))[:10]
        url = "/".join(read.read_url.split("/")[:8]) + "?date_modified_start=" + last_data_retrieved + "&" + "limit="
        response = requests.get(url+ str(1), headers={'Authorization': 'ApiKey %(u)s:%(a)s' % {'u' : commcare_token.username, 'a' : commcare_token.token}})
        if response.status_code == 401:
            commcare_token.delete()
            return (None,0,(messages.ERROR, "Your Commcare usernmane or API Key is incorrect"))
        elif response.status_code != 200:
            return (None,0,(messages.ERROR, "An error importing from commcare has occured: %s %s " % (response.status_code, response.text)))
        metadata = json.loads(response.content)
        if metadata['meta']['total_count'] == 0:
            return (None, 2, (messages.SUCCESS, "Your commcare data was already up to date"))
        #Now call the update data function in commcare tasks
        auth = {'Authorization': 'ApiKey %(u)s:%(a)s' % {'u' : commcare_token.username, 'a' : commcare_token.token}}
        url += "50"
        data_raw = fetchCommCareData(url, auth, True, 0, metadata['meta']['total_count'], 50, silo.id, read.id, True)
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

        columns = list(columns)
        addColsToSilo(silo, columns)
        hideSiloColumns(silo, columns)

        return (None,2,(messages.SUCCESS, "%i commcare records were successfully updated" % metadata['meta']['total_count']))
    else:
        return (None,0,(messages.ERROR,"%s does not support update data functionality. You will have to reinport the data manually" % read.type.read_type))


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
            addColsToSilo(silo, [label])
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


# Add a new column on to a silo
@login_required
def edit_columns(request, id):
    """
    FORM TO CREATE A NEW COLUMN FOR A SILO
    """
    silo = Silo.objects.get(id=id)
    to_delete = []

    if request.method == 'POST':
        data = getSiloColumnNames(id)
        # A form bound to the POST data
        form = EditColumnForm(request.POST or None, extra=data)
        if form.is_valid():  # All validation rules pass
            for label, value in form.cleaned_data.iteritems():
                # update the column name if it doesn't have delete in it
                if (not label.endswith('_delete') and str(label) != str(value)
                    and label != "silo_id" and label != "suds"
                        and label != "id"):
                    # update a column in the existing silo
                    db.label_value_store.update_many(
                        {
                            "silo_id": silo.id
                        },
                        {
                            "$rename": {label: value}
                        },
                        False
                    )
                    column_obj = json.loads(silo.columns)
                    for column in column_obj:
                        if column['name'] == label:
                            column['name'] = value
                            break
                    silo.columns = json.dumps(column_obj)
                    silo.save()
                # if we see delete then it's a check box to delete that column
                elif label.endswith('_delete') and value == 1:
                    column = label.replace("_delete", "")
                    db.label_value_store.update_many(
                        {
                            "silo_id": silo.id
                        },
                        {
                            "$unset": {column: value},
                        },
                        False
                    )
                    try:
                        silo.formulacolumns.filter(column).delete()
                    except Exception as e:
                        pass
                    to_delete.append(column)

            if len(to_delete):
                deleteSiloColumns(silo, to_delete)
            messages.info(request, 'Updates Saved', fail_silently=False)
            return HttpResponseRedirect(reverse_lazy(
                'silo_detail', kwargs={'silo_id': silo.id}))
        else:
            messages.error(request,
                           'ERROR: There was a problem with your request',
                           fail_silently=False)

    data = getSiloColumnNames(id)
    form = EditColumnForm(initial={'silo_id': silo.id}, extra=data)
    return render(request, "silo/edit-column-form.html",
                  {'silo': silo, 'form': form})


#Delete a column from a table silo
@login_required
def deleteColumn(request,id,column):
    """
    DELETE A COLUMN FROM A SILO
    """
    silo = Silo.objects.get(id=id)
    deleteSiloColumns(silo, [column])


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


# SHOW-MERGE FORM
@login_required
def mergeForm(request,id):
    """
    Merge different silos using a multistep column mapping form
    """
    getSource = Silo.objects.get(id=id)
    getSourceTo = Silo.objects.filter(owner=request.user)
    return render(request, "display/merge-form.html", {'getSource':getSource,'getSourceTo':getSourceTo})

# SHOW COLUMNS FOR MERGE FORM
def mergeColumns(request):
    """
    Step 2 in Merge different silos, map columns
    """
    from_silo_id = request.POST["from_silo_id"]
    to_silo_id = request.POST["to_silo_id"]

    getSourceFrom = getSiloColumnNames(from_silo_id)
    getSourceTo = getSiloColumnNames(to_silo_id)

    return render(request, "display/merge-column-form.html", {'getSourceFrom':getSourceFrom, 'getSourceTo':getSourceTo, 'from_silo_id':from_silo_id, 'to_silo_id':to_silo_id})


def do_merge(request):
    # get the table_ids.
    left_table_id = request.POST['left_table_id']
    right_table_id = request.POST['right_table_id']
    merge_type = request.POST.get('tableMergeType', None)
    merged_silo_name = request.POST['merged_table_name']

    if not merged_silo_name:
        merged_silo_name = 'Merging of {} and {}'.format(
            left_table_id, right_table_id)

    try:
        left_table = Silo.objects.get(id=left_table_id)
    except Silo.DoesNotExist:
        msg = 'Could not find the left table with id={}'.format(left_table_id)
        logger.info(msg)
        return JsonResponse({'status': 'danger', 'message': msg})

    try:
        right_table = Silo.objects.get(id=right_table_id)
    except Silo.DoesNotExist:
        msg = 'Could not find the right table with id={}'.format(
            right_table_id)
        logger.info(msg)
        return JsonResponse({'status': 'danger', 'message': msg})

    data = request.POST.get('columns_data', None)
    if not data:
        msg = 'No columns data passed'
        return JsonResponse({'status': 'danger', 'message': msg})

    # Create a new silo
    new_silo = Silo.objects.create(name=merged_silo_name, public=False,
                                   owner=request.user)
    left_table_reads = left_table.reads.values_list('id', flat=True).all()
    right_table_reads = right_table.reads.values_list('id', flat=True).all()
    new_silo.reads.add(*left_table_reads)
    new_silo.reads.add(*right_table_reads)
    merge_table_id = new_silo.pk

    if merge_type == 'merge':
        res = merge_two_silos(data, left_table_id,
                            right_table_id, merge_table_id)
    else:
        res = appendTwoSilos(
            data, left_table_id, right_table_id, merge_table_id
        )

    if res['status'] == 'danger':
        new_silo.delete()
        return JsonResponse(res)

    mapping = MergedSilosFieldMapping(
        from_silo=left_table, to_silo=right_table,
        merged_silo=new_silo, mapping=data, merge_type=merge_type)
    mapping.save()
    res.update({'silo_url': reverse_lazy(
        'silo_detail', kwargs={'silo_id': merge_table_id})})
    return JsonResponse(res)


# EDIT A SINGLE VALUE STORE
@login_required
def valueEdit(request,id):
    """
    Edit a value
    """
    doc = LabelValueStore.objects(id=id).to_json()
    data = {}
    jsondoc = json.loads(doc)
    silo_id = None
    silo = Silo.objects.get(pk=jsondoc[0].get('silo_id'))
    cols = json.loads(silo.columns)

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
                data[k] = v

        keys = item.keys()
        for col in cols:
            if col['name'] not in keys:
                data[col['name']] = None
    if request.method == 'POST': # If the form has been submitted...
        form = MongoEditForm(request.POST or None, extra = data, silo_pk=silo_id) # A form bound to the POST data
        if form.is_valid():
            lvs = LabelValueStore.objects(id=id)[0]
            for lbl, val in form.cleaned_data.iteritems():
                if lbl != "id" and lbl != "silo_id" and lbl != "csrfmiddlewaretoken":
                    setattr(lvs, lbl, val)
            lvs.edit_date = timezone.now()
            try:
                silo = Silo.objects.get(pk=silo_id)
                formula_columns = silo.formulacolumns.all()
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
            except Exception as e:
                messages.warning(request, "Data format error prevented tola tables from applying formula column to your data")
            lvs.save()
            return HttpResponseRedirect('/silo_detail/' + str(silo_id))
        else:
            print "not valid"
    else:
        form = MongoEditForm(initial={'silo_id': silo_id, 'id': id}, extra=data, silo_pk=silo_id)

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

    # get the query and the columns to export
    query = json.loads(request.GET.get('query', "{}"))
    cols = json.loads(request.GET.get('shown_cols', json.dumps(
        getSiloColumnNames(id))))

    # Loads the data from mongo
    data = LabelValueStore.objects(silo_id=int(id), **query).exclude(
        'create_date', 'edit_date', 'silo_id', 'read_id')

    # Sort the data and convert it into JSON
    sort = str(request.GET.get('sort', ''))
    data = data.order_by(sort)
    silo_data = json.loads(data.to_json())

    data = []
    num_cols = len(cols)
    if silo_data:
        num_rows = len(silo_data)

        # Convert OrderedDict to Python list so that it can be written to CSV writer.
        writer.writerow(cols)

        # Populate a 2x2 list structure that corresponds to the number of rows and cols in silo_data
        for i in xrange(num_rows):
            data += [[0]*num_cols]

        for r, row in enumerate(silo_data):
            for col in cols:
                # Map values to column names and place them in the correct position in the data array
                val = row.get(col, '')
                if isinstance(val, dict):
                    try:
                        val = smart_text(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(val['$date']/1000)))
                    except KeyError as e:
                        try:
                            val = smart_text(val['$oid'])
                        except KeyError as e:
                            val = val.popitem()

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

    return HttpResponseRedirect(reverse_lazy('silo_detail', kwargs={'silo_id': id}))


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


@login_required
def removeSource(request, silo_id, read_id):
    """
    removes a sources and unasociates its data
    """
    silo = None
    try:
        silo = Silo.objects.get(pk=silo_id)
    except Silo.DoesNotExist as e:
        messages.error(request,"Table with id=%s does not exist." % silo_id)
        return HttpResponseRedirect(reverse_lazy('list_silos'))

    try:
        read = silo.reads.get(pk=read_id)
        read_name = read.read_name
        silo.reads.remove(read)
        if Silo.objects.filter(reads__pk=read.id).count() == 0:
            read.delete()
        messages.success(request,"%s has been removed successfully" % read_name)
    except Read.DoesNotExist as e:
        messages.error(request,"Datasource with id=%s does not exist." % read_id)

    return HttpResponseRedirect(reverse_lazy('silo_detail', kwargs={'silo_id': silo_id},))


@login_required
def newFormulaColumn(request, pk):
    if request.method == 'POST':
        operation = request.POST.get("math_operation")
        cols = request.POST.getlist("columns")
        column_name = request.POST.get("column_name")
        silo = Silo.objects.get(pk=pk)

        if column_name == "":
            column_name = operation

        #now add the resutls to the mongodb database
        lvs = LabelValueStore.objects(silo_id=silo.pk)
        calc_result = calculateFormulaColumn(lvs,operation,cols,column_name)
        messages.add_message(request,calc_result[0],calc_result[1])

        if calc_result[0] == messages.ERROR:
            return HttpResponseRedirect(reverse_lazy('newFormulaColumn', kwargs={'pk': pk}))
        #now add the formula to the mysql database
        mapping = json.dumps(cols)
        (fcm, created) = FormulaColumn.objects.get_or_create(mapping=mapping,\
                                                operation=operation,\
                                                column_name=column_name)
        fcm.save()
        silo.formulacolumns.add(fcm)
        addColsToSilo(silo,[column_name], {column_name : 'float'})
        silo.save()

        return HttpResponseRedirect(reverse_lazy('silo_detail', kwargs={'silo_id': pk},))

    silo = Silo.objects.get(pk=pk)
    cols = getSiloColumnNames(pk)
    return render(request, "silo/add-formula-column.html", {'silo':silo,'cols': cols})


@login_required
def editColumnOrder(request, pk):
    if request.method == 'POST':
        try:
            #this is not done using utility functions since it is a complete replacement
            silo = Silo.objects.get(pk=pk)
            cols = []
            cols_list = request.POST.getlist("columns")
            col_types = getColToTypeDict(silo)
            for col in cols_list:
                cols.append({'name' : col, 'type': col_types.get(col,'string')})
            visible_cols_set = set(cols_list)

            cols.extend([x for x in json.loads(silo.columns) if (x if isinstance(x, basestring) else x['name']) not in visible_cols_set])
            silo.columns = json.dumps(cols)
            silo.save()

        except Silo.DoesNotExist as e:
            messages.error(request, "silo not found")
            return HttpResponseRedirect(reverse_lazy('list_silos'))


        return HttpResponseRedirect(reverse_lazy('silo_detail', kwargs={'silo_id': pk},))

    silo = Silo.objects.get(pk=pk)
    cols = getSiloColumnNames(pk)
    return render(request, "display/edit-column-order.html", {'silo':silo,'cols': cols})


@login_required
def addColumnFilter(request, pk):
    if request.method == 'POST':
        hide_cols = request.POST.get('hide_cols')
        hide_rows = request.POST.get('hide_rows')
        silo = Silo.objects.get(pk=pk)

        silo.hidden_columns = hide_cols
        silo.rows_to_hide = hide_rows

        silo.save()
        return HttpResponseRedirect(reverse_lazy('silo_detail', kwargs={'silo_id': pk},))


    silo = Silo.objects.get(pk=pk)
    cols = getCompleteSiloColumnNames(pk)

    hidden_cols = json.loads(silo.hidden_columns)
    hidden_rows = json.loads(silo.rows_to_hide)
    for row in hidden_rows:
        row['conditional'] = json.dumps(row['conditional'])

    cols.sort()
    return render(request, "display/add-column-filter.html", {'silo':silo,'cols': cols, 'hidden_cols': hidden_cols, 'hidden_rows': hidden_rows})


@login_required
def export_silo_form(request, id):

    if request.method == 'POST':
        query = makeQueryForHiddenRow(json.loads(request.POST.get('query')))
        shown_cols = request.POST.get('shown_cols')
        return HttpResponseRedirect(request.POST.get('url') +"?query=%s&shown_cols=%s" % (query, shown_cols))


    silo = Silo.objects.get(pk=id)
    cols = getCompleteSiloColumnNames(id)
    shown_cols = getSiloColumnNames(id)
    hidden_rows = json.loads(silo.rows_to_hide)
    for row in hidden_rows:
        row['conditional'] = json.dumps(row['conditional'])

    cols.sort()
    return render(request, "display/export_form.html", {'silo':silo,'cols': cols, 'shown_cols': shown_cols, 'hidden_rows': hidden_rows})


@login_required
def renewAutoJobs(request, read_pk, operation):
    read = Read.objects.get(pk=read_pk)
    if request.user != read.owner:
        #return not owner of import page
        return render(request, "display/read_renew.html", {'message' : 'You must be the owner of the import to renew it'})

    # when go to this url change the read expiration date to 170 days from now
    if operation == "pull" and read.autopull_frequency and (read.autopull_frequency == 'weekly' or read.autopull_frequency == 'daily'):
        read.autopull_expiration = datetime.datetime.now() + datetime.timedelta(days=170)
    elif operation == "push" and read.autopush_frequency and (read.autopush_frequency == 'weekly' or read.autopush_frequency == 'daily'):
        read.autopush_expiration = datetime.datetime.now() + datetime.timedelta(days=170)
    else:
        return render(request, "display/renew_read.html", {'message' : 'Error, auto%s renewal of %s is not a valid operation' % (operation, read.read_name)})
    read.save()

    return render(request, "display/renew_read.html", {'message' : 'Success, your renewal of %s auto%s was successful' % (read.read_name, operation)})


@login_required
def setColumnType(request, pk):
    #should only deal with post request since this will operate with a modal
    if request.method != 'POST':
        messages.error(request, '%s request is invalid' % request.method)
        return HttpResponseRedirect(reverse_lazy('silo_detail', kwargs={'silo_id': pk}))

    silo = Silo.objects.get(pk=pk)
    column = request.POST.get('column_for_type')
    col_type = request.POST.get('column_type')

    msg = setSiloColumnType(int(pk), column, col_type)
    messages.add_message(request, msg[0], msg[1])

    return HttpResponseRedirect(reverse_lazy('silo_detail', kwargs={'silo_id': pk},))
