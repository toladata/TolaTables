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

CLIENT_SECRETS = os.path.join(os.path.dirname(__file__), 'client_secrets.json')
SCOPE = 'https://www.googleapis.com/auth/spreadsheets'
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
    discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?'
                    'version=v4')
    service = discovery.build('sheets', 'v4', http=http,
                              discoveryServiceUrl=discoveryUrl)

    post_body =  { "properties": {"title": "NewTitle"} }
    body = json.dumps(post_body)
    print(body)
    #headers = {'Content-type': 'application/x-www-form-urlencoded'}
    res, content = http.request(
                                uri="https://sheets.googleapis.com/v4/spreadsheets",
                                method="POST",
                                body=body,
                                #headers = headers
                                headers={'Content-Type': 'application/json; charset=UTF-8'},
                                )
    return JsonResponse({"res": res, "content": content})

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


