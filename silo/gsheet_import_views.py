import os, logging, httplib2, json, datetime

from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponseBadRequest, JsonResponse

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

from django.utils import timezone

from oauth2client.client import flow_from_clientsecrets
from oauth2client.django_orm import Storage
from oauth2client import xsrfutil
from django.conf import settings
from django.views.decorators.csrf import csrf_protect
from .models import GoogleCredentialsModel
from apiclient.discovery import build
import gdata.spreadsheets.client
from tola.util import siloToDict, combineColumns

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

    # Create a WorksheetQuery object to allow for filtering for worksheets by the title
    worksheet_query = gdata.spreadsheets.client.WorksheetQuery(title="Sheet1", title_exact=True)
    # Get a feed of all worksheets in the specified spreadsheet that matches the worksheet_query
    worksheets_feed = sp_client.get_worksheets(spreadsheet_key, query=None)

    # Retrieve the worksheet_key from the first match in the worksheets_feed object
    worksheet_key = worksheets_feed.entry[0].id.text.rsplit("/", 1)[1]

    ws = worksheets_feed.entry[0]
    print '%s - rows %s - cols %s\n' % (ws.title.text, ws.row_count.text, ws.col_count.text)
    lvs = LabelValueStore()



    list_feed = sp_client.get_list_feed(spreadsheet_key, worksheet_key)

    for row in list_feed.entry:
        row_data = row.to_dict()
        print(row_data)
        for key, val in row_data.iteritems():
            if key == "" or key is None or key == "silo_id": continue
            elif key == "id" or key == "_id": key = "user_assigned_id"
            elif key == "create_date": key = "created_date"
            elif key == "edit_date": key = "editted_date"
            setattr(lvs, key, val)
        lvs.silo_id = silo_id
        lvs.create_date = timezone.now()
        lvs.save()
        lvs = LabelValueStore()

    combineColumns(silo_id)
    """
    num_rows = int(ws.row_count.text)
    num_cols = int(ws.col_count.text)
    cells = sp_client.get_cells(spreadsheet_key, worksheet_key)
    prev_row = 2
    headings = []

    try:
        for rid in range(0, num_rows):
            if int(cells.entry[rid].cell.row) == 1:
                headings.append(cells.entry[rid].cell.text)
                continue

            curr_row = int(cells.entry[rid].cell.row)
            curr_col = int(cells.entry[rid].cell.col) -1

            val = cells.entry[rid].cell.text
            col_num = rid % len(headings)
            print("curr_col: %s VS col_num: %s" % (curr_col, col_num))
            key = headings[curr_col]

            if key == "" or key is None or key == "silo_id": continue
            elif key == "id" or key == "_id": key = "user_assigned_id"
            elif key == "create_date": key = "created_date"
            elif key == "edit_date": key = "editted_date"

            #print("prev_row #: %s row#: %s col_num: %s col: %s key: %s val: %s" % (prev_row, curr_row, col_num, curr_col, key, val))

            # if prev_row is less than current by more than 1, then there must have been empty rows.
            if prev_row + 1 < curr_row:
                prev_row = curr_row - 1

            if not prev_row == curr_row:
                if val == "" or val == None: continue
                prev_row = prev_row + 1
                # save the existing row as a label value store document
                lvs.create_date = timezone.now()
                lvs.save()

                # create a new label value store document for the new row.
                lvs = LabelValueStore()
                lvs.silo_id = silo_id
            setattr(lvs, key, val)
    except Exception as e:
        print(e)
        lvs.create_date = timezone.now()
        lvs.save()

    combineColumns(silo_id)

    """


    #-------------------------------
    # ListFeed
    #list_feed = sp_client.get_list_feed(spreadsheet_key, worksheet_key)
    #for en in list_feed.entry:
    #    print(en)
    #-------------------------------
    # CellsFeed
    #cell_query = gdata.spreadsheets.client.CellQuery(range=None, return_empty='false')
    # Retrieve all cells thar match the query as a CellFeed
    #cells_feed = sp_client.GetCells(spreadsheet_key, worksheet_key, q=cell_query)
    #print(cells_feed.entry[0].cell.text)
    #-------------------------------
    # retrieve a single cell
    #print(sp_client.get_cell(spreadsheet_key, worksheet_key, 1, 1))
    #-------------------------------

    #silo_data = LabelValueStore.objects(silo_id=silo_id)
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