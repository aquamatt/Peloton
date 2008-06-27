# $Id: testProfile.py 106 2008-04-04 10:47:50Z mp $
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
""" Test the PelotonSettings class """

from unittest import TestCase
from peloton.profile import ServicePSCComparator
from peloton.utils.config import PelotonSettings
from cStringIO import StringIO

class Test_PelotonSettings(TestCase):
    def test_servicePSCcomparison(self):
        """ Assure ourselves that profiles compare as we expect..
"""
        hostProfile = PelotonSettings(ram=2048, hostname='kylie', cpus=1)
        goodSvcProfiles = [PelotonSettings(mincpus=1),
                           PelotonSettings(),
                           PelotonSettings(hostname='kylie'),
                           PelotonSettings(hostname='s:kylie'),
                           PelotonSettings(hostname='r:k.l.*$'),
                           PelotonSettings(hostname='f:k?l*'),
                           PelotonSettings(minram=2048),
                           PelotonSettings(maxram=2048),
                           PelotonSettings(minram=2048, maxram=2048),
                           PelotonSettings(minram=1024, maxram=4096)]
                           
        badSvcProfiles = [PelotonSettings(mincpus=2),
                           PelotonSettings(hostname='billie'),
                           PelotonSettings(hostname='s:billie'),
                           PelotonSettings(hostname='r:bi.l.*$'),
                           PelotonSettings(hostname='f:bi?l*'),
                           PelotonSettings(minram=4096),
                           PelotonSettings(maxram=1024),
                           PelotonSettings(minram=1024, maxram=2000)]
        
        sc = ServicePSCComparator()
        self.assertRaises(NotImplementedError, sc.gt, goodSvcProfiles[0], hostProfile)
        for p in goodSvcProfiles:
            self.assertTrue(sc.eq(p, hostProfile))
            
        for p in badSvcProfiles:
            self.assertFalse(sc.eq(p, hostProfile))
    
    def test_booleanBehaviour(self):
        """ Check that empty config evaluates to False in a test and
to True when not empty. """
        pp = PelotonSettings()
        if pp:
            v = True
        else:
            v = False
        
        self.assertFalse(v)
        
        pp = PelotonSettings(x=10)
        if pp:
            v = True
        else:
            v = False
        self.assertTrue(v)
        
        
        
