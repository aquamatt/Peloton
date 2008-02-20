##############################################################################
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved.
#
# This software  is licensed under the terms of the BSD license, a copy of
# which should accompany this distribution.
#
##############################################################################

from unittest import TestCase
from peloton.utils.structs import ReadOnlyDict

class Test_ReadOnlyDict(TestCase):
    def test_readOnlyDict(self):
        d = ReadOnlyDict()
        d['x'] = 10
        self.assertEquals(d['x'], 10)
        self.assertRaises(Exception, d.__setitem__, 'x', 11)
        d.setRewriteable(['x'])
        d['x'] = 20
        self.assertEquals(d['x'], 20)
        d.setRewriteable('t')
        d['t'] = 10
        self.assertEquals(d['t'], 10)
        d['t'] = 11
        self.assertEquals(d['t'], 11)
        