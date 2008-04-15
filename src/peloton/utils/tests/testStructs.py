# $Id: testStructs.py 113 2008-04-05 22:05:42Z mp $
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details

from unittest import TestCase
from peloton.utils.structs import ReadOnlyDict
from peloton.utils.structs import FilteredOptionParser
from peloton.utils.structs import RoundRobinList
from types import ListType

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
        
class Test_FilteredOptionParser(TestCase):
    def setUp(self):
        self.fo = FilteredOptionParser()
        self.fo.add_option('--prefix', default='/etc/')
        self.fo.add_option('-c', dest='configdir', default='$PREFIX')
        self.fo.add_option('-o', dest='outputdir', default='/')
        
    def tearDown(self):
        pass
    
    def test_noOpts(self):
        o,a = self.fo.parse_args([])
        self.assertEquals(o.prefix, '/etc/')
        self.assertEquals(o.configdir, '/etc/')
        self.assertEquals(o.outputdir, '/')
        
    def test_overidePrefix(self):
        o,a = self.fo.parse_args(['--prefix=/tmp'])
        self.assertEquals(o.prefix, '/tmp')
        self.assertEquals(o.configdir, '/tmp')
        self.assertEquals(o.outputdir, '/')
        
    def test_manualUse(self):
        o,a = self.fo.parse_args(['--prefix=/tmp', '-o', '$PREFIX/output'])
        self.assertEquals(o.prefix, '/tmp')
        self.assertEquals(o.configdir, '/tmp')
        self.assertEquals(o.outputdir, '/tmp/output')
        
    def test_filterArgs(self):
        o, a = self.fo.parse_args(['--prefix=/tmp', '$PREFIX/test.xml'])
        self.assertEquals(a[0], '/tmp/test.xml')
        
    def test_argsOnly(self):
        o, a = self.fo.parse_args(['$PREFIX/test.xml', '$PREFIX'])
        self.assertEquals(a[0], '/etc//test.xml')
        self.assertEquals(a[1], '/etc/')
        
    def test_overideSubstitutions(self):
        self.fo.setSubstitutions(prefix='/var')
        o,a = self.fo.parse_args(['-o', '$PREFIX/output'])
        self.assertEquals(o.prefix, '/var')
        self.assertEquals(o.configdir, '/var')
        self.assertEquals(o.outputdir, '/var/output')
        
    def test_complexOverideSubstitutions(self):
        self.fo.setSubstitutions(prefix='/var/$OUTPUTDIR/test')
        o,a = self.fo.parse_args(['-o','/usr/local'])
        self.assertEquals(o.prefix, '/var//usr/local/test')
        self.assertEquals(o.configdir, '/var//usr/local/test')
        self.assertEquals(o.outputdir, '/usr/local')
        

class Test_RoundRobinList(TestCase):
    def setUp(self):
        self.thelist = RoundRobinList(['a','b','c','d'])
        
    def tearDown(self):
        pass
    
    def test_iter(self):
        self.assertEquals(self.thelist.rrnext(), 'a')
        self.assertEquals(self.thelist.rrnext(), 'b')
        self.assertEquals(self.thelist.rrnext(), 'c')
        self.assertEquals(self.thelist.rrnext(), 'd')
        self.assertEquals(self.thelist.rrnext(), 'a')
        self.assertEquals(self.thelist.rrnext(), 'b')
        self.assertEquals(self.thelist.rrnext(), 'c')
        self.thelist.append('e')
        self.assertEquals(self.thelist.rrnext(), 'd')
        self.assertEquals(self.thelist.rrnext(), 'e')
        self.assertEquals(self.thelist.rrnext(), 'a')
        self.thelist.pop()
        self.thelist.remove('d')
        self.assertEquals(self.thelist.rrnext(), 'b')
        self.assertEquals(self.thelist.rrnext(), 'c')
        self.assertEquals(self.thelist.rrnext(), 'a')

    def test_slicing(self):
        newList = self.thelist[:3]
        self.assertTrue(isinstance(newList, RoundRobinList))
        self.assertEquals(newList.rrnext(), 'a')
        self.assertEquals(newList.rrnext(), 'b')
        self.assertEquals(newList.rrnext(), 'c')
        self.assertEquals(newList.rrnext(), 'a')

        newList = self.thelist[1:3]
        self.assertTrue(isinstance(newList, RoundRobinList))
        self.assertEquals(newList.rrnext(), 'b')
        self.assertEquals(newList.rrnext(), 'c')
        self.assertEquals(newList.rrnext(), 'b')
                
        