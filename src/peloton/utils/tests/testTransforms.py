# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
from unittest import TestCase
from peloton.utils.transforms import valueToDict
from peloton.utils.transforms import stripKeys
from peloton.utils.transforms import upperKeys
from sets import Set

class Test_Transforms(TestCase):
    def setUp(self):
        pass
    
    def tearDown(self):
        pass
    
    def test_valueToDict(self):
        v2d = valueToDict()
        self.assertEquals(v2d('a'), {'d':'a', '_sys':{}})
        self.assertEquals(v2d(1), {'d':1, '_sys':{}})
        self.assertEquals(v2d([1,2,3]), {'d':[1,2,3], '_sys':{}})
        
    def test_stripKeys(self):
        data = {'a':1, 'b':2, 'c':3, 'd':4}
        stripKeys('b', 'c')(data, {})
        self.assertEquals(len(data), 2)
        self.assertTrue(data.has_key('a'))
        self.assertTrue(data.has_key('d'))
        self.assertFalse(data.has_key('b'))
        self.assertFalse(data.has_key('c'))
        
    def test_upperKeys(self):
        data = {'a':1, 'b':2, 'c':3, 'd':4}
        upperKeys()(data, {})
        dataSet = Set(data.keys())
        testSet = Set(['A','B','C','D'])
        self.assertEquals(dataSet-testSet, Set([]))
        self.assertEquals(data['A'], 1)
        self.assertEquals(data['D'], 4)
        self.assertRaises(KeyError, data.__getitem__, 'a')
        
            