import httplib2
import urllib
import os
import logging
import json
import datetime

from django.core.urlresolvers import reverse, reverse_lazy
from django.http import HttpResponseRedirect, HttpResponseBadRequest, JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_protect
from django.conf import settings
from django.utils import timezone

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

from apiclient import discovery

import oauth2client
from oauth2client import client
from oauth2client import tools

from oauth2client.client import flow_from_clientsecrets
from oauth2client.contrib.django_orm import Storage
from oauth2client.contrib import xsrfutil

from .models import GoogleCredentialsModel
from .models import Silo, Read, ReadType, ThirdPartyTokens, LabelValueStore, Tag
from tola.util import siloToDict, combineColumns
logger = logging.getLogger("silo")


CLIENT_SECRETS = os.path.join(os.path.dirname(__file__), 'client_secrets.json')
SCOPE = 'https://www.googleapis.com/auth/spreadsheets'
BASE_URL = "https://sheets.googleapis.com/v4/spreadsheets/"
FLOW = flow_from_clientsecrets(
    CLIENT_SECRETS,
    scope=SCOPE,
    redirect_uri=settings.GOOGLE_REDIRECT_URL)
    #redirect_uri='http://localhost:8000/oauth2callback/')

def import_from_gsheet(request, id):
    gsheet_endpoint = None
    silo = None
    read_url = request.GET.get('link', None)
    spreadsheet_id = request.GET.get('resource_id', None)
    silo_name = request.GET.get("name", "Google Sheet Import")
    if read_url is None or spreadsheet_id is None:
        messages.error(request, "A Google Spreadsheet is not selected to import data from.")
        return HttpResponseRedirect(reverse('index'))

    storage = Storage(GoogleCredentialsModel, 'id', request.user, 'credential')
    credential_obj = storage.get()
    if credential_obj is None or credential_obj.invalid == True:
        FLOW.params['state'] = xsrfutil.generate_token(settings.SECRET_KEY, request.user)
        authorize_url = FLOW.step1_get_authorize_url()
        #FLOW.params.update({'redirect_uri_after_step2': "/export_new_gsheet/%s/" % id})
        request.session['redirect_uri_after_step2'] = "/import_from_gsheet/%s/?link=%s&resource_id=%s" % (id, read_url, spreadsheet_id)
        return HttpResponseRedirect(authorize_url)
    credential = json.loads(credential_obj.to_json())

    defaults = {"name": silo_name, "description": "Google Sheet Import", "public": False, "owner": request.user}
    silo, created = Silo.objects.get_or_create(pk=None if id=='0' else id, defaults=defaults)
    if not created and silo.unique_fields.exists() == False:
        messages.error(request, "A unique column must be specfied when importing to an existing table. <a href='%s'>Specify Unique Column</a>" % reverse_lazy('siloDetail', kwargs={"id": silo.id}))
        return HttpResponseRedirect(request.META['HTTP_REFERER'])

    # If a 'read' object does not exist for this export action, then create it
    read_type = ReadType.objects.get(read_type="GSheet Import")
    defaults = {"type": read_type,
                "read_name":"Google Spreadsheet Import",
                "description": "Google Spreadsheet Import",
                "read_url": "https://docs.google.com/a/mercycorps.org/spreadsheets/d/%s" % spreadsheet_id,
                "owner": request.user}
    gsheet_read, created = Read.objects.get_or_create(silos__id=id,
                                                      silos__owner=request.user,
                                                      resource_id=spreadsheet_id,
                                                      defaults=defaults)
    if created:
        silo.reads.add(gsheet_read)

    http = credential_obj.authorize(httplib2.Http())
    discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?version=v4')
    service = discovery.build('sheets', 'v4', http=http,
                              discoveryServiceUrl=discoveryUrl)

    headers = []
    data = None
    filter_criteria = {'silo_id': silo.id}
    try:
        result = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range="Sheet1").execute()
        data = result.get("values", [])
        for r, row in enumerate(data):
            if r == 0: headers = row; continue;

            # build filter_criteria if unique field(s) have been setup for this silo
            for unique_field in silo.unique_fields.all():
                filter_criteria.update({unique_field.name: row[headers.index(unique_field.name)]})

            # if filter_criteria dict is built based on silo's unique cols then retrieve that doc
            if filter_criteria:
                lvs = LabelValueStore.objects.get(**filter_criteria)
            else:
                lvs = LabelValueStore()
            for c, col in enumerate(row):
                key = headers[c]
                if key == "" or key is None or key == "silo_id" or key == "create_date" or key == "edit_date": continue
                if key == "id" or key == "_id": key = "user_assigned_id"
                setattr(lvs, key, row[c])
            lvs.silo_id = silo.id
            lvs.create_date = timezone.now()
            lvs.save()
    except Exception as e:
        messages.error(request, "Something went wrong: %s" % e.message)

    return HttpResponse(data)

def export_to_gsheet(request, id):
    storage = Storage(GoogleCredentialsModel, 'id', request.user, 'credential')
    credential_obj = storage.get()
    if credential_obj is None or credential_obj.invalid == True:
        FLOW.params['state'] = xsrfutil.generate_token(settings.SECRET_KEY, request.user)
        authorize_url = FLOW.step1_get_authorize_url()
        #FLOW.params.update({'redirect_uri_after_step2': "/export_new_gsheet/%s/" % id})
        request.session['redirect_uri_after_step2'] = "/export_to_gsheet/%s/" % id
        return HttpResponseRedirect(authorize_url)
    credential = json.loads(credential_obj.to_json())

    http = credential_obj.authorize(httplib2.Http())
    discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?version=v4')
    service = discovery.build('sheets', 'v4', http=http,
                              discoveryServiceUrl=discoveryUrl)

    try:
        silo = Silo.objects.get(pk=id)
    except Exception as e:
        logger.erro("Silo with id=%s does not exist" % id)
        return HttpResponseRedirect(reverse('listSilos'))

    # Get the spreadsheet_id from the request object
    spreadsheet_id = request.GET.get("resource_id", None)

    # if no spreadhsset_id is provided, then create a new spreadsheet
    if spreadsheet_id is None:
        post_body =  { "properties": {"title": silo.name} }
        body = json.dumps(post_body)
        res, content = http.request(uri=BASE_URL,
                                    method="POST",
                                    body=body,
                                    headers={'Content-Type': 'application/json; charset=UTF-8'},
                                    )
        content_json = json.loads(content)

        # Now store the id of the newly created spreadsheet
        spreadsheet_id = content_json.get("spreadsheetId", None)

    # If a 'read' object does not exist for this export action, then create it
    read_type = ReadType.objects.get(read_type="Google Spreadsheet")
    defaults = {"type": read_type,
                "read_name":"Google Spreadsheet Export",
                "description": "Google Spreadsheet Export",
                "read_url": "https://docs.google.com/a/mercycorps.org/spreadsheets/d/%s" % spreadsheet_id,
                "owner": request.user}
    gsheet_read, created = Read.objects.get_or_create(silos__id=id,
                                                      silos__owner=request.user,
                                                      resource_id=spreadsheet_id,
                                                      defaults=defaults)
    if created:
        silo.reads.add(gsheet_read)

    #get spreadsheet metadata
    sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheet = sheet_metadata.get('sheets', '')[0]
    title = sheet.get("properties", {}).get("title", "Sheet1")
    sheet_id = sheet.get("properties", {}).get("sheetId", 0)

    # the first element in the array is a placeholder for column names
    rows = [{"values": []}]
    headers = []
    silo_data = LabelValueStore.objects(silo_id=id)

    for row in silo_data:
        # Get all of the values of a single mongodb document into this array
        values = []
        for i, col in enumerate(row):
            if col == "id" or col == "_id" or col == "silo_id" or col == "created_date" or col == "create_date" or col == "edit_date" or col == "editted_date":
                continue
            if col not in headers:
                headers.append(col)

            values.append({"userEnteredValue": {"stringValue": row[col]}})
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

    # execute the batched requests
    try:
        service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=batchUpdateRequest).execute()
        link = "Your exported data is available at <a href=" + gsheet_read.read_url + " target='_blank'>Google Spreadsheet</a>"
        messages.success(request, link)
    except Exception as e:
        messages.error(request, "Something went wrong. %s" % e.message)

    return HttpResponseRedirect(reverse('listSilos'))

@login_required
def oauth2callback(request):
    if not xsrfutil.validate_token(settings.SECRET_KEY, str(request.GET['state']), request.user):
        return  HttpResponseBadRequest()

    credential = FLOW.step2_exchange(request.GET)
    storage = Storage(GoogleCredentialsModel, 'id', request.user, 'credential')
    storage.put(credential)
    #print(credential.to_json())
    redirect_url = request.session['redirect_uri_after_step2']
    return HttpResponseRedirect(redirect_url)


