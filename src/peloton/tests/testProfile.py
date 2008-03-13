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
        sio = StringIO(CONFIG_DATA)
        self.config = MyConfigObj(sio)
    
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
        self.assertEquals(pp['b'], 'world')
        self.assertEquals(pp['c'], '10')
        
        self.assertRaises(Exception, pp.loadFromConfig, self.config['profile'])
        
    def test_servicePSCcomparison(self):
        """ Assure ourselves that profiles compare as we expect..
"""
        hostProfile = PelotonProfile(ram=2048, hostname='kylie', cpus=1)
        goodSvcProfiles = [dict(mincpus=1),
                           dict(),
                           dict(hostname='kylie'),
                           dict(hostname='s:kylie'),
                           dict(hostname='r:k.l.*$'),
                           dict(hostname='f:k?l*'),
                           dict(minram=2048),
                           dict(maxram=2048),
                           dict(minram=2048, maxram=2048),
                           dict(minram=1024, maxram=4096)]
                           
        badSvcProfiles = [dict(mincpus=2),
                           dict(hostname='billie'),
                           dict(hostname='s:billie'),
                           dict(hostname='r:bi.l.*$'),
                           dict(hostname='f:bi?l*'),
                           dict(minram=4096),
                           dict(maxram=1024),
                           dict(minram=1024, maxram=2000)]
        
        
        sc = ServicePSCComparator()
        self.assertRaises(NotImplementedError, sc.gt, goodSvcProfiles[0], hostProfile)
        for p in goodSvcProfiles:
            self.assertTrue(sc.eq(PelotonProfile(psclimits=p), hostProfile))
            
        for p in badSvcProfiles:
            self.assertFalse(sc.eq(PelotonProfile(psclimits=p), hostProfile))