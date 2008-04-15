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
import random
charset = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

GRID_CONFIG = ("megabank.pcfg", """
# grid config
  name=Megabank Peloton site
  gridmode=test
  
  # absolute or relative path to location of
  # license file
  licenseFile=mp.license
   
  #options are any or registered
  domainRegistrationPolicy=any

  # absolute or relative to location of this config
  keyfile=grid.key

  # all domains in a site must use the same message bus
  messagingAdapter=peloton.messaging.rabbitmq
""")

DOMAIN_CONFIG = ("foo_domain.pcfg", """
# domain configuration
# there may be many domains in a site
  name=Front office
  # Allow 'any' service to be started or only
  #       'registered' services
  serviceStartupPolicy=any 

  # absolute or relative to location of this config
  keyfile=domain.key

  administrators=admin@example.com

  # cacheing is restricted to a domain and does not
  # span a whole site
  memcacheHosts=localhost, # trailing comma ensures a list returned
  
  psc_user=peloton
  psc_group=peloton
    
  worker_user=pelotonw
  worker_gropu=peloton
""")

DOMAIN_OVERRIDE_CONFIG = ("foo_test_domain.pcfg", """
# domain configuration
# there may be many domains in a site
  name=Test Front office
  # absolute or relative to location of this config
  keyfile=/etc/peloton/testdomain.key

  administrators=testadmin@example.com
""")

DOMAIN_OVERRIDE_CONFIG_UAT = ("foo_uat_domain.pcfg", """
# domain configuration
# there may be many domains in a site
  name=UAT Front office
  # absolute or relative to location of this config
  keyfile=/etc/peloton/testdomain.key

  administrators=testadmin@example.com
""")

DOMAIN_OVERRIDE_CONFIG_BAZ = ("baz_test_domain.pcfg", """
# domain configuration
# there may be many domains in a site
  name=Baz Office
  # absolute or relative to location of this config
  keyfile=/etc/peloton/testdomain.key

  administrators=testadmin@example.com
""")


PSC_CONFIG = ("psc.pcfg", """
# Individual PSC configuration
  bind=0.0.0.0:9100

[special]
  value=123  
  subst=${bind}
""")

PSC_OVERRIDE_CONFIG=("psc_test.pcfg", """  
  # Overides for different modes
  bind=0.0.0.0:9101 
""")


class Test_PelotonConfig(TestCase):
    def setUp(self):
        """ Create a temp dir and write test config files to it."""
        self.files_dira = [GRID_CONFIG, DOMAIN_CONFIG, PSC_CONFIG]
        self.files_dirb = [DOMAIN_OVERRIDE_CONFIG, DOMAIN_OVERRIDE_CONFIG_UAT, PSC_OVERRIDE_CONFIG, DOMAIN_OVERRIDE_CONFIG_BAZ]
        self.dirNameA = '/tmp/pelotontest_%s/' % \
            "".join([charset[random.randrange(0,len(charset))] 
                     for i in xrange(5)])
        self.dirNameB = '/tmp/pelotontest_%s/' % \
            "".join([charset[random.randrange(0,len(charset))] 
                     for i in xrange(5)])
        self.dirNameC = '/tmp/pelotontest_%s/' % \
            "".join([charset[random.randrange(0,len(charset))] 
                     for i in xrange(5)])
        os.makedirs(self.dirNameA)
        os.makedirs(self.dirNameB)
        os.makedirs(self.dirNameC) # will contain all files in one dir

        for flist, _dir in [(self.files_dira, self.dirNameA), (self.files_dirb, self.dirNameB)]:
            for f in flist:
                o = open(os.sep.join([_dir, f[0]]),'wt')
                o.writelines(f[1])
                o.close()
                o = open(os.sep.join([self.dirNameC, f[0]]), 'wt')
                o.writelines(f[1])
                o.close()
             
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
        for flist, _dir in [(self.files_dira, self.dirNameA), (self.files_dirb, self.dirNameB)]:
            for f in flist:
                os.remove(os.sep.join([_dir, f[0]]))
                os.remove(os.sep.join([self.dirNameC, f[0]]))
            os.removedirs(_dir)
        os.removedirs(self.dirNameC)

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

    def test_allInOneDir(self):
        opts,args = self.parser.parse_args(["--configdir=%s"%self.dirNameC, 
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
        templates = findTemplateTargetsFor(cwd, 'MyService', 'm1')
        self.assertEquals(len(templates), 3)
        targets = [i[0] for i in templates]
        self.assertTrue('xml' in targets)
        self.assertTrue('html' in targets)
        self.assertTrue('rss' in targets)

        templates = findTemplateTargetsFor(cwd, 'MyService', 'm2')
        targets = [i[0] for i in templates]
        self.assertEquals(len(templates), 2)
        self.assertTrue('xml' in targets)
        self.assertTrue('html' in targets)
        
