import logging
import requests
import json
from urlparse import urljoin

from django.conf import settings
from requests.exceptions import MissingSchema

logger = logging.getLogger(__name__)


def _get_headers():
    if settings.TOLA_ACTIVITY_API_TOKEN:
        headers = {
            "content-type": "application/json",
            'Authorization': 'Token {}'.format(
                settings.TOLA_ACTIVITY_API_TOKEN)
        }
    else:
        headers = {
            "content-type": "application/json"
        }
    return headers


def get_workflowteams(**kwargs):
    headers = _get_headers()

    url_subpath = 'api/workflowteam/'
    url_base = urljoin(settings.TOLA_ACTIVITY_API_URL, url_subpath)

    params = ['{}={}'.format(k, v) for k, v in kwargs.iteritems()]
    query_params = '&'.join(params)

    url = '{}?{}'.format(url_base, query_params)
    response = requests.get(url, headers=headers)
    content = []

    if response.status_code == 200:
        content = json.loads(response.content)
    else:
        logger.warn('{}: {}'.format(response.status_code, response.content))
    return content


def get_by_url(url):
    if not url:
        return None

    headers = _get_headers()
    response = requests.get(url, headers=headers)
    content = {}
    if response.status_code == 200:
        content = json.loads(response.content)
    else:
        logger.warn('{}: {}'.format(response.status_code, response.content))
    return content


def get_workflowlevel1s(user):
    try:
        params = {
            'workflow_user__tola_user_uuid': user.tola_user.tola_user_uuid,
            'nested_models': True
        }
        wfteams = get_workflowteams(**params)
        wfl1_uuids = []
        for wfteam in wfteams:
            if wfteam['workflowlevel1']:
                wfl1 = wfteam['workflowlevel1']
                if wfl1:
                    wfl1_uuids.append(wfl1['level1_uuid'])
        return wfl1_uuids
    except MissingSchema:
        return []
