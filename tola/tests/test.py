"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.


from django.utils import timezone
from datetime import datetime
from datetime import timedelta

from django.test import TestCase
from django.test import Client
from django.test import RequestFactory

import pymongo
from pymongo import MongoClient

from tola.util import *
from silo.models import *

client = MongoClient(settings.MONGO_URI)
db = client.get_database(settings.MONGODB_DATABASES['default']['name'])

class onaParserTest(TestCase):

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
        self.assertEqual(data,data_final)
        #since the unit_test doesn't automatically delete entries in the mongodb database do it now
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
        self.assertEqual(data,data_final)
        #since the unit_test doesn't automatically delete entries in the mongodb database do it now
    def test_onaParserThreeLayerByGroup(self):
        label_file_data = [
            {
                "type":"group",
                "name":"a",
                "label":"aa",
                "children": [
                    {
                        "type":"group",
                        "name":"b",
                        "children" : [
                            {
                                "type":"text",
                                "name":"c",
                                "label":"cc"
                            },
                            {
                                "type":"text",
                                "name":"d"
                            }
                        ]
                    },
                    {
                        "type":"text",
                        "name":"e",
                        "label":"ee"
                    }
                ]
            }
        ]
        data = [
            {
                "a/b/c":"1",
                "a/b/d":"2",
                "a/e":"3"
            },
            {
                "a/b/c":"1",
            },
            {
                "a/b/d":"2",
            },
            {
            },
        ]
        data_final = [
            {
                "cc":"1",
                "a/b/d":"2",
                "ee":"3"
            },
            {
                "cc":"1",
            },
            {
                "a/b/d":"2",
            },
            {
            },
        ]
        ona_parse_type_group(data, label_file_data, "", self.silo, self.read)
        self.assertEqual(data,data_final)
        #since the unit_test doesn't automatically delete entries in the mongodb database do it now
    def test_onaParserThreeLayer(self):
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
        self.assertEqual(data,data_final)
        #since the unit_test doesn't automatically delete entries in the mongodb database do it now


class columnManipulation(TestCase):


    def setUp(self):
        self.user = User.objects.create_user(username="joe", email="joe@email.com", password="tola123")
        self.silo = Silo.objects.create(name="test_silo1",public=0, owner = self.user)
    def test_manipulating_columns(self):
        columns = ["b", "a", "x", "4"]
        addColsToSilo(self.silo,columns)
        self.assertEqual(["b", "a", "x", "4"], getSiloColumnNames(self.silo.id))
        self.assertEqual({"b" : 'string', "a" : 'string', "x" : 'string', "4" : 'string'}, getColToTypeDict(self.silo))
        columns = ["c", "q", "3", "8"]
        addColsToSilo(self.silo,columns)
        self.assertEqual(["b", "a", "x", "4", "c", "q", "3", "8"], getSiloColumnNames(self.silo.id))
        columns = ["a", "r", "c", "e"]
        addColsToSilo(self.silo,columns)
        self.assertEqual(["b", "a", "x", "4", "c", "q", "3", "8", "r", "e"], getSiloColumnNames(self.silo.id))
        self.assertEqual(getSiloColumnNames(self.silo.id), getCompleteSiloColumnNames(self.silo.id))
        deleteSiloColumns(self.silo, ["a", "4", "3", "r", "e"])
        self.assertEqual(["b", "x", "c", "q", "8"], getSiloColumnNames(self.silo.id))
        self.assertEqual(getSiloColumnNames(self.silo.id), getCompleteSiloColumnNames(self.silo.id))
        hideSiloColumns(self.silo, ["b", "c"])
        self.assertEqual(["x", "q", "8"], getSiloColumnNames(self.silo.id))
        self.assertEqual(["b", "x", "c", "q", "8"], getCompleteSiloColumnNames(self.silo.id))
        self.assertEqual({"b" : 'string', "x" : 'string', "c" : 'string', "q" : 'string', "8" : 'string'}, getColToTypeDict(self.silo))


class formulaOperations(TestCase):


    def setUp(self):
        self.user = User.objects.create_user(username="joe", email="joe@email.com", password="tola123")
        self.silo = Silo.objects.create(name="test_silo1",public=0, owner = self.user)
        formulaColumn = FormulaColumn.objects.create(mapping=json.dumps(["a", "b", "c"]), operation="sum", column_name="sum")
        self.silo.formulacolumns.add(formulaColumn)
        formulaColumn = FormulaColumn.objects.create(mapping=json.dumps(["a", "b", "c"]), operation="mean", column_name="mean")
        self.silo.formulacolumns.add(formulaColumn)
        formulaColumn = FormulaColumn.objects.create(mapping=json.dumps(["a", "b", "c"]), operation="median", column_name="median")
        self.silo.formulacolumns.add(formulaColumn)
        formulaColumn = FormulaColumn.objects.create(mapping=json.dumps(["a", "b", "c"]), operation="mode", column_name="mode")
        self.silo.formulacolumns.add(formulaColumn)
        formulaColumn = FormulaColumn.objects.create(mapping=json.dumps(["a", "b", "c"]), operation="max", column_name="max")
        self.silo.formulacolumns.add(formulaColumn)
        formulaColumn = FormulaColumn.objects.create(mapping=json.dumps(["a", "b", "c"]), operation="min", column_name="min")
        self.silo.formulacolumns.add(formulaColumn)
    def test_str_nums(self):
        lvs = LabelValueStore()
        lvs.a = "1"
        lvs.b = "1.5"
        lvs.c = "1"
        calculateFormulaCell(lvs, self.silo)
        self.assertEqual(lvs['sum'], 3.5)
        self.assertEqual(lvs['mean'], 1.1667)
        self.assertEqual(lvs['median'], 1)
        self.assertEqual(lvs['mode'], 1)
        self.assertEqual(lvs['max'], 1.5)
        self.assertEqual(lvs['min'], 1)
    def test_float_nums(self):
        lvs = LabelValueStore()
        lvs.a = 3.1
        lvs.b = 3.1
        lvs.c = 4
        calculateFormulaCell(lvs, self.silo)
        self.assertEqual(lvs['sum'], 10.2)
        self.assertEqual(lvs['mean'], 3.4)
        self.assertEqual(lvs['median'], 3.1)
        self.assertEqual(lvs['mode'], 3.1)
        self.assertEqual(lvs['max'], 4)
        self.assertEqual(lvs['min'], 3.1)
    def test_int_nums(self):
        lvs = LabelValueStore()
        lvs.a = 1
        lvs.b = 3
        lvs.c = 5
        calculateFormulaCell(lvs, self.silo)
        self.assertEqual(lvs['sum'], 9)
        self.assertEqual(lvs['mean'], 3)
        self.assertEqual(lvs['median'], 3)
        self.assertEqual(lvs['mode'], 1)
        self.assertEqual(lvs['max'], 5)
        self.assertEqual(lvs['min'], 1)
    def test_empty(self):
        lvs = LabelValueStore()
        calculateFormulaCell(lvs, self.silo)
        self.assertEqual(lvs['sum'], "Error")
        self.assertEqual(lvs['mean'], "Error")
        self.assertEqual(lvs['median'], "Error")
        self.assertEqual(lvs['mode'], "Error")
        self.assertEqual(lvs['max'], "Error")
        self.assertEqual(lvs['min'], "Error")
    def test_sts(self):
        lvs = LabelValueStore()
        lvs.a = "a"
        lvs.b = "b"
        lvs.c = "c"
        calculateFormulaCell(lvs, self.silo)
        self.assertEqual(lvs['sum'], "Error")
        self.assertEqual(lvs['mean'], "Error")
        self.assertEqual(lvs['median'], "Error")
        self.assertEqual(lvs['mode'], "Error")
        self.assertEqual(lvs['max'], "Error")
        self.assertEqual(lvs['min'], "Error")
    def test_median(self):
        self.assertEqual(median([]), None)
        self.assertEqual(median([1,2]), 1.5)
    def test_mathParser(self):
        try:
            parseMathInstruction("a")
            self.assertTrue(False)
        except TypeError as e:
            a = str(e)
            self.assertEqual(a,'a')


class QueryMaker(TestCase):


    def test_blankQuery(self):
        self.assertEqual(makeQueryForHiddenRow([]),"{}")
    def test_queryEmpty(self):
        row_filter = [
            {
                "logic" : "BLANKCHAR",
                "operation": "",
                "number":"",
                "conditional": "---",
            },
            {
                "logic" : "AND",
                "operation": "empty",
                "number":"",
                "conditional": ["a","b"],
            },
            {
                "logic" : "OR",
                "operation": "empty",
                "number":"",
                "conditional": ["c","d"],
            }
        ]
        query = '{"a": {"$not": {"$exists": "true", "$not": {"$in": ["", "---"]}}}, "$or": [{"c": {"$not": {"$exists": "true", "$not": {"$in": ["", "---"]}}}}, {"d": {"$not": {"$exists": "true", "$not": {"$in": ["", "---"]}}}}], "b": {"$not": {"$exists": "true", "$not": {"$in": ["", "---"]}}}}'
        self.assertEqual(json.loads(makeQueryForHiddenRow(row_filter)), json.loads(query))

    def test_queryNempty(self):
        row_filter = [
            {
                "logic" : "BLANKCHAR",
                "operation": "",
                "number":"",
                "conditional": "---",
            },
            {
                "logic" : "AND",
                "operation": "nempty",
                "number":"",
                "conditional": ["a","b"],
            },
            {
                "logic" : "OR",
                "operation": "nempty",
                "number":"",
                "conditional": ["c","d"],
            }
        ]
        # print makeQueryForHiddenRow(row_filter)
        query = '{"a": {"$exists": "true", "$not": {"$in": ["", "---"]}}, "$or": [{"c": {"$exists": "true", "$not": {"$in": ["", "---"]}}}, {"d": {"$exists": "true", "$not": {"$in": ["", "---"]}}}], "b": {"$exists": "true", "$not": {"$in": ["", "---"]}}}'
        self.assertEqual(json.loads(makeQueryForHiddenRow(row_filter)), json.loads(query))
    def test_queryEqual(self):
        row_filter = [
            {
                "logic" : "BLANKCHAR",
                "operation": "",
                "number":"",
                "conditional": "---",
            },
            {
                "logic" : "AND",
                "operation": "eq",
                "number":"0",
                "conditional": ["a","b"],
            },
            {
                "logic" : "OR",
                "operation": "eq",
                "number":"0",
                "conditional": ["c","d"],
            }
        ]
        # print makeQueryForHiddenRow(row_filter)
        query = '{"a": {"$in": ["0", 0.0, 0]}, "$or": [{"c": {"$in": ["0", 0.0, 0]}}, {"d": {"$in": ["0", 0.0, 0]}}], "b": {"$in": ["0", 0.0, 0]}}'
        self.assertEqual(json.loads(makeQueryForHiddenRow(row_filter)), json.loads(query))
    def test_queryNotEqual(self):
        row_filter = [
            {
                "logic" : "BLANKCHAR",
                "operation": "",
                "number":"",
                "conditional": "---",
            },
            {
                "logic" : "AND",
                "operation": "neq",
                "number":"-1",
                "conditional": ["a","b"],
            },
            {
                "logic" : "OR",
                "operation": "neq",
                "number":"15",
                "conditional": ["c","d"],
            }
        ]
        # print makeQueryForHiddenRow(row_filter)
        query = '{"a": {"$nin": ["-1", -1.0, -1]}, "$or": [{"c": {"$nin": ["15", 15.0, 15]}}, {"d": {"$nin": ["15", 15.0, 15]}}], "b": {"$nin": ["-1", -1.0, -1]}}'
        self.assertEqual(json.loads(makeQueryForHiddenRow(row_filter)), json.loads(query))
    def test_queryColumnMultiple(self):
        row_filter = [
            {
                "logic" : "AND",
                "operation": "neq",
                "number":"0",
                "conditional": ["b"],
            },
            {
                "logic" : "AND",
                "operation": "neq",
                "number":"1",
                "conditional": ["b"],
            },
            {
                "logic" : "OR",
                "operation": "neq",
                "number":"2",
                "conditional": ["b"],
            },
            {
                "logic" : "OR",
                "operation": "neq",
                "number":"3",
                "conditional": ["b"],
            }
        ]
        # print makeQueryForHiddenRow(row_filter)
        query = '{"$or": [{"b": {"$nin": ["2", 2.0, 2, "3", 3.0, 3]}}], "b": {"$nin": ["0", 0.0, 0, "1", 1, 1.0]}}'
        self.assertEqual(json.loads(makeQueryForHiddenRow(row_filter)), json.loads(query))


class testDateNewest(TestCase):
    def test_newestDate(self):
        lvs = LabelValueStore()
        now = datetime.today()
        lvs.create_date = now
        lvs.silo_id = "-100"
        lvs.save()

        lvs = LabelValueStore()
        lvs.create_date = now + timedelta(days=1)
        lvs.silo_id = "-100"
        lvs.save()

        lvs = LabelValueStore()
        lvs.create_date = now + timedelta(days=-1)
        lvs.silo_id = "-100"
        lvs.save()
        self.assertEqual(getNewestDataDate(-100).date(), now.date() + timedelta(days=1))
        LabelValueStore.objects.filter(silo_id="-100").delete()


class test_saveDataToSilo(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="joe", email="joe@email.com", password="tola123")
        self.read_type = ReadType.objects.create(read_type="Ona")
        self.silo = Silo.objects.create(name="test_silo1",public=0, owner = self.user)
        self.read = Read.objects.create(read_name="test_read1", owner = self.user, type=self.read_type)
        self.client = Client()
        self.client.login(username='joe', password='tola123')
    def test_noRead(self):
        data = [{'a' : 'dog', 'b' : 'house'}, {'a' : 'cat', 'b' : 'house'}]
        saveDataToSilo(self.silo, data)
        try:
            lvs = LabelValueStore.objects.get(a='dog', b='house', read_id=-1, silo_id = self.silo.id)
        except LabelValueStore.DoesNotExist as e:
            self.deleteTestData()
            self.assert_(False)
        try:
            lvs = LabelValueStore.objects.get(a='cat', b='house', read_id=-1, silo_id = self.silo.id)
        except LabelValueStore.DoesNotExist as e:
            deleteTestData()
            self.assert_(False)
        self.deleteTestData()
    def test_uniqueColsUnique(self):
        unique_field = UniqueFields(name='a', silo=self.silo)
        unique_field.save()
        data = [{'a' : 'dog', 'b' : 'house'}, {'a' : 'cat', 'b' : 'house'}]
        saveDataToSilo(self.silo, data)
        #now test changing data
        data = [{'a' : 'dog', 'b' : 'out'}, {'a' : 'cat', 'b' : 'house'}]
        saveDataToSilo(self.silo, data, self.read)
        try:
            lvs = LabelValueStore.objects.get(a='dog', b='out', read_id=self.read.id, silo_id = self.silo.id)
        except LabelValueStore.DoesNotExist as e:
            self.deleteTestData()
            self.assert_(False)
        try:
            lvs = LabelValueStore.objects.get(a='cat', b='house', read_id=self.read.id, silo_id = self.silo.id)
        except LabelValueStore.DoesNotExist as e:
            self.deleteTestData()
            self.assert_(False)
        self.deleteTestData()
    def test_uniqueColsNonUnique(self):
        data = [{'a' : 'dog', 'b' : 'house'}, {'a' : 'cat', 'b' : 'house'}]
        saveDataToSilo(self.silo, data)
        unique_field = UniqueFields(name='b', silo=self.silo)
        unique_field.save()

        #now test changing data
        data = [{'a' : 'dog', 'b' : 'out'}, {'a' : 'cat', 'b' : 'house'}]
        saveDataToSilo(self.silo, data, self.read)
        try:
            lvs = LabelValueStore.objects.get(a='dog', b='out', read_id=self.read.id, silo_id = self.silo.id)
        except LabelValueStore.DoesNotExist as e:
            self.deleteTestData()
            self.assert_(False)
        try:
            lvs = LabelValueStore.objects.get(a='dog', b='house', read_id=-1, silo_id = self.silo.id)
        except LabelValueStore.DoesNotExist as e:
            self.deleteTestData()
            self.assert_(False)
        try:
            lvs = LabelValueStore.objects.get(a='cat', b='house', read_id=-1, silo_id = self.silo.id)
        except LabelValueStore.DoesNotExist as e:
            self.deleteTestData()
            self.assert_(False)
        self.deleteTestData()

    def test_noUniqueCols(self):
        pass
    def deleteTestData(self):
        LabelValueStore.objects.filter(a='dog', b='house').delete()
        LabelValueStore.objects.filter(a='dog', b='out').delete()
        LabelValueStore.objects.filter(a='cat', b='house').delete()


class test_setSiloColumnType(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="joe", email="joe@email.com", password="tola123")
        self.silo = Silo.objects.create(name="test_silo1",public=0, owner = self.user)
    def test_setToInt(self):
        addColsToSilo(self.silo, ['a','b','c'])
        lvs = LabelValueStore()
        lvs.silo_id = self.silo.pk
        lvs.a = '1'
        lvs.b = 2
        lvs.c = '3'
        lvs.save()
        try:
            lvs = LabelValueStore.objects.get(silo_id=self.silo.pk, a='1', b=2, c = '3')
        except LabelValueStore.DoesNotExist as e:
            lvs = LabelValueStore.objects.filter(silo_id=self.silo.pk).delete()
            self.assertTrue(False)
        try:
            lvs = LabelValueStore.objects.get(silo_id=self.silo.pk, a=1, b=2, c = '3')
            lvs = LabelValueStore.objects.filter(silo_id=self.silo.pk).delete()
            self.assertTrue(False)
        except LabelValueStore.DoesNotExist as e:
            pass
        setSiloColumnType(self.silo.pk, 'a', 'int')
        self.silo = Silo.objects.get(pk=self.silo.pk)
        try:
            lvs = LabelValueStore.objects.get(silo_id=self.silo.pk, a=1, b=2, c = '3')
        except LabelValueStore.DoesNotExist as e:
            lvs = LabelValueStore.objects.filter(silo_id=self.silo.pk).delete()
            self.assertTrue(False)
        try:
            lvs = LabelValueStore.objects.get(silo_id=self.silo.pk, a='1', b=2, c = '3')
            lvs = LabelValueStore.objects.filter(silo_id=self.silo.pk).delete()
            self.assertTrue(False)
        except LabelValueStore.DoesNotExist as e:
            pass
        lvs = LabelValueStore.objects.filter(silo_id=self.silo.pk).delete()
        self.assertTrue({'name' : 'a', 'type' : 'int'} in json.loads(self.silo.columns))
"""