import os, logging, httplib2, json, datetime

from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponseBadRequest, JsonResponse

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

from oauth2client.client import flow_from_clientsecrets
from oauth2client.django_orm import Storage
from oauth2client import xsrfutil
from django.conf import settings
from django.views.decorators.csrf import csrf_protect
from .models import GoogleCredentialsModel
from apiclient.discovery import build
import gdata.spreadsheets.client


from .models import Silo, Read, ReadType, ThirdPartyTokens, LabelValueStore, Tag

CLIENT_SECRETS = os.path.join(os.path.dirname(__file__), 'client_secrets.json')
FLOW = flow_from_clientsecrets(
    CLIENT_SECRETS,
    scope='https://www.googleapis.com/auth/drive https://spreadsheets.google.com/feeds',
    redirect_uri=settings.GOOGLE_REDIRECT_URL)
    #redirect_uri='http://localhost:8000/oauth2callback/')

def import_from_google_spreadsheet(credential_json, silo_id, spreadsheet_key):


    # Create OAuth2Token for authorizing the SpreadsheetClient
    token = gdata.gauth.OAuth2Token(
        client_id = credential_json['client_id'],
        client_secret = credential_json['client_secret'],
        scope = 'https://spreadsheets.google.com/feeds',
        user_agent = "TOLA",
        access_token = credential_json['access_token'],
        refresh_token = credential_json['refresh_token'])

    # Instantiate the SpreadsheetClient object
    sp_client = gdata.spreadsheets.client.SpreadsheetsClient(source="TOLA")

    # authorize the SpreadsheetClient object
    sp_client = token.authorize(sp_client)
    #print(sp_client)


    # Create a WorksheetQuery object to allow for filtering for worksheets by the title
    # worksheet_query = gdata.spreadsheets.client.WorksheetQuery(title="Sheet1", title_exact=True)


    print("spreadsheet_key: %s" % spreadsheet_key)
    # Get a feed of all worksheets in the specified spreadsheet that matches the worksheet_query
    worksheets_feed = sp_client.get_worksheets(spreadsheet_key, query=None)
    #print("worksheets_feed: %s" % worksheets_feed)


    # Retrieve the worksheet_key from the first match in the worksheets_feed object
    worksheet_key = worksheets_feed.entry[0].id.text.rsplit("/", 1)[1]
    print("worksheet_key: %s" % worksheet_key)

    #for j, wsentry in enumerate(worksheets_feed.entry):
    wsentry = worksheets_feed.entry[0]
    print '%s - rows %s - cols %s\n' % (wsentry.title.text, wsentry.row_count.text, wsentry.col_count.text)
    #print(sp_client.get_cell(spreadsheet_key, worksheet_key, 1, 1))
    rows = int(wsentry.row_count.text)


    cells = sp_client.get_cells(spreadsheet_key, worksheet_key)
    #print(cells.entry[0])
    old_row = 1
    for rid in range(0, rows):
        if str(old_row) == cells.entry[rid].cell.row:
            print("old_row# %s VS row# %s val: %s" % (str(old_row), cells.entry[rid].cell.row, cells.entry[rid].cell.text))
        else:
            print("old_row# %s VS NEW row# %s val: %s" % (str(old_row), cells.entry[rid].cell.row, cells.entry[rid].cell.text))
            old_row = old_row + 1

    print("col: %s" % cells.entry[0].cell.col)
    print("row: %s" % cells.entry[0].cell.row)

    #list_feed = sp_client.get_list_feed(spreadsheet_key, worksheet_key)
    #print("PRINTING LIST FEEED:" )
    #print(list_feed.entry)

    silo_data = LabelValueStore.objects(silo_id=silo_id)

    cell_query = gdata.spreadsheets.client.CellQuery(range=None, return_empty='false')

    # Retrieve all cells thar match the query as a CellFeed
    cells_feed = sp_client.GetCells(spreadsheet_key, worksheet_key, q=cell_query)

    #print(type(cells.entry))
    print(cells_feed.entry[0].cell.text)


    return True


@login_required
def import_gsheet(request, id):
    gsheet_endpoint = None
    read_url = request.GET.get('link', None)
    file_id = request.GET.get('resource_id', None)
    if read_url == None or file_id == None:
        messages.error(request, "A Google Spreadsheet is not selected to import data from.")
        return HttpResponseRedirect(reverse('index'))

    storage = Storage(GoogleCredentialsModel, 'id', request.user, 'credential')
    credential = storage.get()
    if credential is None or credential.invalid == True:
        FLOW.params['state'] = xsrfutil.generate_token(settings.SECRET_KEY, request.user)
        authorize_url = FLOW.step1_get_authorize_url()
        #FLOW.params.update({'redirect_uri_after_step2': "/export_gsheet/%s/?link=%s&resource_id=%s" % (id, read_url, file_id)})
        request.session['redirect_uri_after_step2'] = "/import_gsheet/%s/?link=%s&resource_id=%s" % (id, read_url, file_id)
        return HttpResponseRedirect(authorize_url)

    credential_json = json.loads(credential.to_json())
    user = User.objects.get(username__exact=request.user)
    gsheet_endpoint = None
    read_type = ReadType.objects.get(read_type="GSheet Import")
    try:
        gsheet_endpoint = Read.objects.get(silos__id=id, type=read_type, silos__owner=user.id, resource_id=file_id, read_name='GSheet Import')
    except Read.MultipleObjectsReturned:
        print("this should not happen")
        messages.error(request, "There should not be multiple records for the same gsheet, silo, and owner")
    except Read.DoesNotExist:
        gsheet_endpoint = Read(read_name="GSheet Import", type=read_type, resource_id=file_id, owner=user)
        gsheet_endpoint.read_url = read_url
        gsheet_endpoint.save()
        silo = Silo.objects.get(id=id)
        silo.reads.add(gsheet_endpoint)
        silo.save()
    except Exception as e:
        messages.error(request, "An error occured: %" % e.message)

    #print("about to export to gsheet: %s" % gsheet_endpoint.resource_id)
    if import_from_google_spreadsheet(credential_json, id, gsheet_endpoint.resource_id) == True:
        link = "Your imported data is available at here."
        messages.success(request, link)
    else:
        messages.error(request, 'Something went wrong.')
    #messages.success(request, "Now, it should import data from GSheet")
    return HttpResponseRedirect(reverse('index'))