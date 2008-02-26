# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details

from svcdeco import testDecorator
from peloton.utils.structs import ReadOnlyDict

class PelotonService(object):
    """ Base class for all services. Public methods all have names prefixed
'public_', much as twisted spread remote callable methods are prefixed 'remote_'.
"""
    def __init__(self, rootPath):
        """ Root path passed in on construction because from this module
cannot find where the sub-class lives. Configurations are found relative to this
root path. """
        self.rootPath = rootPath
        self.loadConfig()
        
    def loadConfig(self):
        """ Load the configuration and put into self.conf """
        self.conf = ReadOnlyDict()
        # locate config relative to root path of caller... 
    
    def setup(self):
        """ Executed after configuration is loaded, prior to starting work.
Can be used to setup database pools etc. Overide in actual services. """
        pass
    
    def cleanup(self):
        """ Executed prior to shuting down this service or the node.
Can be used to cleanup database pools etc. Overide in actual services. """
        pass
    