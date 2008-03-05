# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
"""Default suite of Peloton protocol adapters """

class AbstractPelotonAdapter(object):
    """ Base class for all Peloton protocol adapters. """
    
    def __init__(self, name):
        self.enabled = False
        self.adapterName = name
    
    def start(self, configuration, options):
        """ Implement to initialise the adapter based on the 
parsed configuration file (configuration) and command line 
options (options). This method must also hook this adapter
into the reactor, probably calling reactor.listenTCP or adding
itself to another protocol as a resource (this is the case for most
HTTP based adapters)."""
        raise NotImplementedError()
    
    def stop(self):
        """ Close down this adapter; stop listening to requests
and release resources. """
        raise NotImplementedError
