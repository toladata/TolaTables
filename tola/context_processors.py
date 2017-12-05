from django.conf import settings
from silo.models import Silo


def google_oauth_settings(self):
    return {
        'GOOGLE_API_CLIENT_ID': settings.GOOGLE_API_CLIENT_ID,
        'GOOGLE_API_KEY': settings.GOOGLE_API_KEY,
    }


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

def google_analytics(request):
    """
    Use the variables returned in this function to render Google Analytics Tracking Code template.
    """

    ga_prop_id = getattr(settings, 'GOOGLE_ANALYTICS_PROPERTY_ID', False)
    if not settings.DEBUG and ga_prop_id:
        return {'google_prop_id': ga_prop_id}
    return {}
