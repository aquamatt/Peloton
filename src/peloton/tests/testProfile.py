# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
""" Test the PelotonProfile class """

from unittest import TestCase
from peloton.profile import PelotonProfile
from peloton.profile import ServicePSCComparator
from peloton.utils.config import PelotonConfigObj
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

        CONFIG_DATA_C="""mandy=more
[extra]
  zippy=10
"""
        
        sio = StringIO(CONFIG_DATA)
        self.config = PelotonConfigObj(sio)
        self.configFile = StringIO(CONFIG_DATA_B)
    
        sio = StringIO(CONFIG_DATA_C)
        self.configb = PelotonConfigObj(sio)
    
    def tearDown(self):
        pass
    
    def test_profileInit(self):
        initDict = {'a':'a', 'b':'2'}
        pp = PelotonProfile(initDict)
        self.assertEquals(pp['b'], initDict['b'])
        
        pp = PelotonProfile(dict(test=1, world='gaia'))
        self.assertEquals(pp['test'], 1)
        self.assertEquals(pp['world'], 'gaia')
        
    def test_loadFromConfig(self):
        pp = PelotonProfile()
        pp.loadFromConfig(self.config)
        self.assertTrue(pp.has_key('a'))
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
        hostProfile = PelotonProfile(dict(ram=2048, hostname='kylie', cpus=1))
        goodSvcProfiles = [PelotonProfile(dict(mincpus=1)),
                           PelotonProfile(),
                           PelotonProfile(dict(hostname='kylie')),
                           PelotonProfile(dict(hostname='s:kylie')),
                           PelotonProfile(dict(hostname='r:k.l.*$')),
                           PelotonProfile(dict(hostname='f:k?l*')),
                           PelotonProfile(dict(minram=2048)),
                           PelotonProfile(dict(maxram=2048)),
                           PelotonProfile(dict(minram=2048, maxram=2048)),
                           PelotonProfile(dict(minram=1024, maxram=4096))]
                           
        badSvcProfiles = [PelotonProfile(dict(mincpus=2)),
                           PelotonProfile(dict(hostname='billie')),
                           PelotonProfile(dict(hostname='s:billie')),
                           PelotonProfile(dict(hostname='r:bi.l.*$')),
                           PelotonProfile(dict(hostname='f:bi?l*')),
                           PelotonProfile(dict(minram=4096)),
                           PelotonProfile(dict(maxram=1024)),
                           PelotonProfile(dict(minram=1024, maxram=2000))]
        
        sc = ServicePSCComparator()
        self.assertRaises(NotImplementedError, sc.gt, goodSvcProfiles[0], hostProfile)
        for p in goodSvcProfiles:
            self.assertTrue(sc.eq(p, hostProfile))
            
        for p in badSvcProfiles:
            self.assertFalse(sc.eq(p, hostProfile))
    
    def test_getAndSetPath(self):
        self.config.setpath('profile.test.newsection', self.configb)
        self.assertEquals(self.config['profile']['test']['newsection']['mandy'], 'more')
        self.assertEquals(self.config['profile']['test']['newsection']['extra']['zippy'], '10')        
        self.assertEquals(self.config.getpath('profile.test.newsection.mandy'), 'more')
        self.assertEquals(self.config.getpath('profile.test.newsection.extra.zippy'), '10')        

        self.config.setpath('news', self.configb)
        self.assertEquals(self.config.getpath('news.mandy'), 'more')
        self.config.setpath('myname', 'jonny')
        self.assertEquals(self.config['myname'], 'jonny')
        
    def test_setMultiPath(self):
        """ Setpath creates entries on the way if any do not exist (bit
like mkdir -p). Test this. """
        self.config.setpath('myname.first.initial','X')
        self.config.setpath('myname.first.name','Xavier')
        self.assertEquals(self.config.getpath('myname.first.initial'), 'X')
        self.assertEquals(self.config.getpath('myname.first.name'), 'Xavier')
        self.assertRaises(KeyError,
                          self.config.setpath,'myname.first.education.primary','blah', 
                          False)
        self.config.setpath('myname.first.education.primary','blah')
        self.assertEquals(self.config.getpath('myname.first.education.primary'), 'blah')
    
    def test_booleanBehaviour(self):
        """ Check that empty config evaluates to False in a test and
to True when not empty. """
        pp = PelotonConfigObj()
        if pp:
            v = True
        else:
            v = False
        
        self.assertFalse(v)
        
        if self.config:
            v = True
        else:
            v = False
        self.assertTrue(v)
        
        
        
