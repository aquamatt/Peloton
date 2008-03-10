# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
""" Test the peloton.utils.config code """

from unittest import TestCase
from peloton.utils.config import loadConfig
from peloton.utils.structs import FilteredOptionParser

GRID_CONFIG = """
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
"""

DOMAIN_CONFIG = """
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
"""

DOMAIN_OVERRIDE_CONFIG = """
# domain configuration
# there may be many domains in a site
[domain]
  name=Test Front office
  # absolute or relative to location of this config
  keyfile=/etc/peloton/testdomain.key

  administrators=testadmin@example.com
"""

PSC_CONFIG = """
# Individual PSC configuration
[psc]
  bind=0.0.0.0:9100
"""

PSC_OVERRIDE_CONFIG="""  
  # Overides for different modes
[test]
  bind=0.0.0.0:9101 
"""


class Test_ReadOnlyDict(TestCase):
    pass


class Test_PelotonConfig(TestCase):
    def setUp(self):
        """ """
        pass
        


class Test_FilteredOptionParser(TestCase):
    def setUp(self):
        self.parser = FilteredOptionParser()
        self.parser.set_defaults(nodetach=False)
        self.parser.add_option("-b", "--bind", dest='bindhost')
        self.parser.add_option("-d", "--domain", default="Pelotonica")

    def tearDown(self):
        pass
    
    def test_overide(self):
        config = loadConfig('/etc', 'dev', TEST_CONFIG, None, None, None)
        self.assertEquals(config['domain']['domainName'], 'Pelotonica')
        self.assertEquals(config['network']['bind'], '0.0.0.0:9100') 
    
    def test_overideMechanism(self):
        """ Check that the mechanism that enables command line
args to overide config vars really does work. """
        overideMapping = {'bindhost':'network.bind',
                          'domain':'domain.domainName'}
        opts, args = self.parser.parse_args(['-d','NewDomain','--bind=192.168.2.3:9100'])
        config = loadConfig('/etc','dev', TEST_CONFIG,None, opts, overideMapping)
        
        self.assertEquals(config['domain']['domainName'], 'NewDomain')
        self.assertEquals(config['network']['bind'], '192.168.2.3:9100') 
        
    def test_overideMissingOpts(self):
        """ Test overide where there is no matching option on the command line
to pair up with an entry in the mapping. """
        overideMapping = {'bindhost':'network.bind',
                          'domain':'domain.domainName'}
        opts, args = self.parser.parse_args(['-d','NewDomain'])
        config = loadConfig('/etc','dev', TEST_CONFIG,None, opts, overideMapping)
        
        self.assertEquals(config['domain']['domainName'], 'NewDomain')
        self.assertEquals(config['network']['bind'], '0.0.0.0:9100') 
