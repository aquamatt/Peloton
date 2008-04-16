# $Id: testJson.py 122 2008-04-11 08:22:28Z mp $
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
from unittest import TestCase
from peloton.utils import json

class Test_JSON(TestCase):
    def setUp(self):
        pass
    
    def tearDown(self):
        pass
    
    def test_serialize(self):
        writer = json.JSONSerializer()
        
        self.assertEquals(writer.write(10), u"10")
        self.assertEquals(writer.write("hello"), u'"hello"')
        self.assertEquals(writer.write([10,20,30]), u"[10, 20, 30]")
        self.assertEquals(writer.write((10,20,30)), u"[10, 20, 30]")
        self.assertEquals(writer.write({'a':10,'b':'text'}), u'{"a": 10, "b": "text"}')
        self.assertEquals(writer.write({'a':[10, 'text'], 'b':{123:'123'}}), u'{"a": [10, "text"], "b": {123: "123"}}')
        self.assertEquals(writer.write({'a':[10, 'text'], 'b':{123:'123','floatval':123.45}}), u'{"a": [10, "text"], "b": {123: "123", "floatval": 123.450000}}')
        self.assertEquals(writer.write("hello\nworld"), u'"hello\\nworld"')
        self.assertEquals(writer.write("hello\n\rworld"), u'"hello\\n\\rworld"')
        self.assertEquals(writer.write("\\hello\n\rworld"), u'"\\\\hello\\n\\rworld"')
        self.assertEquals(writer.write([True, False, None, 10]), u'[true, false, null, 10]')
        self.assertEquals(writer.write(None), u'null')
        self.assertRaises(json.UnSerializableError, writer.write, self)
        
    def test_read(self):
        j = json.JSONSerializer()
        testObjects = [10,
                       "hello",
                       [10,20,30],
                       "hello\nworld",
                       {'a':[10, 'text'], 'b':{123:'123','floatval':123.45}},
                       True,
                       False,
                       None,
                       [True, False, 10],
                       ]
        
        for to in testObjects:
            v = j.write(to)
            _v = j.read(v)
            self.assertEquals(to, _v)