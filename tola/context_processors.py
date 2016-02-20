from silo.models import *

def get_silos(self):
    all_my_silos = Silo.objects.filter(owner=self.user)
    return {"all_my_silos": all_my_silos}