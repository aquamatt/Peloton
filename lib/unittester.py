"""unittest module which will find all instances of "tests" directories 
from a given directory (default that in which it is run), locates all
candidate TestCases (classes inheriting from unittest.TestCase,
and executing all TestCase methods starting with check_
"""

_version='2.0'

DEBUG=False

# Version 2 includes DocTest capability


#-------------------------------------------------------------------------------
# The testing code should make use of PyUnit (/lib/python/unittest.py). Instructions for using PyUnit are available at http://pyunit.sourceforge.net.
# Tests must be placed in a "tests" subdirectory of the package or directory in which the core code you're testing lives.
# Test modules should be named something which represents the functionality they test, and should begin with the prefix "test." E.g., a test module for BTree should be named testBTree.py.
# An individual test module should take no longer than 60 seconds to complete.
#-------------------------------------------------------------------------------
import re
import unittest
import doctest
import sys
import os, os.path

XTESTS=re.compile('^x+test*')

class Tester(object):
    def __init__(self,top_dir,ignoreList=[]):
        self.suites=[]
        self.loader=unittest.TestLoader()
        #self.loader.testMethodPrefix='check'
        self.top_dir=top_dir
        self.ignoreList = ignoreList
        self.run()
        
    
    def run(self):
        os.path.walk(self.top_dir, self.buildTests,None)
        testSuite=unittest.TestSuite(self.suites)
        t=unittest.TextTestRunner()
        t.run(testSuite)
       

    def buildTests(self,args,dir,names):
        "builds the test cases in this directory"
        # only look in directories called "tests"
  
        if os.path.split(dir)[1]<>'tests': return
        if [i for i in self.ignoreList if dir.find(i)>-1]:
            return
        
        if dir not in sys.path:
            sys.path.insert(0,dir)
        if DEBUG:
            print dir
        # look at all the .py files for instances of uninttest.TestCase
        for name in names:       
            if name.startswith('test') and os.path.splitext(name)[1]=='.py':                
                # import this module
                if DEBUG:
                    print name
                mod=__import__(name.split('.')[0])
                self.suites.append(self.loader.loadTestsFromModule(mod))
    
"""
suite = unittest.TestSuite() for mod in my_module_with_doctests, and_another: 
suite.addTest(doctest.DocTestSuite(mod))
"""                    


def runTests(top_dir, ignoreList=[]):
    test=Tester(top_dir, ignoreList)

if __name__=='__main__':

    # read in the command line
    options = None
    args = None
    top_dir = None
#    if os.name == 'java':
#        import getopt
#        options, args = getopt.getopt(sys.argv[1:], 'd',['directory='])
#    #    print args
#    #    print options
#        for o, a in options:
#    #        print o, a
#            if o in ('-d','--directory'):
#                top_dir =  os.path.abspath(a)
#        if not top_dir:
#            top_dir = os.path.abspath('.')
#
#    else:
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-d", "--directory", dest="directory", default='.',
                      help="use this directory as the top of the tree (default=current directory)")
    (options, args) = parser.parse_args()
    top_dir=os.path.abspath(options.directory)
    
    #tester=Tester(top_dir)
    runTests(top_dir)



#if __name__=='__main__':
#    # read in the command line
#    from optparse import OptionParser
#    parser = OptionParser()
#    parser.add_option("-d", "--directory", dest="directory", default='.',
#                      help="use this directory as the top of the tree (default=current directory)")
#    (options, args) = parser.parse_args()
#    
#    top_dir=os.path.abspath(options.directory)
#    
#    tester=Tester(top_dir)
#   
    


