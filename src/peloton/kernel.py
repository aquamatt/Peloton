# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details

import logging
import signal
import sys

from twisted.internet import reactor
from peloton.base import HandlerBase

ADAPTERS = ["peloton.adapters.pb.PelotonPBAdapter",
#            "peloton.adapters.soap.PelotonSoapAdapter",
#            "peloton.adapters.xmlrpc.PelotonXMLRPCAdapter",
#            "peloton.adapters.web.PelotonHTTPAdapter",
            ]

logger = logging.getLogger()

class PelotonKernel(HandlerBase):
    """ The kernel is the core that starts key services of the 
node, registers with the grid, pulls together all kernel modules
and provides the means via which components find each other. For example, 
it is the kernel that gathers together the event transceiver and the
coreIO interfaces.
"""
    def __init__(self, generatorInterface, options, args):
        """ Prepare the kernel. The generatorInterface is a callable via
which the kernel can request a worker to be started for a given service."""
        HandlerBase.__init__(self, options, args)
        self.generatorInterface = generatorInterface
    
    def start(self):
        """ Start the Twisted event loop. This method returns only when
the server is stopped. Returns an exit code."""
        # generate session keys

        # hook into cacheing back-end
        
        # hook into persistence back-ends
        
        # hook into message bus
        
        # hook in the PB adapter and any others listed
        self._startAdapters()
        
        # schedule grid-joining workflow to happen on reactor start
        
        # Write to the generatorInterface to pass host:port of our 
        # twisted RPC interface

        reactor.run()
        
        return 0

    def closedown(self):
        """Closedown in an orderly fashion"""
        # Closedown all worker nodes
        # tidy up kernel
        
        # stop the reactor
        reactor.stop()

    def _startAdapters(self):
        """Prepare all protocol adapters for use."""
        raise NotImplementedError("_startAdapters not yet written.")
    
