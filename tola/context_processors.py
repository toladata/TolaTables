from silo.models import *
from settings.local import ACTIVITY_URL
from settings.local import TABLES_URL


def get_silos(self):
    if self.user.is_authenticated():
        all_my_silos = Silo.objects.filter(owner=self.user)
    else:
        all_my_silos = Silo.objects.none()
    return {"all_my_silos": all_my_silos}


# get the organization labels from the user for each level of workflow for display in templates
def get_servers(request):

    try:
        activity_url = ACTIVITY_URL
        tables_url = TABLES_URL
    except Exception, e:
        activity_url = "http://activity.toladata.io"
        tables_url = "http://tables.toladata.io"


    return {'ACTIVITY_URL': activity_url, 'TABLES_URL': tables_url}