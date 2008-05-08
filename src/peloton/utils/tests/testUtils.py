# $Id: testUtils.py 59 2008-03-12 10:33:50Z mp $
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
""" Test functions in peloton.utils """

from unittest import TestCase
from peloton.utils import chop
from peloton.utils import getClassFromString
from peloton.utils import deCompound

class Test_littleUtils(TestCase):
    def setUp(self):
        pass
    
    def tearDown(self):
        pass

    def test_chop(self):
        match = 'hello world'
        s = 'hello world\n'
        self.assertEquals(chop(s), match)
        s = 'hello world\r'
        self.assertEquals(chop(s), match)
        s = 'hello world\r\n'
        self.assertEquals(chop(s), match)
        s = 'hello world\n\r'
        self.assertEquals(chop(s), match)
        s = 'hello world\r*'
        self.assertEquals(chop(s,extras='*'), match)

    def test_getClassFromString(self):
        c = 'peloton.kernel.PelotonKernel'
        cls = getClassFromString(c)
        from peloton.kernel import PelotonKernel as MatchClass
        self.assertEquals(cls, MatchClass)
        self.assertRaises(Exception, getClassFromString, 'peloton.kernel.Bogus')

    def test_deCompound(self):
        master = ['a','b','c','d','e','f']
        testa = ['a','b','c,d,e','f']
        testb = ['a','b,c','d,e','f']
        testc = ['a','b','c','d','e','f']

        for i in [testa, testb, testc]:
            self.assertEquals(deCompound(i), master)
            