# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
""" Test functions in peloton.utils """

from unittest import TestCase
from peloton.utils import chop
from peloton.utils import getClassFromString

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
