"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase
from django.test import Client
from django.test import RequestFactory

from tola.util import ona_parse_type_group
from silo.models import *

class onaParserTest(TestCase):
    """
    this tests the two recurseive Ona parser testing both the default one that does groups and the secondary one that does repeats
    """
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="joe", email="joe@email.com", password="tola123")
        self.read_type = ReadType.objects.create(read_type="Ona")
        self.silo = Silo.objects.create(name="test_silo1",public=0, owner = self.user)
        self.read = Read.objects.create(read_name="test_read1", owner = self.user, type=self.read_type)

    def test_onaParserOneLayer(self):
        label_file_data = [
            {
                "type":"text",
                "name":"a",
                "label":"aa"
            },
            {
                "type":"text",
                "name":"b",
            }
        ]
        data = [
            {
                "a":"1",
                "b":"2"
            },
            {
                "a":"3"
            },
            {
                "b":"4"
            },
            {
                "c":"5"
            }
        ]
        data_final = [
            {
                "aa":"1",
                "b":"2"
            },
            {
                "aa":"3"
            },
            {
                "b":"4"
            },
            {
                "c":"5"
            }
        ]
        ona_parse_type_group(data, label_file_data, "", self.silo, self.read)
        try: ColumnType.objects.filter(silo_id=self.silo.pk,read_id=self.read.pk,column_name="aa",column_source_name="a",column_type="text")
        except ColumnType.DoesNotExist as e:
            self.assert_(False)
        try: ColumnType.objects.filter(silo_id=self.silo.pk,read_id=self.read.pk,column_name="b",column_source_name="b",column_type="text")
        except ColumnType.DoesNotExist as e:
            self.assert_(False)
        self.assertEqual(data,data_final)
        #since the unit_test doesn't automatically delete entries in the mongodb database do it now
        ColumnType.objects.filter(silo_id=self.silo.pk,read_id=self.read.pk,column_name="aa",column_source_name="a",column_type="text").delete()
        ColumnType.objects.filter(silo_id=self.silo.pk,read_id=self.read.pk,column_name="b",column_source_name="b",column_type="text").delete()
    def test_onaParserTwoLayer(self):
        label_file_data = [
            {
                "type":"group",
                "name":"a",
                "label":"aa",
                "children": [
                    {
                        "type":"text",
                        "name":"b",
                        "label":"bb"
                    },
                    {
                        "type":"text",
                        "name":"c",
                    }
                ]
            },
            {
                "type":"repeat",
                "name":"d",
                "children": [
                    {
                        "type":"text",
                        "name":"e",
                        "label":"ee"
                    },
                    {
                        "type":"text",
                        "name":"f",
                    }
                ]
            },
        ]
        data = [
            {
                "a/b":"1",
                "a/c":"2",
                "d": [
                    {
                        "d/e" : "3",
                        "d/f" : "4",
                    },
                    {
                        "d/e" : "5",
                    },
                    {
                        "d/f" : "6",
                    }
                ]
            },
            {
                "a/b":"1",
                "d": [
                    {
                        "d/e" : "3",
                        "d/f" : "4",
                    },
                    {
                        "d/e" : "5",
                    },
                    {
                        "d/f" : "6",
                    }
                ]
            },
            {
                "d": [
                    {
                        "d/e" : "3",
                        "d/f" : "4",
                    },
                    {
                        "d/e" : "5",
                    },
                    {
                        "d/f" : "6",
                    }
                ]
            },
            {
            },
        ]
        data_final = [
            {
                "bb":"1",
                "a/c":"2",
                "d": [
                    {
                        "ee" : "3",
                        "d/f" : "4",
                    },
                    {
                        "ee" : "5",
                    },
                    {
                        "d/f" : "6",
                    }
                ]
            },
            {
                "bb":"1",
                "d": [
                    {
                        "ee" : "3",
                        "d/f" : "4",
                    },
                    {
                        "ee" : "5",
                    },
                    {
                        "d/f" : "6",
                    }
                ]
            },
            {
                "d": [
                    {
                        "ee" : "3",
                        "d/f" : "4",
                    },
                    {
                        "ee" : "5",
                    },
                    {
                        "d/f" : "6",
                    }
                ]
            },
            {
            },
        ]
        ona_parse_type_group(data, label_file_data, "", self.silo, self.read)
        try: ColumnType.objects.get(silo_id=self.silo.pk,read_id=self.read.pk,column_name="aa",column_source_name="a",column_type="group")
        except ColumnType.DoesNotExist as e:
            self.assert_(False)
        try: ColumnType.objects.get(silo_id=self.silo.pk,read_id=self.read.pk,column_name="bb",column_source_name="b",column_type="text")
        except ColumnType.DoesNotExist as e:
            self.assert_(False)
        try: ColumnType.objects.get(silo_id=self.silo.pk,read_id=self.read.pk,column_name="c",column_source_name="c",column_type="text")
        except ColumnType.DoesNotExist as e:
            self.assert_(False)
        try: ColumnType.objects.get(silo_id=self.silo.pk,read_id=self.read.pk,column_name="d",column_source_name="d",column_type="repeat")
        except ColumnType.DoesNotExist as e:
            self.assert_(False)
        self.assertEqual(data,data_final)
        #since the unit_test doesn't automatically delete entries in the mongodb database do it now
        ColumnType.objects.filter(silo_id=self.silo.pk,read_id=self.read.pk,column_name="aa",column_source_name="a",column_type="group").delete()
        ColumnType.objects.filter(silo_id=self.silo.pk,read_id=self.read.pk,column_name="bb",column_source_name="b",column_type="text").delete()
        ColumnType.objects.filter(silo_id=self.silo.pk,read_id=self.read.pk,column_name="c",column_source_name="c",column_type="text").delete()
        ColumnType.objects.filter(silo_id=self.silo.pk,read_id=self.read.pk,column_name="d",column_source_name="d",column_type="repeat").delete()
    def test_onaParserTwoLayer(self):
        label_file_data = [
            {
                "type":"repeat",
                "name":"rep",
                "children" : [
                    {
                        "type":"group",
                        "name":"a",
                        "label":"aa",
                        "children": [
                            {
                                "type":"text",
                                "name":"b",
                                "label":"bb"
                            },
                            {
                                "type":"text",
                                "name":"c",
                            }
                        ]
                    },
                    {
                        "type":"repeat",
                        "name":"d",
                        "children": [
                            {
                                "type":"text",
                                "name":"e",
                                "label":"ee"
                            },
                            {
                                "type":"text",
                                "name":"f",
                            }
                        ]
                    },
                ]
            }
        ]
        data = [
            {
                "rep":[
                    {
                        "rep/a/b":"1",
                        "rep/a/c":"2",
                        "rep/d": [
                            {
                                "rep/d/e" : "3",
                                "rep/d/f" : "4",
                            },
                            {
                                "rep/d/e" : "5",
                            },
                            {
                                "rep/d/f" : "6",
                            }
                        ]
                    },
                    {
                        "rep/a/b":"1",
                        "rep/d": [
                            {
                                "rep/d/e" : "3",
                                "rep/d/f" : "4",
                            },
                            {
                                "rep/d/e" : "5",
                            },
                            {
                                "rep/d/f" : "6",
                            }
                        ]
                    },
                    {
                        "rep/d": [
                            {
                                "rep/d/e" : "3",
                                "rep/d/f" : "4",
                            },
                            {
                                "rep/d/e" : "5",
                            },
                            {
                                "rep/d/f" : "6",
                            }
                        ]
                    },
                    {
                    },
                ]
            }
        ]
        data_final = [
            {
                "rep":[
                    {
                        "bb":"1",
                        "rep/a/c":"2",
                        "rep/d": [
                            {
                                "ee" : "3",
                                "rep/d/f" : "4",
                            },
                            {
                                "ee" : "5",
                            },
                            {
                                "rep/d/f" : "6",
                            }
                        ]
                    },
                    {
                        "bb":"1",
                        "rep/d": [
                            {
                                "ee" : "3",
                                "rep/d/f" : "4",
                            },
                            {
                                "ee" : "5",
                            },
                            {
                                "rep/d/f" : "6",
                            }
                        ]
                    },
                    {
                        "rep/d": [
                            {
                                "ee" : "3",
                                "rep/d/f" : "4",
                            },
                            {
                                "ee" : "5",
                            },
                            {
                                "rep/d/f" : "6",
                            }
                        ]
                    },
                    {
                    },
                ]
            }
        ]
        ona_parse_type_group(data, label_file_data, "", self.silo, self.read)
        try: ColumnType.objects.get(silo_id=self.silo.pk,read_id=self.read.pk,column_name="bb",column_source_name="b",column_type="text")
        except ColumnType.DoesNotExist as e:
            self.assert_(False)
        try: ColumnType.objects.get(silo_id=self.silo.pk,read_id=self.read.pk,column_name="c",column_source_name="c",column_type="text")
        except ColumnType.DoesNotExist as e:
            self.assert_(False)
        try: ColumnType.objects.get(silo_id=self.silo.pk,read_id=self.read.pk,column_name="rep",column_source_name="rep",column_type="repeat")
        except ColumnType.DoesNotExist as e:
            self.assert_(False)
        self.assertEqual(data,data_final)
        #since the unit_test doesn't automatically delete entries in the mongodb database do it now
        ColumnType.objects.filter(silo_id=self.silo.pk,read_id=self.read.pk,column_name="rep",column_source_name="rep",column_type="repeat").delete()
        ColumnType.objects.filter(silo_id=self.silo.pk,read_id=self.read.pk,column_name="bb",column_source_name="b",column_type="text").delete()
        ColumnType.objects.filter(silo_id=self.silo.pk,read_id=self.read.pk,column_name="c",column_source_name="c",column_type="text").delete()
