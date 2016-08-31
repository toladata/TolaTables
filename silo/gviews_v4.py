import httplib2
import urllib
import os
import logging
import json
import datetime

#from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.core.urlresolvers import reverse, reverse_lazy
from django.http import HttpResponseRedirect, HttpResponseBadRequest, JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_protect
from django.conf import settings
from django.utils import timezone
from django.utils.encoding import smart_text, smart_str

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

from apiclient import discovery

import oauth2client
from oauth2client.client import OAuth2Credentials
from oauth2client import client
from oauth2client import tools

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import HttpAccessTokenRefreshError
from oauth2client.contrib.django_orm import Storage
from oauth2client.contrib import xsrfutil

from .models import GoogleCredentialsModel
from .models import Silo, Read, ReadType, ThirdPartyTokens, LabelValueStore, Tag
from tola.util import siloToDict, combineColumns
logger = logging.getLogger("silo")


CLIENT_SECRETS = os.path.join(os.path.dirname(__file__), 'client_secrets.json')
SCOPE = 'https://www.googleapis.com/auth/spreadsheets'
BASE_URL = "https://sheets.googleapis.com/v4/spreadsheets/"
discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?version=v4')
FLOW = flow_from_clientsecrets(
    CLIENT_SECRETS,
    scope=SCOPE,
    redirect_uri=settings.GOOGLE_REDIRECT_URL)
    #redirect_uri='http://localhost:8000/oauth2callback/')

def get_spreadsheet_url(spreadsheet_id):
    return "https://docs.google.com/a/mercycorps.org/spreadsheets/d/%s/" % str(spreadsheet_id)

def get_credential_object(user, prompt=None):
    storage = Storage(GoogleCredentialsModel, 'id', user, 'credential')
    credential_obj = storage.get()
    if credential_obj is None or credential_obj.invalid == True or prompt:
        FLOW.params['state'] = xsrfutil.generate_token(settings.SECRET_KEY, user)
        FLOW.params['access_type'] = 'offline'
        FLOW.params['approval_prompt'] = 'force'
        authorize_url = FLOW.step1_get_authorize_url()
        return {"level": messages.ERROR,
                    "msg": "Requires Google Authorization Setup",
                    "redirect": authorize_url,
                    "redirect_uri_after_step2": True}
    #print(json.loads(credential_obj.to_json()))
    return credential_obj


def get_authorized_service(credential_obj):
    http = credential_obj.authorize(httplib2.Http())
    service = discovery.build('sheets', 'v4', http=http, discoveryServiceUrl=discoveryUrl)
    return service


def get_or_create_read(rtype, name, description, spreadsheet_id, user, silo):
    # If a 'read' object does not exist for this export action, then create it
    read_type = ReadType.objects.get(read_type=rtype)
    defaults = {"type": read_type,
                "read_name": name,
                "description": description,
                "read_url": get_spreadsheet_url(spreadsheet_id),
                "owner": user}
    gsheet_read, created = Read.objects.get_or_create(silos__id=silo.pk,
                                                      silos__owner=user,
                                                      resource_id=spreadsheet_id,
                                                      defaults=defaults)
    if created:
        silo.reads.add(gsheet_read)
    return gsheet_read


def import_from_gsheet_helper(user, silo_id, silo_name, spreadsheet_id, sheet_id=None):
    msgs = []
    read_url = get_spreadsheet_url(spreadsheet_id)

    if spreadsheet_id is None:
        msgs.append({"level": messages.ERROR,
                    "msg": "A Google Spreadsheet is not selected to import data from.",
                    "redirect" : reverse('index') })

    credential_obj = get_credential_object(user)
    if not isinstance(credential_obj, OAuth2Credentials):
        msgs.append(credential_obj)
        return msgs

    defaults = {"name": silo_name, "description": "Google Sheet Import", "public": False, "owner": user}
    silo, created = Silo.objects.get_or_create(pk=None if silo_id=='0' else silo_id, defaults=defaults)
    if not created and silo.unique_fields.exists() == False:
        msgs.append({"level": messages.ERROR,
                    "msg": "A unique column must be specfied when importing to an existing table. <a href='%s'>Specify Unique Column</a>" % reverse_lazy('siloDetail', kwargs={"id": silo.id}),
                    "redirect": None})
        return msgs

    if created:
        msgs.append({"silo_id": silo.id})

    service = get_authorized_service(credential_obj)

    # fetch the google spreadsheet metadata
    try:
        spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    except HttpAccessTokenRefreshError as e:
        return [get_credential_object(user, True)]
    except Exception as e:
        error = json.loads(e.content).get("error")
        msg = "%s: %s" % (error.get("status"), error.get("message"))
        msgs.append({"level": messages.ERROR,
                    "msg": msg})
        return msgs

    spreadsheet_name = spreadsheet.get("properties", {}).get("title", "")

    gsheet_read = get_or_create_read("GSheet Import",
                                     spreadsheet_name,
                                     "Google Spreadsheet Import",
                                     spreadsheet_id,
                                     user,
                                     silo)
    sheet_name = "Sheet1"
    if sheet_id:
        gsheet_read.gsheet_id = sheet_id
        gsheet_read.save()
        sheets = spreadsheet.get("sheets", None)
        for sheet in sheets:
            properties = sheet.get("properties", None)
            if properties:
                if str(properties.get("sheetId")) == str(sheet_id):
                    sheet_name = properties.get("title")

    headers = []
    data = None

    combine_cols = False
    # Fetch data from gsheet
    try:
        result = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=sheet_name).execute()
        data = result.get("values", [])
    except Exception as e:
        msgs.append({"level": messages.ERROR,
                    "msg": "Something went wrong: %s" % e.message,
                    "redirect": None})
        return msgs

    unique_fields = silo.unique_fields.all()
    skipped_rows = set()
    for r, row in enumerate(data):
        if r == 0: headers = row; continue;
        filter_criteria = {}

        # build filter_criteria if unique field(s) have been setup for this silo
        for unique_field in unique_fields:
            try:
                filter_criteria.update({unique_field.name: row[headers.index(unique_field.name)]})
            except KeyError:
                pass
            except ValueError:
                pass
        if filter_criteria:
            filter_criteria.update({'silo_id': silo.id})
            # if a row is found, then fetch and update it
            # if no row is found then create a new one
            # if multiple rows are found then skip b/c not sure which one to update
            try:
                lvs = LabelValueStore.objects.get(**filter_criteria)
                lvs.edit_date = timezone.now()
            except LabelValueStore.DoesNotExist as e:
                lvs = LabelValueStore()
            except LabelValueStore.MultipleObjectsReturned as e:
                for k,v in filter_criteria.iteritems():
                    skipped_rows.add("%s=%s" % (k,v))
                continue
        else:
            lvs = LabelValueStore()

        for c, col in enumerate(row):
            try:
                key = headers[c]
            except KeyError as e:
                #this happens when a column header is missing gsheet
                continue
            if key == "" or key is None or key == "silo_id": continue
            elif key == "id" or key == "_id": key = "user_assigned_id"
            elif key == "edit_date": key = "editted_date"
            elif key == "create_date": key = "created_date"
            val = smart_str(row[c], strings_only=True)
            key = smart_str(key)
            setattr(lvs, key.replace(".", "_").replace("$", "USD"), val)
        lvs.silo_id = silo.id
        lvs.create_date = timezone.now()
        lvs.save()

    combineColumns(silo.pk)

    if skipped_rows:
        msgs.append({"level": messages.WARNING,
                    "msg": "Skipped updating/adding records where %s because there are already multiple records." % ",".join(str(s) for s in skipped_rows)})

    msgs.append({"level": messages.SUCCESS, "msg": "Operation successful"})
    return msgs

@login_required
def import_from_gsheet(request, id):
    gsheet_endpoint = None
    silo = None
    read_url = request.GET.get('link', None)
    spreadsheet_id = request.GET.get('resource_id', None)
    sheet_id = request.GET.get("sheet_id", None)
    silo_name = request.GET.get("name", "Google Sheet Import")

    msgs = import_from_gsheet_helper(request.user, id, silo_name, spreadsheet_id, sheet_id)
    #return HttpResponseRedirect(request.META['HTTP_REFERER'])
    google_auth_redirect = "/import_gsheet/%s/?link=%s&resource_id=%s" % (id, read_url, spreadsheet_id)
    for msg in msgs:
        if "silo_id" in msg.keys(): id = msg.get("silo_id")
        if "redirect_uri_after_step2" in msg.keys():
            request.session['redirect_uri_after_step2'] = google_auth_redirect
            return HttpResponseRedirect(msg.get("redirect"))
        messages.add_message(request, msg.get("level", "warning"), msg.get("msg", None))

    return HttpResponseRedirect(reverse_lazy('siloDetail', kwargs={'id': str(id)},))





def export_to_gsheet_helper(user, spreadsheet_id, silo_id):
    msgs = []
    credential_obj = get_credential_object(user)
    if not isinstance(credential_obj, OAuth2Credentials):
        msgs.append(credential_obj)
        return msgs

    service = get_authorized_service(credential_obj)

    try:
        silo = Silo.objects.get(pk=silo_id)
    except Exception as e:
        logger.error("Silo with id=%s does not exist" % silo_id)
        msgs.append({"level": messages.ERROR,
                    "msg": "Silo with id=%s does not exist" % silo_id,
                    "redirect": reverse('listSilos')})
        return msgs

    try:
        # if no spreadhsset_id is provided, then create a new spreadsheet
        if spreadsheet_id is None:
            # create a new google spreadsheet
            body = {"properties":{"title": silo.name}}
            spreadsheet = service.spreadsheets().create(body=body).execute()
            spreadsheet_id = spreadsheet.get("spreadsheetId", None)
        else:
            # fetch the google spreadsheet metadata
            spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    except HttpAccessTokenRefreshError as e:
        return [get_credential_object(user, True)]
    except Exception as e:
        error = json.loads(e.content).get("error")
        msg = "%s: %s" % (error.get("status"), error.get("message"))
        msgs.append({"level": messages.ERROR,
                    "msg": msg})
        return msgs

    #get spreadsheet metadata
    spreadsheet_name = spreadsheet.get("properties", {}).get("title", "")
    sheet = spreadsheet.get('sheets', '')[0]
    title = sheet.get("properties", {}).get("title", "Sheet1")
    sheet_id = sheet.get("properties", {}).get("sheetId", 0)

    gsheet_read = get_or_create_read("Google Spreadsheet",
                                     spreadsheet_name,
                                     "Google Spreadsheet Export",
                                     spreadsheet_id,
                                     user,
                                     silo)

    # the first element in the array is a placeholder for column names
    rows = [{"values": []}]
    headers = []
    silo_data = json.loads(LabelValueStore.objects(silo_id=silo_id).to_json())

    for row in silo_data:
        values = [] # Get all of the values of a single mongodb document into this array
        index = 0
        for i, col in enumerate(row):
            if col == "id" or col == "_id" or col == "silo_id" or col == "created_date" or col == "create_date" or col == "edit_date" or col == "editted_date":
                continue
            if col not in headers:
                headers.append(col)

            values.append({"userEnteredValue": {"stringValue": smart_text(row[headers[index]])}})
            index += 1
        rows.append({"values": values})

    # prepare column names as a header row in spreadsheet
    values = []
    for header in headers:
        values.append({
                      "userEnteredValue": {"stringValue": header},
                      'userEnteredFormat': {'backgroundColor': {'red':0.5,'green':0.5, 'blue': 0.5}}
                      })
    # Now update the rows array place holder with real column names
    rows[0]["values"] = values
    #batch all of remote api calls into the requests array
    requests = []

    # prepare the request to resize the sheet to make sure it fits the data;
    # otherwise, errors out for datasets with more than 26 column or 1000 rows.
    requests.append({
        'updateSheetProperties': {
            'properties': {
                'sheetId': sheet_id,
                "title": title,
                "gridProperties": {
                    'rowCount': len(rows),
                    'columnCount': len(headers),
                }
            },
            "fields": "title,gridProperties(rowCount,columnCount)"
        }
    })

    # Now prepare the request to push data to gsheet
    requests.append({
        'updateCells': {
            'start': {'sheetId': sheet_id, 'rowIndex': 0, 'columnIndex': 0},
            'rows': rows,
            'fields': 'userEnteredValue,userEnteredFormat.backgroundColor'
        }
    })

    # encapsulate the requests list into a requests object
    batchUpdateRequest = {'requests': requests}

    try:
        service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=batchUpdateRequest).execute()
        msgs.append({"level": messages.SUCCESS,
                    "msg": "Your exported data is available at <a href=" + gsheet_read.read_url + " target='_blank'>Google Spreadsheet</a>"})
    except Exception as e:
        msgs.append({"level": messages.ERROR,
                    "msg": "Failed to submit data to GSheet. %s" % e})

    return msgs

@login_required
def export_to_gsheet(request, id):
    spreadsheet_id = request.GET.get("resource_id", None)
    msgs = export_to_gsheet_helper(request.user, spreadsheet_id, id)

    google_auth_redirect = "export_to_gsheet/%s/" % id

    for msg in msgs:
        if "silo_id" in msg.keys(): id = msg.get("silo_id")
        if "redirect_uri_after_step2" in msg.keys():
            request.session['redirect_uri_after_step2'] = google_auth_redirect
            return HttpResponseRedirect(msg.get("redirect"))
        messages.add_message(request, msg.get("level"), msg.get("msg"))

    return HttpResponseRedirect(reverse('listSilos'))

@login_required
def get_sheets_from_google_spredsheet(request):
    spreadsheet_id = request.GET.get("spreadsheet_id", None)
    credential_obj = get_credential_object(request.user)
    if not isinstance(credential_obj, OAuth2Credentials):
        request.session['redirect_uri_after_step2'] = request.META.get('HTTP_REFERER')
        return JsonResponse(credential_obj)

    service = get_authorized_service(credential_obj)

    try:
        spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    except HttpAccessTokenRefreshError as e:
        return [get_credential_object(request.user, True)]
    except Exception as e:
        error = json.loads(e.content).get("error")
        msg = "%s: %s" % (error.get("status"), error.get("message"))
        return JsonResponse ({"level": messages.ERROR, "msg": msg})
    return JsonResponse(spreadsheet)

@login_required
def oauth2callback(request):
    if not xsrfutil.validate_token(settings.SECRET_KEY, str(request.GET['state']), request.user):
        return  HttpResponseBadRequest()

    credential = FLOW.step2_exchange(request.GET)
    storage = Storage(GoogleCredentialsModel, 'id', request.user, 'credential')
    storage.put(credential)
    redirect_url = request.session['redirect_uri_after_step2']
    return HttpResponseRedirect(redirect_url)


