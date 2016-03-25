import json
import requests

from django.core.urlresolvers import reverse
from django.http import HttpResponseForbidden,\
    HttpResponseRedirect, HttpResponseNotFound, HttpResponseBadRequest,\
    HttpResponse, HttpResponseRedirect, JsonResponse

from django.utils import timezone
from django.utils.encoding import smart_str

from .models import *

def prep_data(silo_data):
    headers = []
    data = []
    for r, row in enumerate(silo_data):
        row_dict = {}
        for i, col in enumerate(row):
            #print("row:%s col:%s" % (r, i))
            if r == 0:
                col_parts = col.split("/")
                last_part_of_col = col_parts[(len(col_parts) - 1)]
                headers.append(last_part_of_col)
            else:
                print("%s = %s" % (headers[i], smart_str(row[col])))
                row_dict[headers[i]] = smart_str(row[col])
        if not row_dict: continue
        data.append(row_dict)
    return data


def export_to_tola_activity(request, id):
    silo = Silo.objects.get(pk=id)
    silo_data = LabelValueStore.objects(silo_id=id)

    data = prep_data(silo_data)

    url = "https://tola-activity-dev.mercycorps.org/api/agreements/"
    payload = {"some": data}
    headers = {"content-type": "application/json"}

    #r = requests.post(url, data=json.dumps(payload), headers=headers)

    #print(r.text)
    #return HttpResponse(r.text)
    return HttpResponse(data)