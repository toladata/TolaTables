from django.test import TestCase
from bson import ObjectId

import json
from tola.util import JSONEncoder


class RegisterViewTest(TestCase):
    def test_json_encoder(self):
        dict_test = {
            '_id': ObjectId("5aaf820a58d8e7002c889905"),
            'silo_id': 2,
            'read_id': 2,
            'county': "CLAY COUNTY",
            'tiv_2011': 60946.79,
            'statecode': 'FL',
            'policy_id': 353022
        }

        with self.assertRaises(TypeError):
            json.dumps(dict_test)

        encoded = JSONEncoder().encode(dict_test)
        self.assertTrue(isinstance(encoded, str))
