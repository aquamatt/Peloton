# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
""" Test the PelotonProfile class """

from unittest import TestCase
from peloton.profile import PelotonProfile
from peloton.profile import ServicePSCComparator
from peloton.utils.config import MyConfigObj
from cStringIO import StringIO

class Test_PelotonProfile(TestCase):
    def setUp(self):
        CONFIG_DATA="""test=10
[profile]
  a=hello
  b=world
  c=10
"""

        CONFIG_DATA_B="""  a=hello
  b=tentacles
  c=320
"""
        sio = StringIO(CONFIG_DATA)
        self.config = MyConfigObj(sio)
        self.configFile = StringIO(CONFIG_DATA_B)
    
    def tearDown(self):
        pass
    
    def test_profileInit(self):
        initDict = {'a':'a', 'b':'2'}
        pp = PelotonProfile(initDict)
        self.assertEquals(pp['b'], initDict['b'])
        
        pp = PelotonProfile(test=1, world='gaia')
        self.assertEquals(pp['test'], 1)
        self.assertEquals(pp['world'], 'gaia')
        
    def test_loadFromConfig(self):
        pp = PelotonProfile()
        pp.loadFromConfig(self.config)
        self.assertEquals(pp['a'], 'hello')
        self.assertEquals(pp['b'], 'world')
        self.assertEquals(pp['c'], '10')
        
        self.assertRaises(Exception, pp.loadFromConfig, self.config['profile'])

    def test_merge(self):
        pp = PelotonProfile()
        pp.loadFromConfig(self.config)
        self.assertEquals(pp['b'], 'world')
        pp.update({'b':'bbc'})
        self.assertEquals(pp['b'], 'bbc')
        
    def test_loadFromConfig_then_loadFromFile(self):
        """ Test that overriding of properties works as
desired."""
        pp = PelotonProfile()
        pp.loadFromConfig(self.config)
        self.assertEquals(pp['a'], 'hello')
        self.assertEquals(pp['b'], 'world')
        self.assertEquals(pp['c'], '10')
        pp.loadFromFile(self.configFile)
        self.assertEquals(pp['a'], 'hello')
        pp.update({'b':'tentacles'})
        self.assertEquals(pp['c'], '320')

    def test_booleanEvaluation(self):
        """ Confirm that use in an if clause, e.g.::
    if not profile:
      ...
will work as expected, i.e. return False if the profile is 
empty.
"""
        pp = PelotonProfile()
        self.assertFalse(pp)
        pp.loadFromConfig(self.config)
        self.assertTrue(pp)
        
    def test_servicePSCcomparison(self):
        """ Assure ourselves that profiles compare as we expect..
"""
        hostProfile = PelotonProfile(ram=2048, hostname='kylie', cpus=1)
        goodSvcProfiles = [PelotonProfile(mincpus=1),
                           PelotonProfile(),
                           PelotonProfile(hostname='kylie'),
                           PelotonProfile(hostname='s:kylie'),
                           PelotonProfile(hostname='r:k.l.*$'),
                           PelotonProfile(hostname='f:k?l*'),
                           PelotonProfile(minram=2048),
                           PelotonProfile(maxram=2048),
                           PelotonProfile(minram=2048, maxram=2048),
                           PelotonProfile(minram=1024, maxram=4096)]
                           
        badSvcProfiles = [PelotonProfile(mincpus=2),
                           PelotonProfile(hostname='billie'),
                           PelotonProfile(hostname='s:billie'),
                           PelotonProfile(hostname='r:bi.l.*$'),
                           PelotonProfile(hostname='f:bi?l*'),
                           PelotonProfile(minram=4096),
                           PelotonProfile(maxram=1024),
                           PelotonProfile(minram=1024, maxram=2000)]
        
        sc = ServicePSCComparator()
        self.assertRaises(NotImplementedError, sc.gt, goodSvcProfiles[0], hostProfile)
        for p in goodSvcProfiles:
            self.assertTrue(sc.eq(p, hostProfile))
            
        for p in badSvcProfiles:
            self.assertFalse(sc.eq(p, hostProfile))
    
