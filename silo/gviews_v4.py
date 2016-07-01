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


def export_new_gsheet(request, id):
    storage = Storage(GoogleCredentialsModel, 'id', request.user, 'credential')
    credential_obj = storage.get()
    if credential_obj is None or credential_obj.invalid == True:
        FLOW.params['state'] = xsrfutil.generate_token(settings.SECRET_KEY, request.user)
        authorize_url = FLOW.step1_get_authorize_url()
        #FLOW.params.update({'redirect_uri_after_step2': "/export_new_gsheet/%s/" % id})
        request.session['redirect_uri_after_step2'] = "/export_new_gsheet/%s/" % id
        return HttpResponseRedirect(authorize_url)
    credential = json.loads(credential_obj.to_json())

    http = credential_obj.authorize(httplib2.Http())
    discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?version=v4')
    service = discovery.build('sheets', 'v4', http=http,
                              discoveryServiceUrl=discoveryUrl)

    post_body =  { "properties": {"title": "xyztitle"} }
    body = json.dumps(post_body)

    res, content = http.request(uri=BASE_URL,
                                method="POST",
                                body=body,
                                headers={'Content-Type': 'application/json; charset=UTF-8'},
                                )
    content_json = json.loads(content)
    spreadsheetId = content_json.get("spreadsheetId", None)

    #spreadsheetId = "1IX66-N5vNZsymKo2WsX1jsmMQOCKup445BoDrcXERNg"
    #get spreadsheet metadata
    sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheetId).execute()
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
    content_json = service.spreadsheets().batchUpdate(spreadsheetId=spreadsheetId, body=batchUpdateRequest).execute()

    return JsonResponse(sheet_metadata)

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


