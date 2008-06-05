# $Id: testConfig.py 106 2008-04-04 10:47:50Z mp $
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
""" Test the peloton.utils.config code """

from unittest import TestCase
from peloton.utils.config import PelotonConfig
from peloton.utils.config import findTemplateTargetsFor
from peloton.utils.structs import FilteredOptionParser
import os

class Test_PelotonConfig(TestCase):
    def setUp(self):
        """ Create a temp dir and write test config files to it."""
        import testConfig
        root = os.path.split(testConfig.__file__)[0]+"/testConfigs"
        self.dirNameA = "%s/root_a" % root
        self.dirNameB = "%s/root_b" % root

        self.parser = FilteredOptionParser()
        self.parser.add_option("-c", "--configdir",
                          dest="configdirs",
                          action="append",
                          default=['/etc/peloton'])
        
        self.parser.add_option("-g", "--grid",
                          default="peligrid")
        
        self.parser.add_option("-d", "--domain",
                          default="pelotonica")
        
        self.parser.add_option("-b", "--bind", 
                          dest='bindhost')
    
        
    def tearDown(self):
        pass
    
    def test_loadConfig(self):
        opts,args = self.parser.parse_args(["--configdir=%s"%self.dirNameA, 
                                '-c',self.dirNameB,
                                '-g', 'megabank',
                                '-d', 'foo'])
        pc = PelotonConfig(opts)
        
        self.assertEquals(pc['grid.gridmode'], 'test')
        self.assertEquals(pc['domain.name'], 'Test Front office')
        self.assertEquals(pc['psc.bind'], '0.0.0.0:9101')
        self.assertEquals(pc['psc.special.value'], '123')

        opts,args = self.parser.parse_args(["--configdir=%s"%self.dirNameA, 
                                '-g', 'megabank',
                                '-d', 'foo'])
        pc = PelotonConfig(opts)
        self.assertEquals(pc['grid.gridmode'], 'test')
        self.assertEquals(pc['domain.name'], 'Front office')
        self.assertEquals(pc['psc.bind'], '0.0.0.0:9100')
        
    def test_substitution(self):
        opts,args = self.parser.parse_args(["--configdir=%s"%self.dirNameA, 
                                '-c',self.dirNameB,
                                '-g', 'megabank',
                                '-d', 'foo'])
        pc = PelotonConfig(opts)
        
        self.assertEquals(pc['psc.special.subst'], pc['psc.bind'])

    def test_haskey(self):
        opts,args = self.parser.parse_args(["--configdir=%s"%self.dirNameA, 
                                '-c',self.dirNameB,
                                '-g', 'megabank',
                                '-d', 'foo'])
        pc = PelotonConfig(opts)
        self.assertTrue(pc.has_key('psc.special.subst'))
        self.assertFalse(pc.has_key('psc.special.foobar'))

    def test_overideFromCommandLine(self):
        opts,args = self.parser.parse_args(["--configdir=%s"%self.dirNameA, 
                                '-c',self.dirNameB,
                                '-g', 'megabank',
                                '-d', 'foo',
                                '--bind=192.168.2.1:9090'])
        pc = PelotonConfig(opts)
        self.assertEquals(pc['psc.bind'], '192.168.2.1:9090')

    def test_updateItems(self):
        opts,args = self.parser.parse_args(["--configdir=%s"%self.dirNameA, 
                                '-c',self.dirNameB,
                                '-g', 'megabank',
                                '-d', 'foo',
                                '--bind=192.168.2.1:9090'])
        pc = PelotonConfig(opts)
        self.assertEquals(pc['psc.bind'], '192.168.2.1:9090')
        pc['psc.bind'] = '111.222.333.444:111'
        self.assertEquals(pc['psc.bind'], '111.222.333.444:111')
        
    def test_deleteitems(self):
        opts,args = self.parser.parse_args(["--configdir=%s"%self.dirNameA, 
                                '-c',self.dirNameB,
                                '-g', 'megabank',
                                '-d', 'foo',
                                '--bind=192.168.2.1:9090'])
        pc = PelotonConfig(opts)
        self.assertEquals(pc['psc.bind'], '192.168.2.1:9090')
        del pc['psc.bind']
        self.assertRaises(KeyError, pc.__getitem__,'psc.bind')
        self.assertEquals(pc['psc.special.value'], '123')
        del pc['psc']
        self.assertRaises(KeyError, pc.__getitem__,'psc.special.value')
        self.assertEquals(pc['psc'], {})        


class Test_templateTools(TestCase):
    def setUp(self):
        def touch(root, file):
            o = open("%s/%s" % (root, file), 'wt')
            o.write("hello")
            o.close()
        cwd = os.getcwd()
        root = "%s/resource/templates/MyService" % cwd
        os.makedirs(root)
        for i in ['m1.xml.genshi','m1.html.genshi','m1.rss.genshi']:
            touch(root, i)
        for i in ['m2.xml.genshi','m2.html.genshi']:
            touch(root, i)

    def tearDown(self):
        cwd = os.getcwd()
        root = "%s/resource/templates/MyService" % cwd
        for i in os.listdir(root):
            os.unlink("%s/%s" % (root, i) )
        os.removedirs(root)        

    def test_findTemplateTargetsFor(self):
        cwd = os.getcwd()
        templates = findTemplateTargetsFor(cwd+'/resource','MyService', 'm1')
        self.assertEquals(len(templates), 3)
        targets = [i[0] for i in templates]
        self.assertTrue('xml' in targets)
        self.assertTrue('html' in targets)
        self.assertTrue('rss' in targets)

        templates = findTemplateTargetsFor(cwd+'/resource', 'MyService', 'm2')
        targets = [i[0] for i in templates]
        self.assertEquals(len(templates), 2)
        self.assertTrue('xml' in targets)
        self.assertTrue('html' in targets)
        
