# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
""" Test the peloton.utils.config code """

from unittest import TestCase
from peloton.utils.config import PelotonConfig
from peloton.utils.structs import FilteredOptionParser
from peloton.utils.structs import ReadOnlyDict
import os
import random
charset = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

GRID_CONFIG = ("megabank.pcfg", """
# grid config
[grid]
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
[domain]
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
[domain]
  name=Test Front office
  # absolute or relative to location of this config
  keyfile=/etc/peloton/testdomain.key

  administrators=testadmin@example.com
""")

DOMAIN_OVERRIDE_CONFIG_UAT = ("foo_uat_domain.pcfg", """
# domain configuration
# there may be many domains in a site
[domain]
  name=UAT Front office
  # absolute or relative to location of this config
  keyfile=/etc/peloton/testdomain.key

  administrators=testadmin@example.com
""")

DOMAIN_OVERRIDE_CONFIG_BAZ = ("baz_test_domain.pcfg", """
# domain configuration
# there may be many domains in a site
[domain]
  name=Baz Office
  # absolute or relative to location of this config
  keyfile=/etc/peloton/testdomain.key

  administrators=testadmin@example.com
""")


PSC_CONFIG = ("psc.pcfg", """
# Individual PSC configuration
[psc]
  bind=0.0.0.0:9100
""")

PSC_OVERRIDE_CONFIG=("psc_test.pcfg", """  
  # Overides for different modes
[psc]
  bind=0.0.0.0:9101 
""")


class Test_ReadOnlyDict(TestCase):
    def test_dict(self):
        r = ReadOnlyDict()
        r.setRewriteable(['rewriteTest'])
        r['x'] = 10
        r['y'] = 'hello world'
        r['rewriteTest'] = 'jonny'
        
        self.assertEquals(r['x'], 10)
        self.assertEquals(r['y'], 'hello world')
        self.assertEquals(r['rewriteTest'], 'jonny')
        
        try:
            r['x'] = 12
            self.fail("I was able to rebind r['x'] in a readonly dictionary")
        except:
            pass

        try:
            r['y'] = 'afsd'
            self.fail("I was able to rebind r['y'] in a readonly dictionary")
        except:
            pass
        
        try:
            r['rewriteTest'] = 'ball'
        except:
            self.fail("I was UNable to rebind the re-writeable key in a readonly dict")

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
        os.makedirs(self.dirNameA)
        os.makedirs(self.dirNameB)

        for flist, _dir in [(self.files_dira, self.dirNameA), (self.files_dirb, self.dirNameB)]:
            for f in flist:
                o = open(os.sep.join([_dir, f[0]]),'wt')
                o.writelines(f[1])
                o.close()
             
        self.parser = FilteredOptionParser()
        self.parser.add_option("-c", "--configdir",
                          dest="configdirs",
                          help="Path to directory containing configuration data, links to services etc. [default: %default]",
                          action="append",
                          default=['/etc/peloton'])
        
        self.parser.add_option("-g", "--grid",
                          help="""Short name for the grid to join [default: %default]""",
                          default="peligrid")
        
        self.parser.add_option("-d", "--domain",
                          help="""Short name for the domain to join [default: %default]""",
                          default="pelotonica")
        
        
    def tearDown(self):
        for flist, _dir in [(self.files_dira, self.dirNameA), (self.files_dirb, self.dirNameB)]:
            for f in flist:
                os.remove(os.sep.join([_dir, f[0]]))
            os.removedirs(_dir)


    def test_loadConfig(self):
        opts,args = self.parser.parse_args(["--configdir=%s"%self.dirNameA, 
                                '-c',self.dirNameB,
                                '-g', 'megabank',
                                '-d', 'foo'])
        pc = PelotonConfig(opts)
        
        self.assertEquals(pc.get('grid.gridmode', 'grid'), 'test')
        self.assertEquals(pc.get('domain.name', 'domain'), 'Test Front office')
        self.assertEquals(pc.get('psc.bind', 'psc'), '0.0.0.0:9101')

        opts,args = self.parser.parse_args(["--configdir=%s"%self.dirNameA, 
                                '-g', 'megabank',
                                '-d', 'foo'])
        pc = PelotonConfig(opts)
        self.assertEquals(pc.get('grid.gridmode', 'grid'), 'test')
        self.assertEquals(pc.get('domain.name', 'domain'), 'Front office')
        self.assertEquals(pc.get('psc.bind', 'psc'), '0.0.0.0:9100')
        
class Test_FilteredOptionParser(TestCase):
    def test_none(self):
        self.fail("Write tests for FilteredOptionParser")
#    def setUp(self):
#        self.parser = FilteredOptionParser()
#        self.parser.set_defaults(nodetach=False)
#        self.parser.add_option("-b", "--bind", dest='bindhost')
#        self.parser.add_option("-d", "--domain", default="Pelotonica")
#
#    def tearDown(self):
#        pass
#    
#    def test_overide(self):
#        config = loadConfig('/etc', 'dev', TEST_CONFIG, None, None, None)
#        self.assertEquals(config['domain']['domainName'], 'Pelotonica')
#        self.assertEquals(config['network']['bind'], '0.0.0.0:9100') 
#    
#    def test_overideMechanism(self):
#        """ Check that the mechanism that enables command line
#args to overide config vars really does work. """
#        overideMapping = {'bindhost':'network.bind',
#                          'domain':'domain.domainName'}
#        opts, args = self.parser.parse_args(['-d','NewDomain','--bind=192.168.2.3:9100'])
#        config = loadConfig('/etc','dev', TEST_CONFIG,None, opts, overideMapping)
#        
#        self.assertEquals(config['domain']['domainName'], 'NewDomain')
#        self.assertEquals(config['network']['bind'], '192.168.2.3:9100') 
#        
#    def test_overideMissingOpts(self):
#        """ Test overide where there is no matching option on the command line
#to pair up with an entry in the mapping. """
#        overideMapping = {'bindhost':'network.bind',
#                          'domain':'domain.domainName'}
#        opts, args = self.parser.parse_args(['-d','NewDomain'])
#        config = loadConfig('/etc','dev', TEST_CONFIG,None, opts, overideMapping)
#        
#        self.assertEquals(config['domain']['domainName'], 'NewDomain')
#        self.assertEquals(config['network']['bind'], '0.0.0.0:9100') 
