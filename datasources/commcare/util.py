
from silo.models import Read


def getProjects():
    reads = Read.objects.filter(read_url__contains='www.commcarehq.org')
    projects = []
    for read in reads:
        projects.append(read.read_url.split('/')[4])
    return list(set(projects))
