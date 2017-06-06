
from silo.models import Read, ReadType

#this gets a list of projects that users have used in the past to import data from commcare
#used in commcare/forms.py
def getProjects():
    reads = Read.objects.filter(type__read_type='CommCare')
    projects = []
    for read in reads:
        projects.append(read.read_url.split('/')[4])
    return list(set(projects))

#since the commcare dictionary does not use the proper column names and instead uses column
#idnetifiers this funciton changes the dictionary to use the proper column names
#used in commcoare/views.py for saveCommCareData
def useHeaderName(columns, data):
    for row in data:
        for column in columns:
            row[column['header']] = row.pop(column['slug'])
