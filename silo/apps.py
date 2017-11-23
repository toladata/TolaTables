import logging

from django.apps import AppConfig
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from mongoengine import connection

logger = logging.getLogger(__name__)


class SiloAppConfig(AppConfig):
    name = 'silo'
    verbose_name = "Silo"

    def ready(self):
        if not hasattr(settings, 'MONGODB_DATABASES'):
            raise ImproperlyConfigured(
                "Missing `MONGODB_DATABASES` in settings.py")

        for alias, conn_settings in settings.MONGODB_DATABASES.items():
            logger.info("Registering connection '%s' with args: %s",
                        alias, conn_settings)
            connection.register_connection(alias, **conn_settings)
