# $Id: testConfig.py 106 2008-04-04 10:47:50Z mp $
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
""" Test the peloton.utils.config code """

from unittest import TestCase
from peloton.utils.config import findTemplateTargetsFor
from peloton.utils.config import PelotonSettings
from peloton.utils.structs import FilteredOptionParser
import os

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
        
class Test_pelotonSettings(TestCase):
    def setUp(self):
        fdir = os.path.split(__file__)[0]+'/testConfigs'
        self.config = \
            PelotonSettings(initFile=os.path.abspath(fdir+'/example_conf.pcfg'))
    
    def test_values(self):
        self.assertEquals(self.config['a'], 10)
        self.assertEquals(self.config['c']['value'],'mango')
        
    def test_repr(self):
        newconfig = eval(repr(self.config))
        self.assertEquals(newconfig['a'], 10)
        self.assertEquals(newconfig['c']['value'],'mango')

    def test_attrToItem(self):
        self.assertEquals(self.config.a, 10)
        self.assertEquals(self.config.c.value,'mango')
        
    def test_assignment(self):
        self.config.c['index_value'] = 'index'
        self.config.c.attr_value = 'attr' # want this to go as index
        
        self.assertEquals(self.config.c.index_value, 'index')
        self.assertEquals(self.config.c.attr_value, 'attr')
        self.assertEquals(self.config.c['index_value'], 'index')
        self.assertEquals(self.config.c['attr_value'], 'attr')
        
        self.config['d'] = PelotonSettings()
        self.config['d'].name='hello'
        self.assertEquals(self.config.d.name, 'hello')
        self.assertEquals(self.config['d'].name, 'hello')
        self.assertEquals(self.config['d']['name'], 'hello')
        