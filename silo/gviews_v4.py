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

    """
    res, content = http.request(uri=BASE_URL,
                                method="POST",
                                body=body,
                                headers={'Content-Type': 'application/json; charset=UTF-8'},
                                )
    content_json = json.loads(content)
    sid = content_json.get("spreadsheetId", "none")
    url = BASE_URL + sid + "/values:batchUpdate"
    requests = []
    # Change the name of sheet ID '0' (the default first sheet on every
    # spreadsheet)
    requests.append({
        'updateSheetProperties': {
            'properties': {'sheetId': 0, 'title': 'New Sheet Name'},
            'fields': 'title'
        }
    })
    requests.append({
        'updateCells': {
            'start': {'sheetId': 0, 'rowIndex': 0, 'columnIndex': 0},
            'rows': [
                {
                    'values': [
                        {
                            'userEnteredValue': {'numberValue': 1},
                            'userEnteredFormat': {'backgroundColor': {'red': 1}}
                        }, {
                            'userEnteredValue': {'numberValue': 2},
                            'userEnteredFormat': {'backgroundColor': {'blue': 1}}
                        }, {
                            'userEnteredValue': {'numberValue': 3},
                            'userEnteredFormat': {'backgroundColor': {'green': 1}}
                        }
                    ]
                }
            ],
            'fields': 'userEnteredValue,userEnteredFormat.backgroundColor'
        }
    })
    batchUpdateRequest = {'requests': requests}
    """
    #service.spreadsheets().batchUpdate(spreadsheetId=sid, body=batchUpdateRequest).execute()

    sid = "1IX66-N5vNZsymKo2WsX1jsmMQOCKup445BoDrcXERNg"
    # get spreadsheet metadata
    #content_json = service.spreadsheets().get(spreadsheetId=sid).execute()
    headers = []
    data = []
    silo_data = LabelValueStore.objects(silo_id=id)
    for silo_row in silo_data:
        row = []
        for i, col in enumerate(silo_row):
            if col not in headers:
                if col == "id" or col == "_id" or col == "silo_id" or col == "created_date" or col == "create_date" or col == "edit_date" or col == "editted_date":
                    continue
                headers.append(col)
            row.append(silo_row[col])
        if len(data) == 0: data.append(headers)
        data.append(row)

    requests = {
        "valueInputOption": "USER_ENTERED",
        "data": [
            {
                "range": "A1:AB%s" % len(data),
                "majorDimension": "ROWS",
                "values": data
            }
        ]
    }

    content_json = service.spreadsheets().values().batchUpdate(spreadsheetId=sid, body=requests).execute()
    return JsonResponse(content_json)

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


