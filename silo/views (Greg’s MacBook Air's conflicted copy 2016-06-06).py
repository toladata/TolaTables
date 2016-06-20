import datetime
import urllib2
import json
import base64
import csv
from operator import and_, or_
from collections import OrderedDict
from django.core.urlresolvers import reverse_lazy

from .forms import ReadForm, UploadForm, SiloForm, MongoEditForm, NewColumnForm, EditColumnForm
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.http import HttpResponseForbidden,\
    HttpResponseRedirect, HttpResponseNotFound, HttpResponseBadRequest,\
    HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render_to_response, get_object_or_404, redirect, render
from django.http import HttpResponse
from django.template import RequestContext, Context
from django.db import models
from django.shortcuts import render_to_response
from django.shortcuts import render
from django.db.models import Max, F, Q
from django.views.decorators.csrf import csrf_protect
import django_tables2 as tables
from django_tables2 import RequestConfig

from oauth2client.django_orm import Storage
from .models import GoogleCredentialsModel
from google_views import *
from .models import Silo, Read, ReadType, ThirdPartyTokens, LabelValueStore, Tag, UniqueFields, MergedSilosFieldMapping, TolaSites

from .tables import define_table
from tola.util import getSiloColumnNames

from django.contrib.auth.decorators import login_required
from tola.util import siloToDict, combineColumns

from django.core.urlresolvers import reverse

from django.utils import timezone
from django.utils.encoding import smart_str
from django.utils.encoding import smart_text




def mergeTwoSilos(data, left_table_id, right_table_id):
    columns_mapping = json.loads(data)

    left_unmapped_cols = columns_mapping.pop('left_unmapped_cols')
    right_unmapped_cols = columns_mapping.pop('right_unmapped_cols')

    merged_data = []

    left_table_data = LabelValueStore.objects(silo_id=left_table_id).to_json()
    left_table_data_json = json.loads(left_table_data)
    unique_cols = set()
    for row in left_table_data_json:
        merge_data_row = {}

        # Loop through the mapped_columns for each row in left_table.
        for k, v in columns_mapping.iteritems():
            merge_type = v['merge_type']
            left_cols = v['left_table_cols']
            right_col = v['right_table_col']

            # only the right_col is added to the unique_cols set because the left_columns are mapped to the right_col
            unique_cols.add(right_col)

            # if merge_type is specified then there must be multiple columns in the left_cols array
            if merge_type:
                mapped_value = ''
                for col in left_cols:
                    try:
                        if merge_type == 'Join':
                            mapped_value += ' ' + str(row[col])
                        elif merge_type == 'Sum' or merge_type == 'Avg':
                            try:
                                if mapped_value == '':
                                    mapped_value = float(row[col])
                                else:
                                    mapped_value = float(mapped_value) + float(row[col])
                            except Exception as e1:
                                return {"status": "danger", "message": "The value, %s, is not a numeric value." % mapped_value}
                        else:
                            pass
                    except Exception as e:
                        return {'status': "danger",  'message': 'Failed to apply %s to column, %s : %s ' % (merge_type, col, e.message)}

                if merge_type == 'Avg':
                    mapped_value = mapped_value / len(left_cols)

            # there is only a single column in left_cols array
            else:
                col = str(left_cols[0])
                mapped_value = row[col]

            # finally add the mapped_value to the merge_data_row
            merge_data_row[right_col] = mapped_value

        # Loop through the left_unmapped_columns for each row in left_table.
        for col in left_unmapped_cols:
            unique_cols.add(col)
            if col in row.keys():
                merge_data_row[col] = row[col]
            else:
                merge_data_row[col] = ''

        # Loop through all of the right_unmapped_cols for each row in left_table.
        for col in right_unmapped_cols:
            unique_cols.add(col)
            if col in row.keys():
                merge_data_row[col] = row[col]
            else:
                merge_data_row[col] = ''

        merge_data_row['left_table_id'] = left_table_id
        merge_data_row['right_table_id'] = right_table_id

        # add the complete row/object to the merged_data array
        merged_data.append(merge_data_row)

    # Get the right silo and append its data to merged_data array
    right_table_data = LabelValueStore.objects(silo_id=right_table_id).to_json()
    right_table_data_json = json.loads(right_table_data)
    for row in right_table_data_json:
        merge_data_row = {}
        for col in unique_cols:
            #print(row.keys())
            if col in row.keys():
                merge_data_row[col] = smart_str(row[col])
            else:
                merge_data_row[col] = ''

        merge_data_row['left_table_id'] = left_table_id
        merge_data_row['right_table_id'] = right_table_id
        # add the complete row/object to the merged_data array
        merged_data.append(merge_data_row)
    return merged_data


# Edit existing silo meta data
@csrf_protect
@login_required
def editSilo(request, id):
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

from silo.forms import *
import requests
from requests.auth import HTTPDigestAuth


def tolaCon(request):
    params = {'_method': 'OPTIONS'}
    #response = requests.post("https://tola-activity-dev.mercycorps.org/api/proposals/", params)
    response = requests.get("https://tola-activity-dev.mercycorps.org/api/")
    #jsondata = json.loads(response.content)['actions']['POST']
    jsondata = json.loads(response.content)
    """
    data = {}
    for field in jsondata:
        data[field] = {'label': jsondata[field]['label'], 'type': jsondata[field]['type']}

    #print (data)
    """
    return render(request, 'silo/tolaactivity.html', {'data': jsondata })



@login_required
def saveAndImportRead(request):
    """
    Saves ONA read if not already in the db and then imports its data
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("HTTP method, %s, is not supported" % request.method)

    read_type = ReadType.objects.get(read_type="JSON")
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
    except Exception as e:
         #print(e)
         return HttpResponse("Silo ID can only be an integer")

    try:
        read, created = Read.objects.get_or_create(read_name=name, owner=owner,
            defaults={'read_url': url, 'type': read_type, 'description': description})
        if created: read.save()
    except Exception as e:
        #print(e)
        return HttpResponse("Invalid name and/or URL")

    existing_silo_cols = []
    new_cols = []
    show_mapping = False

    if silo_id <= 0:
        # create a new silo by the name of "name"
        silo = Silo(name=name, public=False, owner=owner)
        silo.save()
        silo.reads.add(read)
    else:
        # import into existing silo
        # Compare the columns of imported data with existing silo in case it needs merging
        silo = Silo.objects.get(pk=silo_id)
        lvs = json.loads(LabelValueStore.objects(silo_id=silo.id).to_json())
        for l in lvs:
            existing_silo_cols.extend(c for c in l.keys() if c not in existing_silo_cols)

        for row in data:
            new_cols.extend(c for c in row.keys() if c not in new_cols)

        for c in existing_silo_cols:
            if c == "silo_id" or c == "create_date": continue
            if c not in new_cols: show_mapping = True
            if show_mapping == True:
                params = {'getSourceFrom':existing_silo_cols, 'getSourceTo':new_cols, 'from_silo_id':0, 'to_silo_id':silo.id}
                response = render_to_response("display/merge-column-form-inner.html", params, context_instance=RequestContext(request))
                response['show_mapping'] = '1'
                return response

    if silo:
        # import data into this silo
        num_rows = len(data)
        counter = None
        #loop over data and insert create and edit dates and append to dict
        for counter, row in enumerate(data):
            lvs = LabelValueStore()
            lvs.silo_id = silo.pk
            for new_label, new_value in row.iteritems():
                if new_label is not "" and new_label is not None and new_label is not "edit_date" and new_label is not "create_date":
                    setattr(lvs, new_label, new_value)
            lvs.create_date = timezone.now()
            result = lvs.save()

        if num_rows == (counter+1):
            combineColumns(silo_id)
            return HttpResponse("View table data at <a href='/silo_detail/%s' target='_blank'>See your data</a>" % silo.pk)

    return HttpResponse(read.pk)

@login_required
def getOnaForms(request):
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
    initial = {'owner': request.user}
    excluded_fields=('autopush_frequency', 'autopull_frequency', 'read_url')
    try:
        read_instance = Read.objects.get(pk=id)
        if read_instance.type.read_type != "CSV":
            excluded_fields = ('file_data',)
    except Read.DoesNotExist as e:
        read_instance = None
        initial['type'] = ReadType.objects.get(read_type="CSV")

    if request.method == 'POST':
        form = ReadForm(request.POST, request.FILES, instance=read_instance)
        if form.is_valid():
            read = form.save()
            if form.instance.type.read_type == "CSV":
                return HttpResponseRedirect("/file/" + str(read.id) + "/")

            if form.instance.autopull_frequency or form.instance.autopush_frequency:
                messages.info(request, "Your table must have a unique column set for Autopull/Autopush to work.")
            return HttpResponseRedirect(reverse_lazy('listSilos'))
        else:
            messages.error(request, 'Invalid Form', fail_silently=False)
    else:
        form = ReadForm(exclude_list=excluded_fields, instance=read_instance, initial=initial)
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
            data = csv.reader(read_obj.file_data)
            labels = None
            try:
                labels = data.next() #First row of CSV should be Column Headers
            except IOError as e:
                messages.error(request, "The CSV file could not be found")
                return HttpResponseRedirect(reverse_lazy('showRead', kwargs={'id': read_obj.id},))

            for row in data:
                lvs = LabelValueStore()
                lvs.silo_id = silo_id
                for col_counter, val in enumerate(row):
                    key = str(labels[col_counter]).replace(".", "_").replace("$", "USD")
                    if key != "" and key is not None and key != "silo_id" and key != "id" and key != "_id":
                        if key == "create_date": key = "created_date"
                        if key == "edit_date": key = "editted_date"
                        setattr(lvs, key, val)
                lvs.create_date = timezone.now()
                lvs.save()
            combineColumns(silo_id)
            return HttpResponseRedirect('/silo_detail/' + str(silo_id) + '/')
        else:
            messages.error(request, "There was a problem with reading the contents of your file" + form.errors)
            #print form.errors

    user = User.objects.get(username__exact=request.user)
    # get all of the silo info to pass to the form
    get_silo = Silo.objects.filter(owner=user)

    # display login form
    return render(request, 'read/file.html', {
        'read_id': id, 'get_silo': get_silo,
    })


@login_required
def getJSON(request):
    """
    Get JSON feed info from form then grab data
    """
    if request.method == 'POST':
        # retrieve submitted Feed info from database
        read_obj = Read.objects.get(id = request.POST.get("read_id", None))

        # set date time stamp
        today = datetime.date.today()
        today.strftime('%Y-%m-%d')
        today = str(today)
        try:
            request2 = urllib2.Request(read_obj.read_url)
            #if they passed in a usernmae get auth info from form post then encode and add to the request header
            if request.POST['user_name']:
                username = request.POST['user_name']
                password = request.POST['password']
                base64string = base64.encodestring('%s:%s' % (username, password))[:-1]
                request2.add_header("Authorization", "Basic %s" % base64string)
            #retrieve JSON data from formhub via auth info
            json_file = urllib2.urlopen(request2)
        except Exception as e:
            #print e
            messages.error(request, 'Authentication Failed, Please double check your login credentials and URL!')

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
        data = json.load(json_file)
        json_file.close()

        #loop over data and insert create and edit dates and append to dict
        for row in data:
            lvs = LabelValueStore()
            lvs.silo_id = silo_id
            for new_label, new_value in row.iteritems():
                if new_label is not "" and new_label is not None and new_label is not "edit_date" and new_label is not "create_date":
                    setattr(lvs, new_label, new_value)
            lvs.create_date = timezone.now()
            lvs.save()
        combineColumns(silo_id)
        messages.success(request, "Data imported successfully.")
        return HttpResponseRedirect('/silo_detail/' + str(silo_id) + '/')
    else:
        messages.error(request, "Invalid Request for importing JSON data")
        return HttpResponseRedirect("/")
#display
#INDEX
def index(request):

    # get all of the table(silo) info for logged in user and public data
    if request.user.is_authenticated():
        user = User.objects.get(username__exact=request.user)
        get_silos = Silo.objects.filter(owner=user)
    else:
        get_silos = None
    count_all = Silo.objects.count()
    count_max = count_all + (count_all * .10)
    get_public = Silo.objects.filter(public=1)
    site = TolaSites.objects.get(site_id=1)
    return render(request, 'index.html',{'get_silos':get_silos,'get_public':get_public, 'count_all':count_all, 'count_max':count_max, 'site': site})


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
        if unique_cols and silo_id:
            silo = Silo.objects.get(pk=silo_id)
            silo.unique_fields.all().delete()
            for col in unique_cols:
                unique_field = UniqueFields(name=col, silo=silo)
                unique_field.save()
            return HttpResponse("Unique Fields saved")
    return HttpResponse("Only POST requests are processed.")


@login_required
def updateEntireColumn(request):
    silo_id = request.POST.get("silo_id", None)
    silo_id = int(silo_id)
    colname = request.POST.get("update_col", None)
    new_val = request.POST.get("new_val", None)
    if silo_id and colname and new_val:
        client = MongoClient(uri)
        db = client.tola
        db.label_value_store.update_many(
                {"silo_id": silo_id},
                    {
                    "$set": {colname: new_val},
                    },
                False
            )
        messages.success(request, "Successfully, changed the %s column value to %s" % (colname, new_val))

    return HttpResponseRedirect(reverse_lazy('siloDetail', kwargs={'id': silo_id}))

#SILO-DETAIL Show data from source
@login_required
def siloDetail(request,id):
    """
    Show silo source details
    """
    silo = Silo.objects.filter(pk=id).prefetch_related("unique_fields")[0]
    owner = silo.owner
    public = silo.public

    lvs = json.loads(LabelValueStore.objects(silo_id = id).to_json())
    cols = []
    for l in lvs:
        cols.extend([k for k in l.keys() if k not in cols and k != '_id' and k != 'silo_id' and k != 'create_date' and k != 'edit_date' and k != 'source_table_id'])
    #cols = json.dumps(cols)

    #if str(owner.username) == str(request.user) or public:
    if silo.owner == owner or silo.public == True or owner__in == silo.shared:
        table = LabelValueStore.objects(silo_id=id).to_json()
        decoded_json = json.loads(table)
        column_names = []
        #column_names = decoded_json[0].keys()
        for row in decoded_json:
            column_names.extend([k for k in row.keys() if k not in column_names])

        if decoded_json:
            silo_table = define_table(column_names)(decoded_json)

            #This is needed in order for table sorting to work
            RequestConfig(request).configure(silo_table)

            #send the keys and vars from the json data to the template along with submitted feed info and silos for new form
            return render(request, "display/silo_detail.html", {"silo_table": silo_table, 'silo': silo, 'id':id, 'cols': cols})
        else:
            messages.error(request, "There is not data in Table with id = %s" % id)
            return HttpResponseRedirect(request.META['HTTP_REFERER'])
    else:
        messages.info(request, "You don't have the permission to see data in this table")
        return HttpResponseRedirect(request.META['HTTP_REFERER'])


@login_required
def updateMergeSilo(request, pk):
    silo = None
    mapping = None

    try:
        silo = Silo.objects.get(id=pk)
    except Silo.DoesNotExist as e:
        return HttpResponse("Table (%s) does not exist" % pk)

    try:
        mapping = MergedSilosFieldMapping.objects.get(merged_silo = silo.pk)
        left_table_id = mapping.from_silo.pk
        right_table_id = mapping.to_silo.pk
        data = mapping.mapping

        merged_data = mergeTwoSilos(data, left_table_id, right_table_id)
        try:
            merged_data['status']
            messages.error(request, 'Failed to apply %s to column, %s : %s ' % (merge_type, col, e.message))
            return HttpResponseRedirect(reverse_lazy('siloDetail', kwargs={'id': pk},))
        except Exception as e:
            pass

        lvs = LabelValueStore.objects(silo_id=silo.id)
        num_rows_deleted = lvs.delete()

        # put the new silo data in mongo db.
        for counter, row in enumerate(merged_data):
            lvs = LabelValueStore()
            lvs.silo_id = silo.pk
            for l, v in row.iteritems():
                if l == 'silo_id' or l == '_id' or l == 'create_date' or l == 'edit_date':
                    continue
                else:
                    setattr(lvs, l, v)
            lvs.create_date = timezone.now()
            result = lvs.save()

    except MergedSilosFieldMapping.DoesNotExist as e:
        # Check if the silo has a source from ONA: and if so, then update its data
        stop = False



        if silo.unique_fields.all().exists() == False:
            stop = True
            messages.info(request, "In order to update a table, it must have a unique field set.")


        read_type = ReadType.objects.get(read_type="JSON")
        reads = silo.reads.filter(type=read_type.pk)
        for read in reads:
            ona_token = ThirdPartyTokens.objects.get(user=silo.owner.pk, name="ONA")
            response = requests.get(read.read_url, headers={'Authorization': 'Token %s' % ona_token.token})
            data = json.loads(response.content)

            # import data into this silo
            num_rows = len(data)
            if num_rows == 0:
                continue

            counter = None
            #loop over data and insert create and edit dates and append to dict
            for counter, row in enumerate(data):
                skip_row = False
                #if the value of unique column is already in existing_silo_data then skip the row
                for unique_field in silo.unique_fields.all():
                    filter_criteria = {'silo_id': silo.pk, unique_field.name: row[unique_field.name]}
                    if LabelValueStore.objects.filter(**filter_criteria).count() > 0:
                        skip_row = True
                        continue
                if skip_row == True:
                    continue
                # at this point, the unique column value is not in existing data so append it.
                lvs = LabelValueStore()
                lvs.silo_id = silo.pk
                for new_label, new_value in row.iteritems():
                    if new_label is not "" and new_label is not None and new_label is not "edit_date" and new_label is not "create_date":
                        setattr(lvs, new_label, new_value)
                lvs.create_date = timezone.now()
                result = lvs.save()

            if num_rows == (counter+1):
                combineColumns(silo.pk)
        # reset num_rows
        num_rows = 0
        read_types = ReadType.objects.filter(Q(read_type="GSheet Import") | Q(read_type="Google Spreadsheet"))
        reads = silo.reads.filter(reduce(or_, [Q(type=read.id) for read in read_types]))
        for read in reads:
            # get gsheet authorized client and the gsheet id to fetch its data into the silo
            storage = Storage(GoogleCredentialsModel, 'id', silo.owner, 'credential')
            credential = storage.get()
            credential_json = json.loads(credential.to_json())
            #self.stdout.write("%s" % credential_json)
            if credential is None or credential.invalid == True:
                messages.error(request, "There was a Google credential problem with user: %s for gsheet %s" % (request.user, read.pk))
                continue

            suc = import_from_google_spreadsheet(credential_json, silo, read.resource_id)
            if suc == False:
                messages.error(request, "Failed to import data from gsheet %s " % read.pk)

        if not reads:
            stop = True
            messages.info(request, "Tables that only have a CSV source cannot be updated.")
    return HttpResponseRedirect(reverse_lazy('siloDetail', kwargs={'id': pk},))


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
            client = MongoClient(uri)
            db = client.tola
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
    data = getSiloColumnNames(id)
    form = EditColumnForm(initial={'silo_id': silo.id}, extra=data)

    if request.method == 'POST':
        form = EditColumnForm(request.POST or None, extra = data)  # A form bound to the POST data
        if form.is_valid():  # All validation rules pass
            client = MongoClient(uri)
            db = client.tola
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
    client = MongoClient(uri)
    db = client.tola

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

import pymongo
from bson.objectid import ObjectId
from pymongo import MongoClient
uri = 'mongodb://localhost/tola'

def doMerge(request):

    # setup mongodb conn.
    client = MongoClient(uri)
    db = client.tola

    # get the table_ids.
    left_table_id = request.POST['left_table_id']
    right_table_id = request.POST["right_table_id"]
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

    merged_data = mergeTwoSilos(data, left_table_id, right_table_id)

    try:
        merged_data['status']
        return JsonResponse(merged_data)
    except Exception as e:
        pass

    # Create a new silo
    new_silo = Silo(name=merged_silo_name , public=False, owner=request.user)
    new_silo.save()

    # put the new silo data in mongo db.
    for counter, row in enumerate(merged_data):
        lvs = LabelValueStore()
        lvs.silo_id = new_silo.pk
        for l, v in row.iteritems():
            if l == 'silo_id' or l == '_id' or l == 'create_date' or l == 'edit_date':
                continue
            else:
                setattr(lvs, l, v)
        lvs.create_date = timezone.now()
        result = lvs.save()

    mapping = MergedSilosFieldMapping(from_silo=left_table, to_silo=right_table, merged_silo=new_silo, mapping=data)
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
            #print("The key and value are ({}) = ({})".format(k, v))
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



def customFeed(request,id):
    """
    All tags in use on this system
    id = Silo
    """
    queryset = LabelValueStore.objects.exclude("silo_id").filter(silo_id=id).to_json()

    return render(request, 'feed/json.html', {"jsonData": queryset}, content_type="application/json")

def createFeed(request):
    """
    Create an XML or JSON Feed from a given Silo
    """
    getSilo = ValueStore.objects.filter(field__silo__id=request.POST['silo_id']).order_by('row_number')

    #return a dict with label value pair data
    formatted_data = siloToDict(getSilo)

    getFeedType = FeedType.objects.get(pk = request.POST['feed_type'])

    if getFeedType.description == "XML":
        xmlData = serialize(formatted_data)
        return render(request, 'feed/xml.html', {"xml": xmlData}, content_type="application/xhtml+xml")
    elif getFeedType.description == "JSON":
        jsonData = simplejson.dumps(formatted_data)
        return render(request, 'feed/json.html', {"jsonData": jsonData}, content_type="application/json")


def export_silo(request, id):

    silo_name = Silo.objects.get(id=id).name

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="%s.csv"' % silo_name
    writer = csv.writer(response)

    silo_data = LabelValueStore.objects(silo_id=id)
    data = []
    num_cols = 0
    cols = OrderedDict()
    if silo_data:
        num_rows = len(silo_data)

        for row in silo_data:
            for i, col in enumerate(row):
                if col not in cols.keys():
                    num_cols = num_cols + 1
                    cols[col] = num_cols

        # Convert OrderedDict to Python list so that it can be written to CSV writer.
        cols = list(cols)
        writer.writerow(list(cols))

        # Populate a 2x2 list structure that corresponds to the number of rows and cols in silo_data
        for i in xrange(num_rows): data += [[0]*num_cols]

        for r, row in enumerate(silo_data):
            for col in row:
                # Map values to column names and place them in the correct position in the data array
                data[r][cols.index(col)] = smart_str(row[col])
            writer.writerow(data[r])
    return response


