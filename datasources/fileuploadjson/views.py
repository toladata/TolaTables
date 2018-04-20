import json
import requests
import datetime


from django.http import HttpResponseRedirect
from django.utils import timezone
from django.shortcuts import render
from tola.util import save_data_to_silo
from django.core.urlresolvers import reverse, reverse_lazy

from django.contrib import messages

from silo.models import Silo, Read, ReadType, User
from silo.forms import UploadForm, get_read_form
from .forms import get_json_form

# Create your views here.

def jsonuploadfile(request,id):
    initial = {'owner': request.user}
    excluded_fields = ['gsheet_id', 'resource_id', 'token', 'create_date', 'edit_date', 'token', 'username', 'password', 'autopush_frequency', 'autopull_frequency', 'read_url']

    try:
        read_instance = Read.objects.get(pk=id)
        read_type = read_instance.type.read_type
    except Read.DoesNotExist as e:
        read_instance = None
        read_type = 'JSON'
        initial['type'] = ReadType.objects.get(read_type=read_type)

    if request.method == 'POST':
        form = get_json_form(excluded_fields)(request.POST, request.FILES, instance=read_instance)
        if form.is_valid():
            if(request.FILES is None):
                messages.error(request,'Please select a file to upload')
            read = form.save(commit=False)
            read.save()
            return HttpResponseRedirect("/fileuploadjson/file/" + str(read.id) + "/")
        else:
            messages.error(request, 'Invalid Form', fail_silently=False)

    else:
        form = get_json_form(excluded_fields)(instance=read_instance, initial=initial)
    return render(request, 'read/read.html', {'form': form, 'read_id': id,})

def file(request, id):
    if request.method == 'POST':
        form = UploadForm(request.POST)
        if form.is_valid():
            read_obj = Read.objects.get(pk=id)
            user = User.objects.get(username__exact=request.user)

            if request.POST.get("new_silo", None):
                silo = Silo(name=request.POST['new_silo'], owner=user, public=False,
                            create_date=timezone.now())
                silo.save()
            else:
                silo = Silo.objects.get(id = request.POST["silo_id"])
            # try:
            silo.reads.add(read_obj)
            silo_id = silo.id
            data = json.load(read_obj.file_data)
            save_data_to_silo(silo, data, read_obj)
            return HttpResponseRedirect('/silo_detail/%s/' % silo_id)
            # except Exception as e:
            #     messages.error(request, "Your JSON file was formatted incorrectly")
            #     return HttpResponseRedirect('/fileuploadjson')
        else:
            messages.error(request, "There was a problem with reading the contents of your file" + form.errors)

    user = User.objects.get(username__exact=request.user)
    # get all of the silo info to pass to the form
    get_silo = Silo.objects.filter(owner=user)

    # display the form for user to choose a table or ener a new table name to import data into
    return render(request, 'read/file.html', {
        'read_id': id, 'form_action': reverse_lazy("fileupload", kwargs={"id": id}), 'get_silo': get_silo,
    })
