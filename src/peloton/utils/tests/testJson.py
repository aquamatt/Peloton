# $Id: testCrypto.py 91 2008-03-24 00:57:50Z mp $
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
        writer = json.JSONWriter()
        
        self.assertEquals(writer.serialize(10), u"10")
        self.assertEquals(writer.serialize("hello"), u'"hello"')
        self.assertEquals(writer.serialize([10,20,30]), u"[10, 20, 30]")
        self.assertEquals(writer.serialize((10,20,30)), u"[10, 20, 30]")
        self.assertEquals(writer.serialize({'a':10,'b':'text'}), u'{"a": 10, "b": "text"}')
        self.assertEquals(writer.serialize({'a':[10, 'text'], 'b':{123:'123'}}), u'{"a": [10, "text"], "b": {123: "123"}}')
        self.assertEquals(writer.serialize({'a':[10, 'text'], 'b':{123:'123','floatval':123.45}}), u'{"a": [10, "text"], "b": {123: "123", "floatval": 123.450000}}')
        self.assertEquals(writer.serialize("hello\nworld"), u'"hello\\nworld"')
        self.assertEquals(writer.serialize("hello\n\rworld"), u'"hello\\n\\rworld"')
        self.assertEquals(writer.serialize("\\hello\n\rworld"), u'"\\\\hello\\n\\rworld"')
        self.assertEquals(writer.serialize(None), u'null')
        self.assertRaises(json.UnSerializableError, writer.serialize, self)