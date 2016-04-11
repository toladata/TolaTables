import json
import requests
import logging

from django.core.urlresolvers import reverse
from django.conf import settings
from django.http import HttpResponseForbidden,\
    HttpResponseRedirect, HttpResponseNotFound, HttpResponseBadRequest,\
    HttpResponse, HttpResponseRedirect, JsonResponse
from django.http import JsonResponse
from django.utils import timezone
from django.utils.encoding import smart_str

from .models import *
#curl -X GET https://tola-activity-demo.mercycorps.org/api/users/ -H 'Authorization: Token 59aadc96265c9d7fabcf1f35df9aed23c7196dd6'
#curl -X GET http://localhost:8000/api/read/ -H 'Authorization: Token 77b2224a904cec44f9964664e07c5de9a818ff67'

logger = logging.getLogger("silo")
url = settings.TOLA_ACTIVITY_API_URL + "agreements/"
auth_headers = {"content-type": "application/json", 'Authorization': settings.TOLA_ACTIVITY_API_TOKEN}


def prep_data(silo_data):
    headers = []
    data_failed_to_post = []
    for r, row in enumerate(silo_data):
        print(r)
        row_dict = {}
        for i, col in enumerate(row):
            col_parts = col.split("/")
            last_part_of_col = col_parts[(len(col_parts) - 1)]
            if last_part_of_col == "program" or last_part_of_col == "Program":
                val = settings.TOLA_ACTIVITY_API_URL + "programs/" + smart_str(row[col]) + "/"
            else:
                val = smart_str(row[col])
            row_dict[last_part_of_col] = val
        if not row_dict: continue
        payload = json.dumps(row_dict)
        res = requests.post(url, headers=auth_headers, data=payload)
        if res.status_code != 201:
            logger.error("Project Agreement (%s) for program (%s) failed to get created in TolaActivity" % (row_dict.get("program", None), row_dict.get("project_name", None)))
            data_failed_to_post.append(row_dict)
    return data_failed_to_post


def export_to_tola_activity(request, id):
    silo = Silo.objects.get(pk=id)
    silo_data = LabelValueStore.objects(silo_id=id)

    data_failed_to_post = prep_data(silo_data)

    if len(data_failed_to_post) == 0:
        json_formatted_data = {"status": "Data pushed successfully to TolaActivity"}
    else:
        json_formatted_data = {"status": "failed_agreements", "data": data_failed_to_post }
    return JsonResponse(json_formatted_data)
