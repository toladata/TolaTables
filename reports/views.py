from django.views.generic.list import ListView
from django.http import HttpResponse

from django.shortcuts import render
from silo.models import WorkflowLevel2, WorkflowLevel1, Country, TolaSites, Silo, User, TolaUser, LabelValueStore, UniqueFields
from django.db.models import Sum
from django.db.models import Q

from django.contrib.auth.decorators import login_required
import requests
import json
import ast


def listTableDashboards(request,id=0):

    user = User.objects.get(username__exact=request.user)
    tola_user = TolaUser.objects.get(user__username__exact=request.user)
    get_tables = Silo.objects.filter(Q(owner=user) | Q(organization=tola_user.organization) | Q(shared=user))

    return render(request, "reports/table_list.html", {'get_tables': get_tables})


def tableDashboard(request,id=0):
    """
    DEMO only survey for Tola survey for use with public talks about TolaData
    Share URL to survey and data will be aggregated in tolatables
    then imported to this dashboard
    :return:
    """
    # get all countires
    countries = Country.objects.all()
    get_table = Silo.objects.get(id=id)
    try:
        get_fields = UniqueFields.objects.get(silo__id=id)
    except UniqueFields.DoesNotExist:
        get_fields = None
    doc = LabelValueStore.objects(silo_id=id).to_json()

    data = ast.literal_eval(doc)

    from collections import Counter
    latitude = {}
    longitude = {}
    lat_long = {}
    country = {}
    # each field needs a count of unique answers
    if get_fields is None and data:
        get_fields = {}
        # loop over the field names only
        for field in data[0]:
            # to-do move these into models
            exclude_string = ['read_id','silo_id','_id','formhub/uuid','meta/instanceID','user_assigned_id','meta/instanceName']
            map_lat_string = ['lat', 'latitude', 'x']
            map_long_string = ['long', 'longitude', 'y']
            map_country_string = ['countries','country']
            if str(field) not in exclude_string:
                get_fields[field] = {} # create a dict with fields as the key
                cnt = Counter()
                answers = [] # a list for the answers
                for idx, col in enumerate(data):
                    # get_fields[field][idx] = col[field] # append list of all answers
                    try:
                        answers.append(col[field]) # append list of answers
                    except KeyError:
                        answers.append(None)  # no answer
                # loop and count each unique answer
                for a in answers:
                    # if answer has a dict in it loop over that
                    if isinstance(a, dict):
                        for x in a: cnt[x] +=1
                    else:
                        cnt[a] += 1
                    unique_count = cnt
                # append unique answer plus count to dict
                get_fields[field][idx] = unique_count.most_common()

                from django.utils.safestring import SafeString

                temp = []
                temp2 = []
                for letter, count in get_fields[field][idx]:
                    temp.append(str(letter))
                    temp2.append(str(count))

                get_fields[field][idx] = {"label": SafeString(temp), "count": SafeString(temp2)}
            # if a latitude string add it to the map list
            elif str(field) in map_lat_string:
                for idx, col in enumerate(data):
                    latitude[field].append(col[field])
            # if a longitude string add it to the map list
            elif str(field) in map_long_string:
                for idx, col in enumerate(data):
                    longitude[field].append(col[field])
        # merge lat and long
        lat_long = latitude.copy()
        lat_long.update(longitude)
 
    else:
        get_fields = None

    columns = ast.literal_eval(get_table.columns)

    return render(request, "reports/table_dashboard.html",
                  {'data': data, 'get_table': get_table, 'countries': countries, 'get_fields': get_fields,
                   'lat_long': lat_long, 'columns': columns})





