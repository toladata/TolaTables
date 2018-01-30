from django.shortcuts import render
from silo.models import Country, Silo, User, TolaUser, LabelValueStore, UniqueFields
from django.db.models import Q

import json
import ast



def listTableDashboards(request,id=0):

    user = User.objects.get(username__exact=request.user)
    tola_user = TolaUser.objects.get(user__username__exact=request.user)
    get_tables = Silo.objects.filter(Q(owner=user) | Q(organization=tola_user.organization) | Q(shared=user))

    return render(request, "reports/table_list.html", {'get_tables': get_tables})


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
        get_fields = UniqueFields.objects.get(silo__id=id)
    except UniqueFields.DoesNotExist:
        get_fields = None
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
    if get_fields is None and data:
        get_fields = {}
        # loop over the field names only
        for field in data[0]:
            # to-do move these into models
            exclude_string = ['read_id','silo_id','_id','formhub/uuid','meta/instanceID','user_assigned_id','meta/instanceName','create_date']
            map_lat_string = ['lat', 'latitude', 'x']
            map_long_string = ['long','lng','longitude', 'y']
            map_country_string = ['countries','country']
            if field not in exclude_string:
                get_fields[field] = {} # create a dict with fields as the key
                cnt = 0
                answers = [] # a list for the answers
                for idx, col in enumerate(data):
                    # get_fields[field][idx] = col[field] # append list of all answers
                    try:
                        answers.append(col[field]) # append list of answers
                    except KeyError:
                        answers.append(None)  # no answer
                # loop and count each unique answer
                """
                TODO: Needs to be moved to a recurssive function that checks each level for
                list or dict and continues to parse until it can be counted
                """
                for a in answers:
                    # if answer has a dict or list count each element
                    cnt = cnt + 1

                unique_count = cnt
                # append unique answer plus count to dict
                get_fields[field][idx] = unique_count

                from django.utils.safestring import SafeString

                temp = []
                temp2 = []
                for letter in get_fields[field]:
                    # u' '.join((agent_contact, agent_telno)).encode('utf-8').strip()
                    temp.append(letter)
                    temp2.append(get_fields[field][idx])

                get_fields[field][idx] = {"label": SafeString(temp), "count": SafeString(temp2)}

            # if a latitude string add it to the map list
            if field in map_lat_string:
                for idx, col in enumerate(data):
                    latitude.append(col[field])

            # if a longitude string add it to the map list
            if field in map_long_string:
                for idx, col in enumerate(data):
                    longitude.append(col[field])

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

    columns = ast.literal_eval(get_table.columns)

    return render(request, "reports/table_dashboard.html",
                  {'data': data, 'get_table': get_table, 'countries': countries, 'get_fields': get_fields,
                   'lat_long': lat_long,'country': country, 'columns': columns})





