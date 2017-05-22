import json
import requests

from requests.auth import HTTPDigestAuth
from django.http import HttpResponseForbidden,\
    HttpResponseRedirect, HttpResponseNotFound, HttpResponseBadRequest,\
    HttpResponse, HttpResponseRedirect, JsonResponse


from django.shortcuts import render
from tola.util import siloToDict, combineColumns, importJSON, saveDataToSilo, getSiloColumnNames
from django.shortcuts import render_to_response, get_object_or_404, redirect, render
from django.core.urlresolvers import reverse, reverse_lazy


from silo.models import Silo, Read, ReadType, ThirdPartyTokens, LabelValueStore, Tag, UniqueFields, MergedSilosFieldMapping, TolaSites, PIIColumn
from .forms import CommCareForm, CommCareProjectForm


def getCommCareForm(request):
    """
    Get the forms owned or shared with the logged in user
    :param request:
    :return: list of Ona forms paired with action buttons
    """
    data = {}
    form = None
    provider = "CommCare"
    """ #If I can get the authorization token to work
    auth_success = False
    commcare_token = None
    url_user_token = "" #url to get the user data
    url_user_forms = "" #url to get the data contained
    url_user_forms1 = "https://www.commcarehq.org/a/"
    url_user_forms2 = "/api/v0.5/simplereportconfiguration/?format=json"
    user_project = None

    if request.method == 'POST':
        try: #just need the project name
            commcare_token = ThirdPartyTokens.objects.get(name=provider, user=request.user) #forms a query of the the username to get an authentication token
            auth_success = True
            form = CommCareProjectForm(request.POST) #add the project name to the request
            user_project = request.POST['project']
            url_user_forms = url_user_forms1 + user_project + url_user_forms2
        except Exception as e: #need to get the project name and the username and password
            form = CommCareForm(request.POST) #add the username and password to the request
            if form.is_valid(): #does the form meet requierements
                response = requests.get(url_user_token, auth=HTTPDigestAuth(request.POST['username'], request.POST['password'])) #request the user data with a password and username
                if response.status_code == 401:
                    messages.error(request, "Invalid username or password.")
                elif response.status_code == 200:
                    user_project = request.POST['project']
                    url_user_forms = url_user_forms1 + user_project + url_user_forms2
                    auth_success = True
                    token = json.loads(response.content)['api_token'] #load the users authentication token into a variables
                    commcare_token, created = ThirdPartyTokens.objects.get_or_create(user=request.user, name=provider, token=token) #load the users token
                    if created: commcare_token.save()
                else:
                    messages.error(request, "A %s error has occured: %s " % (response.status_code, response.text))

    else:
        try: #if the authentication token is in the database just get the project name
            commcare_token = ThirdPartyTokens.objects.get(name=provider, user=request.user) #forms a query of the the username to get an authentication token
            form = CommCareProjectForm()
        except Exception as e: #otherwise need the username/password/project
            form = CommCareForm()

    if commcare_token and auth_success:
        commcareforms = requests.get(url_user_forms, headers={'Authorization': 'Token %s' % commcare_token.token}) #get the data
        data = json.loads(commcareforms.content) #load data into the json
    """
    #this version works without the token
    url_user_forms = "" #url to get the data contained
    url_user_forms1 = "https://www.commcarehq.org/a/"
    url_user_forms2 = "/api/v0.5/simplereportconfiguration/?format=json"

    if request.method == 'POST':
        form = CommCareForm(request.POST) #add the username and password to the request
        if form.is_valid(): #does the form meet requierements
            url_user_forms = url_user_forms1 + request.POST['project'] + url_user_forms2
            response = requests.get(url_user_forms, auth=HTTPDigestAuth(request.POST['username'], request.POST['password'])) #request the user data with a password and username
            if response.status_code == 401:
                messages.error(request, "Invalid username, password or project.")
            elif response.status_code == 200:
                data = json.loads(response.content) #load data into the json
            else:
                messages.error(request, "A %s error has occured: %s " % (response.status_code, response.text))
    else:
        form = CommCareForm()


    silos = Silo.objects.filter(owner=request.user)
    return render(request, 'getcommcareforms.html', {'form': form, 'data': data, 'silos': silos})
