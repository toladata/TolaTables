import json
import requests
import base64

from requests.auth import HTTPDigestAuth
from django.http import HttpResponseRedirect, HttpResponseBadRequest, HttpResponse


from tola.util import saveDataToSilo, getSiloColumnNames
from django.shortcuts import redirect, render
from django.core.urlresolvers import reverse, reverse_lazy

from django.contrib import messages
from django.utils import timezone
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
    user_id = request.user.id
    total_cases = 0
    for silo in silos:
        choices.append((silo.pk, silo.name))

    if request.method == 'POST':
        #their exists a project and authorization so get the data
        form = CommCareProjectForm(request.POST, choices=choices, user_id=user_id)

        if form.is_valid():
            try:
                created = False
                #either add a new commcare_auth token or retrieve an old one
                try:
                    if request.POST['auth_token'] != '':
                        commcare_token, created = ThirdPartyTokens.objects.get_or_create(user=request.user,name=provider,token=request.POST['auth_token'],username=request.POST['username'])
                        form = CommCareAuthForm(request.POST, choices=choices, user_id=user_id)
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
                    form = CommCareAuthForm(choices=choices, user_id=user_id)
                elif response.status_code == 200:
                    response_data = json.loads(response.content)
                    total_cases = response_data.get('meta').get('total_count')
                    if created: commcare_token.save()
                    #add the silo and reads if necessary
                    try:
                        silo_id = int(request.POST.get("silo", None))
                        if silo_id == 0:
                            silo_id = None
                    except Exception as e:
                        return HttpResponse("Silo ID can only be an integer")

                    # try:
                    read, read_created = Read.objects.get_or_create(read_name="%s cases" % project, owner=request.user,
                        defaults={'read_url': url, 'type': ReadType.objects.get(read_type=provider), 'description': ""})
                    if read_created: read.save()
                    # except Exception as e:
                    #     return HttpResponse("Invalid name and/or URL")

                    new_silo_name = request.POST.get('new_silo_name', None)
                    silo, silo_created = Silo.objects.get_or_create(id=silo_id, defaults={"name": new_silo_name, "public": False, "owner": request.user})
                    if silo_created or read_created:
                        silo.reads.add(read)
                    elif read not in silo.reads.all():
                        silo.reads.add(read)

                    #get the actual data
                    authorization = {'Authorization': 'ApiKey %(u)s:%(a)s' % {'u' : commcare_token.username, 'a' : commcare_token.token}}
                    ret = getCommCareCaseData(project, authorization, True, total_cases, silo, read)
                    messages.add_message(request,ret[0],ret[1])
                    #need to impliment if import faluire
                    cols = ret[2]
                    return HttpResponseRedirect(reverse_lazy("siloDetail", kwargs={'silo_id' : silo.id}))

                else:
                    messages.error(request, "A %s error has occured: %s " % (response.status_code, response.text))
                    form = CommCareAuthForm(choices=choices, user_id=user_id)
            except KeyboardInterrupt as e:
                form = CommCareAuthForm(request.POST, choices=choices, user_id=user_id)
                form.is_valid()
        else:
            try:
                #look for authorization token
                commcare_token = ThirdPartyTokens.objects.get(user=request.user,name=provider)
            except Exception as e:
                form = CommCareAuthForm(request.POST, choices=choices, user_id=user_id)

    else:
        try:
            #look for authorization token
            commcare_token = ThirdPartyTokens.objects.get(user=request.user,name=provider)
            form = CommCareProjectForm(choices=choices, user_id=user_id)
            auth = 0
        except Exception as e:
            form = CommCareAuthForm(choices=choices, user_id=user_id)

    return render(request, 'getcommcareforms.html', {'form': form, 'data': cols, 'auth': auth, 'entries': total_cases, 'time' : timezone.now()})

@login_required
def getCommCareFormPass(request):
    cols = []
    form = None
    provider = "CommCare"

    #this version works without the token
    url = "" #url to get the data contained
    url1 = "https://www.commcarehq.org/a/"
    url2 = "/api/v0.5/case/?format=JSON&limit=1"
    project = None
    silos = Silo.objects.filter(owner=request.user)
    choices = [(0, ""), (-1, "Create new silo")]
    user_id = request.user.id
    total_cases = 0
    for silo in silos:
        choices.append((silo.pk, silo.name))

    if request.method == 'POST':
        form = CommCarePassForm(request.POST, choices=choices, user_id=user_id) #add the username and password to the request
        if form.is_valid(): #does the form meet requierements
            project = request.POST['project']
            url = url1 + project + url2
            response = requests.get(url, auth=HTTPDigestAuth(request.POST['username'], request.POST['password'])) #request the user data with a password and username
            if response.status_code == 401:
                messages.error(request, "Invalid username, password or project.")
            elif response.status_code == 200:
                response_data = json.loads(response.content)
                total_cases = response_data.get('meta').get('total_count')
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

                silo_name = request.POST.get('new_silo_name', "%s cases" % (project))
                silo, silo_created = Silo.objects.get_or_create(id=silo_id, defaults={"name": silo_name, "public": False, "owner": request.user})
                if silo_created or read_created:
                    silo.reads.add(read)
                elif read not in silo.reads.all():
                    silo.reads.add(read)

                #get the actual data
                auth = {"u" : request.POST['username'], "p" : request.POST['password']}
                ret = getCommCareCaseData(project, auth, False, total_cases, silo, read)
                #need to impliment if import faluire
                messages.add_message(request,ret[0],ret[1])
                cols = ret[2]
                return HttpResponseRedirect(reverse_lazy("siloDetail", kwargs={'silo_id' : silo.id}))

            else:
                messages.error(request, "A %s error has occured: %s " % (response.status_code, response.text))
    else:
        form = CommCarePassForm(choices=choices, user_id=user_id)


    return render(request, 'getcommcareforms.html', {'form': form, 'data': cols, 'auth': 2, 'entries': total_cases})


@login_required
def commcareLogout(request):
    try:
        token = ThirdPartyTokens.objects.get(user=request.user, name="CommCare")
        token.delete()
    except Exception as e:
        pass

    messages.error(request, "You have been logged out of your CommCare account.  Any Tables you have created with this account ARE still available, but you must log back in here to update them.")
    return HttpResponseRedirect(reverse_lazy('getCommCareAuth'))
