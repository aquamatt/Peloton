# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
""" Test the peloton.utils.config code """

from unittest import TestCase
from peloton.utils.config import loadConfig
from peloton.utils.structs import FilteredOptionParser

TEST_CONFIG = """
[site]
    siteName=Peloton Site
    siteLicense=''

[domain]
    domainName=Pelotonica
    domainAdmin=admin@example.com

[network]
    bind=0.0.0.0:9100
    
[external]
    messagingAdapter=peloton.messaging.rabbitmq
    memcacheHosts=localhost
"""


class Test_ReadOnlyDict(TestCase):
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
