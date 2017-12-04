from django.conf import settings
from silo.models import Silo


def get_silos(self):
    if self.user.is_authenticated():
        all_my_silos = Silo.objects.filter(owner=self.user)
    else:
        all_my_silos = Silo.objects.none()
    return {"all_my_silos": all_my_silos}


def get_servers(request):
    return {
        'ACTIVITY_URL': settings.ACTIVITY_URL,
        'TABLES_URL': settings.TABLES_URL,
    }
