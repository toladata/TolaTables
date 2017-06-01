from __future__ import unicode_literals

from django.db import models

from silo.models import ThirdPartyTokens

# Create your models here.
class ThirdPartyTokensUsername(ThirdPartyTokens):
    username = models.CharField(max_length=60)
