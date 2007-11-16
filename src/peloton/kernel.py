# Copyright 2007 Matthew Pontefract
# See LICENSE for details

from twisted.internet import reactor
import peloton.adapters

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
        # start memcache daemon
        
        # hook into persistence back-ends
        
        # hook into message bus
        
        # hook in the PB adapter and any others listed

        # schedule grid-joining workflow to happen on reactor start
        
        # hook up signal handlers        
        reactor.run()
