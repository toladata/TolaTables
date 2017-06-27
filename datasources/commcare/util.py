
from silo.models import Read, ReadType
from django.contrib import messages

from celery import group

from .tasks import fetchCommCareData, requestCommCareData, storeCommCareData

from silo.models import LabelValueStore
from tola.util import saveDataToSilo

#this gets a list of projects that users have used in the past to import data from commcare
#used in commcare/forms.py
def getProjects():
    reads = Read.objects.filter(type__read_type='CommCare')
    projects = []
    for read in reads:
        projects.append(read.read_url.split('/')[4])
    return list(set(projects))

def useHeaderName(columns, data):
    """
    since the commcare dictionary does not use the proper column names and instead uses column
    idnetifiers this funciton changes the dictionary to use the proper column names
    used in commcoare/views.py for saveCommCareData
    """
    for row in data:
        for column in columns:
            row[column['header']] = row.pop(column['slug'])

def getCommCareCaseData(domain, auth, auth_header, total_cases, silo, read):
    """
    Use fetch and request CommCareData to store all of the case data

    domain -- the domain name used for a commcare project
    auth -- the authorization required
    auth_header -- True = use Header, False = use Digest authorization
    total_cases -- total cases to get
    silo - silo to put the data into
    read -- read that the data is apart of
    """


    RECORDS_PER_REQUEST = 100
    base_url = "https://www.commcarehq.org/a/"+ domain\
                +"/api/v0.5/case/?format=JSON&limit="+str(RECORDS_PER_REQUEST)

    #import the cases in groups of 10000

    import time
    start = time.time()
    data_raw = fetchCommCareData(base_url, auth, auth_header,\
                    0, total_cases, RECORDS_PER_REQUEST, silo.id, read.id)
    data_collects = data_raw.apply_async()
    data_retrieval = [v.get() for v in data_collects]
    columns = set()
    for data in data_retrieval:
        columns = columns.union(data)

    print (time.time()-start)
    return (messages.SUCCESS, "CommCare cases imported successfully", columns)
