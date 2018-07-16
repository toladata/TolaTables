import httplib2
import os
import datetime
import logging
import json

from apiclient import discovery
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse, reverse_lazy
from django.http import (HttpResponseRedirect, HttpResponseBadRequest,
                         JsonResponse, HttpResponseNotAllowed, HttpResponse)
from django.utils import timezone
from django.utils.encoding import smart_text, smart_str
from oauth2client.client import (OAuth2Credentials, flow_from_clientsecrets,
                                 HttpAccessTokenRefreshError,
                                 OAuth2WebServerFlow)
from oauth2client.contrib.django_orm import Storage
from oauth2client.contrib import xsrfutil
from oauth2client.client import AccessTokenCredentialsError

from .models import GoogleCredentialsModel
from .models import Silo, Read, ReadType, LabelValueStore
from tola.util import (addColsToSilo, calculateFormulaCell, clean_data_obj,
                       cleanKey, getSiloColumnNames, makeQueryForHiddenRow,
                       parseMathInstruction)

logger = logging.getLogger('silo')

SCOPE = 'https://www.googleapis.com/auth/spreadsheets'
BASE_URL = 'https://sheets.googleapis.com/v4/spreadsheets/'
DISCOVERY_URL = 'https://sheets.googleapis.com/$discovery/rest?version=v4'
CLIENT_SECRETS_FILENAME = 'client_secrets.json'  # Mercy Corps feature


def _get_spreadsheet_url(spreadsheet_id):
    return "https://docs.google.com//spreadsheets/d/%s/" % str(spreadsheet_id)


def _get_oauth_flow():
    client_secrets = os.path.join(os.path.dirname(__file__),
                                  CLIENT_SECRETS_FILENAME)
    if settings.GOOGLE_OAUTH_CLIENT_ID and settings.GOOGLE_OAUTH_CLIENT_SECRET:
        flow = OAuth2WebServerFlow(
            client_id=settings.GOOGLE_OAUTH_CLIENT_ID,
            client_secret=settings.GOOGLE_OAUTH_CLIENT_SECRET,
            scope=SCOPE,
            redirect_uri=settings.GOOGLE_REDIRECT_URL)
    elif os.path.isfile(client_secrets):
        flow = flow_from_clientsecrets(
            client_secrets,
            scope=SCOPE,
            redirect_uri=settings.GOOGLE_REDIRECT_URL)
    else:
        raise ImproperlyConfigured(
            'GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET settings '
            'are missing')
    return flow


def _get_credential_object(user, prompt=None):
    storage = Storage(GoogleCredentialsModel, 'id', user, 'credential')
    credential_obj = storage.get()
    if credential_obj is None or credential_obj.invalid == True or prompt:
        flow = _get_oauth_flow()
        flow.params['state'] = xsrfutil.generate_token(settings.SECRET_KEY, user)
        flow.params['access_type'] = 'offline'
        flow.params['approval_prompt'] = 'force'
        authorize_url = flow.step1_get_authorize_url()
        return {
            "level": messages.ERROR,
            "msg": "Requires Google Authorization Setup",
            "redirect": authorize_url,
            "redirect_uri_after_step2": True
        }

    return credential_obj


def _get_authorized_service(credential_obj):
    http = credential_obj.authorize(httplib2.Http())
    service = discovery.build('sheets', 'v4', http=http,
                              discoveryServiceUrl=DISCOVERY_URL)
    return service


def _get_or_create_read(rtype, name, description, spreadsheet_id, user, silo):
    # If a 'read' object does not exist for this export action, then create it
    read_type = ReadType.objects.get(read_type=rtype)
    defaults = {"type": read_type,
                "read_name": name,
                "description": description,
                "read_url": _get_spreadsheet_url(spreadsheet_id),
                "owner": user}
    gsheet_read, created = Read.objects.get_or_create(silos__id=silo.pk,
                                                      silos__owner=user,
                                                      resource_id=spreadsheet_id,
                                                      defaults=defaults)
    if created:
        silo.reads.add(gsheet_read)
    return gsheet_read


def _get_gsheet_metadata(credential_obj, spreadsheet_id, user):
    """
    Get the sheet metada data from Google to name of the sheet and create a Read
    :param credential_obj: OAuth2Credentials object
    :param spreadsheet_id: integer
    :param user: User object
    :return: The name of the sheet, the Read, an error msg
             | (object, dict)
    """
    service = _get_authorized_service(credential_obj)
    try:
        spreadsheet = service.spreadsheets().get(
            spreadsheetId=spreadsheet_id).execute()
    except HttpAccessTokenRefreshError:
        error = {'credential': [_get_credential_object(user, True)]}
        return None, error
    except Exception as e:
        error = json.loads(e.content).get('error')
        msg = '{}: {}'.format(error.get("status"), error.get("message"))
        error = {'level': messages.ERROR, 'msg': msg}
        return None, error

    return spreadsheet, None


def _fetch_data_gsheet(credential_obj, spreadsheet_id, sheet_name):
    """
    Fetch the table data from Google Spreadsheet
    :param credential_obj: OAuth2Credentials object
    :param spreadsheet_id: integer
    :param sheet_name: string
    :return: the data, an error msg | (object, dict)
    """
    service = _get_authorized_service(credential_obj)
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, range=sheet_name).execute()
        values = result.get('values', [])
    except Exception as e:
        logger.error(e)
        msg = {
            'level': messages.ERROR,
            'msg': 'Something went wrong 22: {}'.format(e),
            'redirect': None
        }
        return None, msg
    else:
        return values, None


def _convert_gsheet_data(headers, values):
    """
    Convert the data from GSheet into a list of dict
    :param headers: list of keys(column names)
    :param values: the GSheet data - list(list)
    :return: list(dict)
    """
    data = []
    for row in values:
        data_dict = {}
        for c, col in enumerate(row[:len(headers)]):
            data_dict.update({headers[c]: col})
        if data_dict:
            data.append(data_dict)

    return data


def import_from_gsheet_helper(user, silo_id, silo_name, spreadsheet_id,
                              sheet_id=None, partialcomplete=False):
    msgs = []
    if spreadsheet_id is None:
        msgs.append({
            'level': messages.ERROR,
            'msg': 'A Google Spreadsheet is not selected to import data from.',
            'redirect': reverse('index')
        })

    credential_obj = _get_credential_object(user)
    if not isinstance(credential_obj, OAuth2Credentials):
        msgs.append(credential_obj)
        return msgs

    defaults = {
        'name': silo_name,
        'description': 'Google Sheet Import',
        'public': False,
        'owner': user
    }
    silo, created = Silo.objects.get_or_create(
        pk=None if silo_id == '0' else silo_id, defaults=defaults)
    msgs.append({'silo_id': silo.id})

    metadata, error = _get_gsheet_metadata(credential_obj, spreadsheet_id, user)
    if error:
        if 'credential' in error:
            return error.get('credential')
        else:
            msgs.append(error)
            return msgs

    spreadsheet_name = metadata.get('properties', {}).get('title', '')
    gsheet_read = _get_or_create_read(
        'GSheet Import', spreadsheet_name, 'Google Spreadsheet Import',
        spreadsheet_id, user, silo)
    if sheet_id:
        gsheet_read.gsheet_id = sheet_id
        gsheet_read.save()

    sheet_name = 'Sheet1'
    if gsheet_read.gsheet_id:
        sheets = metadata.get('sheets', None)
        for sheet in sheets:
            properties = sheet.get('properties', None)
            if properties:
                if str(properties.get('sheetId')) == str(gsheet_read.gsheet_id):
                    sheet_name = properties.get('title')

    values, error = _fetch_data_gsheet(credential_obj, spreadsheet_id,
                                       sheet_name)
    if error:
        msgs.append(error)
        return msgs

    unique_fields = silo.unique_fields.all()
    skipped_rows = set()
    headers = []
    lvss = []

    # get the column names
    header = values.pop(0)
    for h in header:
        h = cleanKey(h)
        headers.append(h)

    data = _convert_gsheet_data(headers, values)

    for r, row in enumerate(data):
        filter_criteria = {}
        # build filter_criteria if unique field(s) have been setup for this silo
        for uf in unique_fields:
            try:
                if str(row[uf.name]).isdigit():
                    filter_criteria.update({str(uf.name): int(row[uf.name])})
                else:
                    filter_criteria.update({str(uf.name): str(row[uf.name])})
            except AttributeError as e:
                logger.warning(e)
        if filter_criteria:
            filter_criteria.update({'silo_id': silo.id})
            try:
                lvs = LabelValueStore.objects.get(**filter_criteria)
                lvs.edit_date = timezone.now()
            except LabelValueStore.DoesNotExist:
                lvs = LabelValueStore()
            except LabelValueStore.MultipleObjectsReturned:
                for k, v in filter_criteria.iteritems():
                    skipped_rows.add('{}={}'.format(k, v))
                continue
        else:
            lvs = LabelValueStore()

        # add the key and values to the document
        row = clean_data_obj(row)
        for key, val in row.iteritems():
            val = smart_str(val, strings_only=True)
            setattr(lvs, key, val)

        lvs.silo_id = silo.id
        lvs.read_id = gsheet_read.id
        lvs.create_date = timezone.now()
        lvs = calculateFormulaCell(lvs, silo)
        if partialcomplete:
            lvss.append(lvs)
        else:
            lvs.save()
    addColsToSilo(silo, headers)

    if skipped_rows:
        skipped_str = ','.join(str(s) for s in skipped_rows)
        msg = 'Skipped updating/adding records where {} because there are ' \
              'already multiple records.'.format(skipped_str)
        msgs.append({
            'level': messages.WARNING,
            'msg': msg
        })

    msgs.append({'level': messages.SUCCESS, 'msg': 'Operation successful'})
    if partialcomplete:
        return lvss, msgs
    return msgs


@login_required
def import_from_gsheet(request, id):
    gsheet_endpoint = None
    silo = None
    read_url = request.GET.get('link', None)
    spreadsheet_id = request.GET.get('resource_id', None)
    sheet_id = request.GET.get("sheet_id", None)
    silo_name = request.GET.get("name", "Google Sheet Import")

    msgs = import_from_gsheet_helper(request.user, id, silo_name, spreadsheet_id, sheet_id)
    google_auth_redirect = "/import_gsheet/%s/?link=%s&resource_id=%s" % (id, read_url, spreadsheet_id)
    for msg in msgs:
        if "silo_id" in msg.keys(): id = msg.get("silo_id")
        if "redirect_uri_after_step2" in msg.keys():
            request.session['redirect_uri_after_step2'] = google_auth_redirect
            return HttpResponseRedirect(msg.get("redirect"))
        messages.add_message(request, msg.get("level", "warning"), msg.get("msg", None))

    return HttpResponseRedirect(reverse_lazy('silo_detail', kwargs={'silo_id': str(id)},))


def export_to_gsheet_helper(user, spreadsheet_id, silo_id, query, headers):
    msgs = []
    credential_obj = _get_credential_object(user)
    if not isinstance(credential_obj, OAuth2Credentials):
        msgs.append(credential_obj)
        return msgs

    service = _get_authorized_service(credential_obj)

    try:
        silo = Silo.objects.get(pk=silo_id)
    except Exception as e:
        logger.error("Silo with id=%s does not exist" % silo_id)
        msgs.append({"level": messages.ERROR,
                    "msg": "Silo with id=%s does not exist" % silo_id,
                    "redirect": reverse('list_silos')})
        return msgs

    try:
        # if no spreadsheet_id is provided, then create a new spreadsheet
        if spreadsheet_id is None:
            # create a new google spreadsheet
            body = {"properties":{"title": silo.name}}
            spreadsheet = service.spreadsheets().create(body=body).execute()
            spreadsheet_id = spreadsheet.get("spreadsheetId", None)
        else:
            # fetch the google spreadsheet metadata
            spreadsheet = service.spreadsheets().get(spreadsheetId=
                                                     spreadsheet_id).execute()
    except HttpAccessTokenRefreshError:
        return [_get_credential_object(user, True)]
    except Exception as e:
        error = json.loads(e.content).get("error")
        msg = "%s: %s" % (error.get("status"), error.get("message"))
        msgs.append({"level": messages.ERROR,
                    "msg": msg})
        return msgs

    # get spreadsheet metadata
    spreadsheet_name = spreadsheet.get("properties", {}).get("title", "")
    sheet = spreadsheet.get('sheets', '')[0]
    title = sheet.get("properties", {}).get("title", "Sheet1")
    sheet_id = sheet.get("properties", {}).get("sheetId", 0)

    gsheet_read = _get_or_create_read("Google Spreadsheet",
                                      spreadsheet_name,
                                      "Google Spreadsheet Export",
                                      spreadsheet_id,
                                      user,
                                      silo)

    # get the meta-data from other sheets
    other_title = []
    other_sheet_id = []
    if len(spreadsheet.get('sheets','')) > 0:
        for other_sheet in spreadsheet.get('sheets','')[1:]:
            other_title.append(other_sheet.get("properties", {}).get(
                "title", ""))
            other_sheet_id.append(other_sheet.get("properties", {}).get(
                "sheetId", 0))

    # the first element in the array is a placeholder for column names
    rows = [{"values": []}]
    silo_data = json.loads(LabelValueStore.objects(silo_id=silo_id,
                                                   **query).to_json())
    repeat_headers = []
    repeat_data = {}
    repeat_cells = {}

    for y, row in enumerate(silo_data):
        # Get all of the values of a single mongodb document into this array
        values = []
        for x, header in enumerate(headers):
            try:
                if type(row[header]) == list:
                    if header == 'sys__geolocation':
                        geo_string = ",".join(
                            [str(h) for h in list(row[header])])
                        values.append({"userEnteredValue":
                                           {"stringValue":
                                                smart_text(geo_string)}})
                    elif len(row[header]) > 0:
                        try:
                            repeat_data[header].append(row[header])
                        except KeyError as e:
                            repeat_data[header] = [row[header]]
                        repeat_cells[header] = (x,y+1)
                        values.append({"userEnteredValue":
                                           {"stringValue":  smart_text(
                                               header)}})
                        if header not in repeat_headers \
                                and header not in other_title:
                            repeat_headers.append(header)
                    else:
                        values.append({"userEnteredValue":
                                           {"stringValue": ""}})
                else:
                    value = smart_text(row[header])
                    if header == '_id':
                        value = smart_text(row[header]['$oid'])

                    values.append({"userEnteredValue": {
                        "stringValue": value}})

            except KeyError:
                values.append({"userEnteredValue": {"stringValue": ""}})
        rows.append({"values": values})

    # prepare column names as a header row in spreadsheetxw
    values = []
    for header in headers:
        if header == '_id':
            header = 'id'

        values.append({"userEnteredValue": {"stringValue": header},
                       'userEnteredFormat': {'backgroundColor':
                             {'red': 0.5, 'green': 0.5, 'blue': 0.5}}})
    # Now update the rows array place holder with real column names
    rows[0]["values"] = values

    # batch all of remote api calls into the requests array
    requests = []

    # Add extra sheets for repeats
    for header in repeat_headers:
        requests.append({
            "addSheet" : {
                "properties": {
                  "title": header,
                  "gridProperties": {
                    "rowCount": (len(repeat_data[header][0])+1)*len(
                        repeat_data[header]),
                    "columnCount": len(repeat_data[header][0][0])
                  },
                  "tabColor": {
                    "red": 1.0,
                    "green": 0.3,
                    "blue": 0.4
                  }
                }
            }
        })

    # prepare the request to resize the sheet to make sure it fits the data;
    # otherwise, errors out for datasets with more than 26 column or 1000 rows.
    requests.append({
        'updateSheetProperties': {
            'properties': {
                'sheetId': sheet_id,
                "title": title,
                "gridProperties": {
                    'rowCount': len(rows),
                    'columnCount': len(headers),
                }
            },
            "fields": "title,gridProperties(rowCount,columnCount)"
        }
    })

    # Now prepare the request to push data to gsheet
    requests.append({
        'updateCells': {
            'start': {'sheetId': sheet_id, 'rowIndex': 0, 'columnIndex': 0},
            'rows': rows,
            'fields': 'userEnteredValue,userEnteredFormat.backgroundColor'
        }
    })

    # encapsulate the requests list into a requests object
    batchUpdateRequest = {'requests': requests}

    try:
        response = service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id, body=batchUpdateRequest).execute()
        msgs.append({"level": messages.SUCCESS,
                    "msg": "Your exported data is available at <a href=" +
                           gsheet_read.read_url + " target='_blank'>Google "
                                                  "Spreadsheet</a>"})
    except Exception as e:
        msgs.append({"level": messages.ERROR,
                    "msg": "Failed to submit data to GSheet. %s" % e})
        return msgs

    # if their is no repeat data we are done
    if len(repeat_cells) == 0:
        return msgs

    # use the response to get the sheetid for new sheets added
    for reply in response['replies']:
        try:
            other_title.append(reply.get("addSheet").get("properties").get(
                "title"))
            other_sheet_id.append(reply.get("addSheet").get(
                "properties").get("sheetId"))
        except (KeyError,AttributeError):
            pass
    if len(other_title) != len(other_sheet_id):
        msgs.append({"level": messages.ERROR,
                    "msg": "Failed to submit repeat data to GSheet %s" % e})
        return msgs

    requests = []
    # Add repeats data to the new sheet
    # goes through each sheet
    for i in range(0, len(other_title)):
        rows = [{"values": []}]
        for j, row_set in enumerate(repeat_data.get(other_title[i],[])):
            headers = []
            rows.append({"values":
                            [{"userEnteredValue":
                                  {"stringValue": "From row ""%i" % j},
                              'userEnteredFormat': {'backgroundColor': {
                                'red':0.75,'green':0.75, 'blue': 0.75}}
                            }]
            })
            for row in row_set:
                values = []
                for index, col in enumerate(row):
                    if col not in headers:
                        headers.append(col)
                    values.append(
                        {"userEnteredValue":
                             {"stringValue": smart_text(row[headers[index]])}})
                rows.append({"values": values})

        # prepare column names as a header row in spreadsheet
        values = []
        for header in headers:
            values.append({
                          "userEnteredValue": {"stringValue": header},
                          'userEnteredFormat': {'backgroundColor': {
                              'red': 0.5, 'green': 0.5, 'blue': 0.5}}
                          })

        # Now update the rows array place holder with real column names
        rows[0]["values"] = values

        requests.append({
            'updateSheetProperties': {
                'properties': {
                    'sheetId': other_sheet_id[i],
                    "gridProperties": {
                        'rowCount': len(rows),
                        'columnCount': len(headers),
                    }
                },
                "fields": "gridProperties(rowCount,columnCount)"
            }
        })

        requests.append({
            "updateCells": {
                "range": {
                  "sheetId": other_sheet_id[i],
                },
                "fields": "userEnteredValue,userEnteredFormat"
              }
            }
        )

        requests.append({
            'updateCells': {
                'start': {'sheetId': other_sheet_id[i], 'rowIndex': 0,
                          'columnIndex': 0},
                'rows': rows,
                'fields': 'userEnteredValue,userEnteredFormat.backgroundColor'
            }
        })
        rows = []
        x_cord = repeat_cells.get(other_title[i],(0,0))[0]
        y_cord = repeat_cells.get(other_title[i],(0,0))[1]
        for j in range(0, y_cord):
            rows.append({"values": [
                        {"userEnteredValue":
                             {"formulaValue": "=HYPERLINK(\"#gid=%i\","
                                        "\"See Data\")" % other_sheet_id[i]
                        }}
                ]})
        # Get hyperlink to actually work
        if len(rows) > 0:
            requests.append({
                'updateCells': {
                    'start': {'sheetId': sheet_id, 'rowIndex': 1,
                              'columnIndex': x_cord},
                    'rows': rows,
                    'fields': 'userEnteredValue',
                },
            })

    # Send second request
    batchUpdateRequest = {'requests': requests}

    try:
        request = service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id, body=batchUpdateRequest)
        request.execute()
    except Exception as e:
        msgs.append({"level": messages.ERROR,
                    "msg": "Failed to submit repeat data to GSheet. %s" % e})

    return msgs


@login_required
def export_to_gsheet(request, id):
    spreadsheet_id = request.GET.get("resource_id", None)
    query = json.loads(request.GET.get('query', "{}"))
    if type(query) == list:
        query = json.loads(makeQueryForHiddenRow(query))

    cols_to_export = json.loads(request.GET.get('shown_cols', json.dumps(
        getSiloColumnNames(id))))

    cols_to_export.insert(0, '_id')

    msgs = export_to_gsheet_helper(request.user, spreadsheet_id, id, query,
                                   cols_to_export)

    google_auth_redirect = "export_to_gsheet/%s/" % id

    for msg in msgs:
        if "redirect_uri_after_step2" in msg.keys():
            request.session['redirect_uri_after_step2'] = google_auth_redirect
            return HttpResponseRedirect(msg.get("redirect"))
        messages.add_message(request, msg.get("level"), msg.get("msg"))

    return HttpResponseRedirect(reverse('list_silos'))


@login_required
def get_sheets_from_google_spreadsheet(request):
    spreadsheet_id = request.GET.get("spreadsheet_id", None)
    credential_obj = _get_credential_object(request.user)
    if not isinstance(credential_obj, OAuth2Credentials):
        request.session['redirect_uri_after_step2'] = request.META.get('HTTP_REFERER')
        return JsonResponse(credential_obj)

    service = _get_authorized_service(credential_obj)

    try:
        spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    except HttpAccessTokenRefreshError:
        return [_get_credential_object(request.user, True)]
    except Exception as e:
        error = json.loads(e.content).get("error")
        msg = "%s: %s" % (error.get("status"), error.get("message"))
        return JsonResponse({"level": messages.ERROR, "msg": msg}, status=403)
    return JsonResponse(spreadsheet)


@login_required
def oauth2callback(request):
    if not xsrfutil.validate_token(settings.SECRET_KEY,
                                   str(request.GET.get('state', '')),
                                   request.user):
        return HttpResponseBadRequest()

    flow = _get_oauth_flow()
    credential = flow.step2_exchange(request.GET)
    storage = Storage(GoogleCredentialsModel, 'id', request.user, 'credential')
    storage.put(credential)
    redirect_url = request.session['redirect_uri_after_step2']
    return HttpResponseRedirect(redirect_url)


@login_required
def store_oauth2_credential(request):
    if request.method == 'GET':
        return HttpResponseNotAllowed(['POST', 'OPTIONS'])

    data = request.POST

    if 'access_token' not in data:
        logger.info('Failed to retrieve access token')
        if 'error' in data:
            error_msg = (str(data['error']) +
                         str(data.get('error_description', '')))
        else:
            error_msg = 'Invalid response. No access token.'
        raise AccessTokenCredentialsError(error_msg)

    access_token = data['access_token']
    if 'refresh_token' in data:
        refresh_token = data['refresh_token']
    else:
        refresh_token = None
        logger.info(
            'Received token response with no refresh_token. Consider '
            "reauthenticating with approval_prompt='force'.")
    token_expiry = None
    if 'expires_in' in data:
        delta = datetime.timedelta(seconds=int(data['expires_in']))
        token_expiry = delta + datetime.datetime.utcnow()

    logger.info('Successfully retrieved access token')
    flow = _get_oauth_flow()
    credential = OAuth2Credentials(
        access_token, flow.client_id, flow.client_secret,
        refresh_token, token_expiry, flow.token_uri, flow.user_agent,
        revoke_uri=flow.revoke_uri, id_token=None,
        token_response=data, scopes=flow.scope,
        token_info_uri=flow.token_info_uri)

    storage = Storage(GoogleCredentialsModel, 'id', request.user, 'credential')
    storage.put(credential)
    return HttpResponse('{"detail": "The credential was successfully saved."}')
