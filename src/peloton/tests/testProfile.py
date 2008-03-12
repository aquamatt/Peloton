# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
""" Test the PelotonProfile class """

from unittest import TestCase
from peloton.profile import PelotonProfile
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
        
    def test_comparison(self):
        """ Assure ourselves that profiles compare as we expect... """
        pass