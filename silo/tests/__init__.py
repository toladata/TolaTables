import logging

from django.test import SimpleTestCase
from django.conf import settings
from mongoengine import connect
from mongoengine.connection import get_db
import pymongo

logger = logging.getLogger(__name__)


class MongoTestCase(SimpleTestCase):
    def __init__(self, methodName='runtest'):
        conn_params = {
            'db': settings.MONGODB_DATABASES['default']['name'],
            'username': settings.MONGODB_DATABASES['default']['username'],
            'password': settings.MONGODB_DATABASES['default']['password'],
            'host': settings.MONGODB_DATABASES['default']['host'],
            'port': settings.MONGODB_DATABASES['default']['port'],
        }
        connect(**conn_params)
        try:
            self.db = get_db()
        except pymongo.errors.OperationFailure as error:
            logger.error('Error when connecting to mongodb. Params %s. '
                         'Details: %s', conn_params, error)
            raise
        super(MongoTestCase, self).__init__(methodName)

    def _drop_collections(self):
        for collection in self.db.collection_names():
            if collection.startswith('system.'):
                continue
            self.db.drop_collection(collection)

    def tearDown(self):
        self._drop_collections()
