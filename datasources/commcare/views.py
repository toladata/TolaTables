import json
import requests
import base64

from requests.auth import HTTPDigestAuth
from django.http import HttpResponseRedirect, HttpResponseBadRequest, HttpResponse


from tola.util import saveDataToSilo, getSiloColumnNames
from django.shortcuts import redirect, render
from django.core.urlresolvers import reverse, reverse_lazy

from django.contrib import messages
from django.contrib.auth.decorators import login_required

from silo.models import Silo, Read, ReadType, ThirdPartyTokens
from .forms import CommCareAuthForm, CommCarePassForm, CommCareProjectForm
from .tasks import fetchCommCareData, requestCommCareData
from .util import getCommCareCaseData

@login_required
def getCommCareAuth(request):
    """
    Get the forms owned or shared with the logged in user
    :param request:
    :return: list of Ona forms paired with action buttons
    """
    cols = []
    form = None
    provider = "CommCare"
    #If I can get the authorization token to work
    auth = 1
    commcare_token = None
    url = "" #url to get the data contained
    url1 = "https://www.commcarehq.org/a/"
    url2 = "/api/v0.5/case/?format=JSON&limit=1"
    project = None
    silos = Silo.objects.filter(owner=request.user)
    choices = [(0, ""), (-1, "Create new silo")]
    for silo in silos:
        choices.append((silo.pk, silo.name))

    if request.method == 'POST':
        #their exists a project and authorization so get the data
        form = CommCareProjectForm(request.POST, choices=choices)

        if form.is_valid():
            try:
                created = False
                #either add a new commcare_auth token or retrieve an old one
                try:
                    if request.POST['auth_token'] != '':
                        commcare_token, created = ThirdPartyTokens.objects.get_or_create(user=request.user,name=provider,token=request.POST['auth_token'],username=request.POST['username'])
                        form = CommCareAuthForm(request.POST, choices=choices)
                        if form.is_valid():
                            pass
                except Exception as e:
                    commcare_token = ThirdPartyTokens.objects.get(user=request.user,name=provider)

                project = request.POST['project']
                url = url1 + project + url2
                response = requests.get(url, headers={'Authorization': 'ApiKey %(u)s:%(a)s' % {'u' : commcare_token.username, 'a' : commcare_token.token}})
                if response.status_code == 401:
                    messages.error(request, "Invalid username, authorization token or project.")
                    try:
                        token = ThirdPartyTokens.objects.get(user=request.user, name="CommCare")
                        token.delete()
                    except Exception as e:
                        pass
                    form = CommCareAuthForm(choices=choices)
                elif response.status_code == 200:
                    response_data = json.loads(response.content)
                    total_cases = response_data.get('meta').get('total_count')
                    if created: commcare_token.save()
                    #add the silo and reads if necessary
                    try:
                        silo_id = int(request.POST.get("silo", None))
                        if silo_id == 0: silo_id = None
                    except Exception as e:
                        return HttpResponse("Silo ID can only be an integer")

                    # try:
                    read, read_created = Read.objects.get_or_create(read_name="%s cases" % project, owner=request.user,
                        defaults={'read_url': url, 'type': ReadType.objects.get(read_type=provider), 'description': ""})
                    if read_created: read.save()
                    # except Exception as e:
                    #     return HttpResponse("Invalid name and/or URL")

                    silo, silo_created = Silo.objects.get_or_create(id=silo_id, defaults={"name": "%s cases" % project, "public": False, "owner": request.user})
                    if silo_created or read_created:
                        silo.reads.add(read)
                    elif read not in silo.reads.all():
                        silo.reads.add(read)

                    #get the actual data
                    auth = {'Authorization': 'ApiKey %(u)s:%(a)s' % {'u' : commcare_token.username, 'a' : commcare_token.token}}
                    getCommCareCaseData(project, auth, True, total_cases, silo, read)
                    cols = getSiloColumnNames(silo.id)

                else:
                    messages.error(request, "A %s error has occured: %s " % (response.status_code, response.text))
                    form = CommCareAuthForm(choices=choices)
            except KeyboardInterrupt as e:
                form = CommCareAuthForm(request.POST, choices=choices)
                form.is_valid()
        else:
            try:
                #look for authorization token
                commcare_token = ThirdPartyTokens.objects.get(user=request.user,name=provider)
            except Exception as e:
                form = CommCareAuthForm(request.POST, choices=choices)

    else:
        try:
            #look for authorization token
            commcare_token = ThirdPartyTokens.objects.get(user=request.user,name=provider)
            form = CommCareProjectForm(choices=choices)
            auth = 0
        except Exception as e:
            form = CommCareAuthForm(choices=choices)

    return render(request, 'getcommcareforms.html', {'form': form, 'data': cols, 'auth': auth})

@login_required
def getCommCareFormPass(request):
    data = {}
    form = None
    provider = "CommCare"

    #this version works without the token
    url = "" #url to get the data contained
    url1 = "https://www.commcarehq.org/a/"
    url2 = "/api/v0.5/simplereportconfiguration/?format=json"
    usrn = None
    pwd = None
    project = None

    if request.method == 'POST':
        form = CommCarePassForm(request.POST) #add the username and password to the request
        if form.is_valid(): #does the form meet requierements
            project = request.POST['project']
            url = url1 + project + url2
            response = requests.get(url, auth=HTTPDigestAuth(request.POST['username'], request.POST['password'])) #request the user data with a password and username
            if response.status_code == 401:
                messages.error(request, "Invalid username, password or project.")
            elif response.status_code == 200:
                data = json.loads(response.content) #load json into data
                data = data['objects']
                usrn = request.POST['username']
                usrn = base64.b64encode(usrn)
                pwd = request.POST['password']
                pwd = base64.b64encode(pwd)
                project = base64.b64encode(project)

            else:
                messages.error(request, "A %s error has occured: %s " % (response.status_code, response.text))
    else:
        form = CommCarePassForm()


    silos = Silo.objects.filter(owner=request.user)
    return render(request, 'getcommcareforms.html', {'form': form, 'data': data, 'silos': silos, 'usrn' : usrn, 'pwd' : pwd, 'project' : project, 'auth' : 2})


@login_required
def saveCommCareData(request):
    RECORDS_PER_STORAGE = 10000
    RECORDS_PER_REQUEST = 100

    """
    Saves CommCare read if not already in the db and then imports its data
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("HTTP method, %s, is not supported" % request.method)

    #first check to see if their is authorization
    commcare_token = None
    provider = "CommCare"
    try:
        commcare_token = ThirdPartyTokens.objects.get(user=request.user,name=provider)
    except Exception as e:
        pass

    read_type = ReadType.objects.get(read_type="CommCare")
    read_name = request.POST.get('read_name', None)
    silo_name = request.POST.get('silo_name', None)
    data_id = request.POST.get('data_id', None)
    usrn = None
    pwd = None
    if not commcare_token:
        usrn = request.POST.get('asiufjoiawenowe', None)
        usrn = base64.b64decode(usrn)
        pwd = request.POST.get('reoihgweboqwe', None)
        pwd = base64.b64decode(pwd)
    project = request.POST.get('no24jrfindaibanoif', None)
    project = base64.b64decode(project)
    owner = request.user
    description = request.POST.get('description', None)
    silo_id = None
    read = None
    silo = None



    # Fetch the first page of data from CommCare
    #use usrn and pwd to get authorization
    url = "https://www.commcarehq.org/a/"+ project+"/api/v0.5/configurablereportdata/"+ data_id+"/?format=json&offset=" + str(0)
    response = None
    if commcare_token:
        response = requests.get(url, headers={'Authorization': 'ApiKey %(u)s:%(a)s' % {'u' : commcare_token.username, 'a' : commcare_token.token}})
    else:
        response = requests.get(url, auth=HTTPDigestAuth(usrn, pwd))
    if response.status_code != 200:
        messages.error(request, "A %s error has occured: %s " % (response.status_code, response.text))
        return HttpResponseRedirect(reverse_lazy('getCommCareAuth'))



    metadata = json.loads(response.content)
    useHeaderName(metadata['columns'],metadata['data'])

    #run everything once and create new silo if needed

    data = metadata['data']

    try:
        silo_id = int(request.POST.get("silo_id", None))
        if silo_id == 0: silo_id = None
    except Exception as e:
         return HttpResponse("Silo ID can only be an integer")

    try:
        read, read_created = Read.objects.get_or_create(read_name=read_name, owner=owner,
            defaults={'read_url': url, 'type': read_type, 'description': description})
        if read_created: read.save()
    except Exception as e:
        return HttpResponse("Invalid name and/or URL")

    existing_silo_cols = []
    new_cols = []
    show_mapping = False

    silo, silo_created = Silo.objects.get_or_create(id=silo_id, defaults={"name": silo_name, "public": False, "owner": owner})
    if silo_created or read_created:
        silo.reads.add(read)
    elif read not in silo.reads.all():
        silo.reads.add(read)

    if len(data) == 0:
        return HttpResponse("There is no data for the selected form, %s" % read_name)

    # import data into this silo
    saveDataToSilo(silo, data, read)

    if commcare_token:
        auth={'Authorization': 'ApiKey %(u)s:%(a)s' % {'u' : commcare_token.username, 'a' : commcare_token.token}}
        auth_header = True
    else:
        auth=HTTPDigestAuth(usrn, pwd)
        auth_header = False

    #since the data is paged get data on the future pages
    # this is the parallized method
    # do this in groups of 10,000 to not exceed RAM
    import time
    start = time.time()
    if metadata['total_records'] > RECORDS_PER_REQUEST:
        data_collects = []
        for offset_start in xrange(RECORDS_PER_REQUEST, metadata['total_records'], RECORDS_PER_STORAGE):

            if offset_start + RECORDS_PER_STORAGE < metadata['total_records']:
                data_raw = fetchCommCareData(project,data_id,RECORDS_PER_REQUEST,auth,auth_header, offset_start + RECORDS_PER_STORAGE, offset_start)
            else:
                data_raw = fetchCommCareData(project,data_id,RECORDS_PER_REQUEST,auth,auth_header, metadata['total_records'], offset_start)
            data_collects.append(data_raw.apply_async())
        while len(data_collects) > 0:
            data_retrieval = [v.get() for v in data_collects.pop()]
            data = []
            for lst in data_retrieval:
                data.extend(lst)
            saveDataToSilo(silo, data, read)
    end = time.time()
    print (start-end)

    return HttpResponse("View table data at <a href='/silo_detail/%s' target='_blank'>See your data</a>" % silo.pk)

@login_required
def commcareLogout(request):
    try:
        token = ThirdPartyTokens.objects.get(user=request.user, name="CommCare")
        token.delete()
    except Exception as e:
        pass

    messages.error(request, "You have been logged out of your CommCare account.  Any Tables you have created with this account ARE still available, but you must log back in here to update them.")
    return HttpResponseRedirect(reverse_lazy('getCommCareAuth'))
