from django.shortcuts import render
from silo.models import Country, Silo, User, TolaUser, LabelValueStore, UniqueFields
from django.db.models import Q

import json
import ast

# import the logging library
import logging

# Get an instance of a logger
logger = logging.getLogger('django')


def listTableDashboards(request,id=0):

    user = User.objects.get(username__exact=request.user)
    tola_user = TolaUser.objects.get(user__username__exact=request.user)
    get_tables = Silo.objects.filter(Q(owner=user) | Q(organization=tola_user.organization) | Q(shared=user))

    return render(request, "reports/table_list.html", {'get_tables': get_tables})


import itertools


def tableDashboard(request,id=0):
    """
    Dynamic Dashboard report based on Table Data
    find lat and long fields

    :return:
    """
    # get all countires
    countries = Country.objects.all()
    get_table = Silo.objects.get(id=id)
    try:
        get_init_fields = UniqueFields.objects.get(silo__id=id)
    except UniqueFields.DoesNotExist:
        get_init_fields = None
    doc = LabelValueStore.objects(silo_id=id).to_json()

    try:
        data = ast.literal_eval(doc)
    except ValueError:
        data = json.loads(doc)

    from collections import Counter
    latitude = []
    longitude = []
    lat_long = {}
    country = {}

    # each field needs a count of unique answers
    if get_init_fields is None and data:
        get_fields = {}
        # loop over the field names only
        for field in data[0]:
            # to-do move these into models
            exclude_string = ['read_id','silo_id','_id','formhub/uuid','meta/instanceID','user_assigned_id','meta/instanceName','create_date']
            map_lat_string = ['lat', 'latitude', 'x']
            map_long_string = ['long','lng','longitude', 'y']
            map_country_string = ['countries','country']
            map_location = ['location', 'coordinated','coord']
            if field not in exclude_string:
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
                """
                TODO: Needs to be moved to a recursive function that checks each level for
                list or dict and continues to parse until a count can be found
                """
                for a in answers:
                    # if answer has a dict or list count each element
                    if isinstance(a, dict):
                        for x in a.keys():
                            cnt[x] += 1
                    elif isinstance(a, list):
                        # if a list within a list
                        for x in a:
                            if isinstance(x, dict):
                                for y in x.keys():
                                    cnt[y] += 1
                            else:
                                cnt[x] += 1
                    else:
                        cnt[a] += 1
                    unique_count = cnt

                # append unique answer plus count to dict
                get_fields[field][idx] = unique_count.most_common()

                from django.utils.safestring import SafeString
                import unicodedata

                temp = []
                temp2 = []
                for letter, count in get_fields[field][idx]:

                    if isinstance(letter,unicode):
                        temp.append(SafeString(unicodedata.normalize('NFKD', letter).encode('ascii', 'ignore')))
                    else:
                        temp.append(letter)
                    temp2.append(count)

                try:
                    find_none = temp.index(None)
                    temp[find_none] = 'None'
                except ValueError:
                    temp = temp

                get_fields[field][idx] = {"label": SafeString(temp), "count": SafeString(temp2)}


            # if a latitude string add it to the map list
            if field in map_lat_string:
                for idx, col in enumerate(data):
                    latitude.append(col[field])

            # if a longitude string add it to the map list
            if field in map_long_string:
                for idx, col in enumerate(data):
                    longitude.append(col[field])

            # if a longitude string add it to the map list
            if field in map_location:
                for idx, col in enumerate(data):
                    latitude.append(itertools.islice(col[field].iteritems(), 3, 4))
                    longitude.append(itertools.islice(col[field].iteritems(), 4, 5))

            # if a country name
            if field in map_country_string:
                for idx, col in enumerate(data):
                    country_obj=Country.objects.get(country=col[field])
                    longitude.append(country_obj.longitude)
                    latitude.append(country_obj.latitude)
                    country.append(country_obj.country)

            # merge lat and long
            lat_long = dict(zip(latitude,longitude))

    else:
        get_fields = None

    try:
        columns = ast.literal_eval(get_table.columns)
    except ValueError:
        columns = json.loads(get_table.columns)

    return render(request, "reports/table_dashboard.html",
                  {'data': data, 'get_table': get_table, 'countries': countries, 'get_fields': get_fields,
                   'lat_long': lat_long,'country': country, 'columns': columns})





