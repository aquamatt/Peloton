# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details


import peloton.adapters
import signal
import sys

from twisted.internet import reactor

ADAPTERS = [peloton.adapters.pb.PelotonPBAdapter,
#            peloton.adapters.soap.PelotonSoapAdapter,
#            peloton.adapters.xmlrpc.PelotonXMLRPCAdapter,
#            peloton.adapters.web.PelotonHTTPAdapter,
            ]

class PelotonKernel(object):
    """ The kernel is the core that starts key services of the 
node, registers with the grid, pulls together all kernel modules
and provides the means via which components find each other. For example, 
it is the kernel that gathers together the event transceiver and the
coreIO interfaces.
"""
    def __init__(self, profile):
        """ Prepare the kernel with the provided profile."""
        pass
    
    def start(self):
        """ Start the Twisted event loop. This method returns only when
the server is stopped. """
        # hook into cacheing back-end
        
        # hook into persistence back-ends
        
        # hook into message bus
        
        # hook in the PB adapter and any others listed
        self._startAdapters()
        
        # schedule grid-joining workflow to happen on reactor start
        
        # hook up signal handlers    

        # hide sys.exit
        self._trapExit()

        reactor.run()

    def closedown(self):
        """Closedown in an orderly fashion"""
        reactor.stop()

    def _startAdapters(self):
        """Prepare all protocol adapters for use."""
        raise NotImplementedError("_addAdapters not yet written.")
    
    def _signalClosedown(self, num, frame):
        """ Handle SIGINT/TERM """
        self.closedown()
    
    def _signalReload(self, num, frame):
        """ Reaction to a SIGHUP: need to re-start so as to re-load configuration
files etc."""
        raise NotImplementedError("SIGHUP handler not yet written.")
    
    def _setSignalHandlers(self):
        """Set signal traps for INT and TERM to the _signalClosedown method
that tidies up behind itself."""
        signal.signal(signal.SIGINT, self._signalClosedown)
        signal.signal(signal.SIGTERM, self._signalClosedown)
        signal.signal(signal.SIGHUP, self._signalReload)    

    def _trapExit(self):
        """ Move sys.exit to sys.realexit and put a dummy
into sys.exit. This prevents service writers from accidentaly
closing a node down."""
        def dummyExit():
            raise Exception("sys.exit disabled to prevent accidental node shutdown.")
        
        sys.realexit = sys.exit
        sys.exit = dummyExit