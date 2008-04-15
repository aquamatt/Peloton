# $Id: test_pseudomq.py 93 2008-03-25 22:08:27Z mp $
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
from unittest import TestCase
from peloton.plugins.pseudomq import PseudoExchange

class Test_PseudoMQ(TestCase):
    def setUp(self):
        pass
    
    def tearDown(self):
        pass
    
    def test_patternMatchSimple(self):
        ex = PseudoExchange('test')
        self.assertTrue(ex.matchKey("a.b.c.d", "a.b.c.d"))
        self.assertFalse(ex.matchKey("a.b.c.d", "a.b.c"))
        self.assertFalse(ex.matchKey("a.b.c", "a.b.c.d"))

    def test_patternMatchHash(self):
        """ Test matching with # wildcard (matches zero or more
tokens). """
        ex = PseudoExchange('test')
        self.assertTrue(ex.matchKey("a.b.#", "a.b"))
        self.assertTrue(ex.matchKey("a.b.#", "a.b.c"))
        self.assertTrue(ex.matchKey("a.b.#", "a.b.c.d"))
        self.assertTrue(ex.matchKey("#", "a.b.c.d"))
        self.assertTrue(ex.matchKey("#.d", "a.b.c.d"))
        self.assertFalse(ex.matchKey("#.c", "a.b.c.d"))
        self.assertFalse(ex.matchKey("a.b.#", "a.c"))
        self.assertFalse(ex.matchKey("a.b.#", "a"))

        self.assertTrue(ex.matchKey("a.b.#.c.d", "a.b.x.x.x.c.d"))
        self.assertTrue(ex.matchKey("a.b.#.c.d", "a.b.x.c.d"))
        self.assertTrue(ex.matchKey("a.b.#.c.d", "a.b.c.d"))
        self.assertTrue(ex.matchKey("a.b.#.c.d", "a.b.x.x.c.x.x.c.d"))
        self.assertFalse(ex.matchKey("a.b.#.c.d", "a.b.x.x.c.x.x.c.e"))

    def test_patternMatchStar(self):
        """ Test matching with * wildcard (matches a single
token). """
        ex = PseudoExchange('test')
        self.assertTrue(ex.matchKey("a.*.b", "a.x.b"))
        self.assertTrue(ex.matchKey("a.*", "a.b"))
        self.assertTrue(ex.matchKey("*.b", "a.b"))
        self.assertFalse(ex.matchKey("a.*.b", "a.b"))        
        self.assertFalse(ex.matchKey("a.b.*", "a.b"))
        self.assertFalse(ex.matchKey("a.b.*", "a.b.x.d"))
        
    def test_patternMatchMixed(self):
        """ Test mixed # and * in a pattern."""
        ex = PseudoExchange('test')
        self.assertTrue(ex.matchKey("a.b.#.c.*", "a.b.x.x.x.c.d"))
        self.assertTrue(ex.matchKey("a.b.#.c.*", "a.b.x.x.x.c.e"))
        self.assertTrue(ex.matchKey("a.b.#.c.*.e", "a.b.x.x.x.c.d.e"))

        self.assertFalse(ex.matchKey("a.b.#.c.*", "a.b.x.x.x.c"))
        self.assertFalse(ex.matchKey("a.b.#.c.*.e", "a.b.x.x.x.c.e"))
        
        # the example from spec - should work for this at the very least!
        self.assertTrue(ex.matchKey("*.stock.#", "usd.stock"))
        self.assertTrue(ex.matchKey("*.stock.#", "eur.stock.db"))
        self.assertFalse(ex.matchKey("*.stock.#", "stock.nasdaq"))
