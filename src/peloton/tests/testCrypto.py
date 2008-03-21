# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
""" Test the peloton.crypto module """

from unittest import TestCase
import peloton.crypto as crypto
import random

class Test_PelotonProfile(TestCase):
    def setUp(self):
        self.key = crypto.newKey(512)
    
    def tearDown(self):
        pass
    
    def test_makeCookie(self):
        # limited amount to test here, but check
        # the length is good and the characters all
        # come from the tokenspace
        # Try 100 times (a lame test really!)
        
        for i in xrange(100):
            l = random.randint(1, 2000)
            cookie = crypto.makeCookie(l)
            self.assertTrue(len(cookie), l)
            ct = [i for i in cookie if i not in crypto.tokenspace]
            self.assertEquals(ct, [])
    
    def test_encryptDecrypt(self):
        v = [1,2,'hello world', 21.34]
        ct = crypto.encrypt(v, self.key)
        pt = crypto.decrypt(ct, self.key)
        self.assertEquals(pt, v)

        v = {'a':1,2:56,'greeting':'hello world', 'weight':21.34}
        ct = crypto.encrypt(v, self.key)
        pt = crypto.decrypt(ct, self.key)
        self.assertEquals(pt, v)
        