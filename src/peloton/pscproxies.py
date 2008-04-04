# $Id: mapping.py 104 2008-04-02 17:22:55Z mp $
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details

from twisted.internet.defer import Deferred
from twisted.spread import pb
from peloton.exceptions import PelotonError

class PSCProxy(object):        
    """ Base class for PSC proxies through which the routing
table can exchange messages with PSCs. A proxy is required because
the PSC may be the local process, a PSC in the domain or a PSC in
another domain on the grid.
"""
    def __init__(self, kernel, profile):
        self.profile = profile
        self.kernel = kernel
        
    def call(self, service, method, *args, **kwargs):
        """ Request the serice method be called on this 
PSC. """
        raise NotImplementedError
        
class TwistedPSCProxy(PSCProxy):        
    """ Proxy for a PSC that is running on the same domain as this 
node and accepts Twisted PB RPC. This is the prefered proxy to use
if a node supports it and if it is suitably located (i.e. same 
domain)."""
    pass    
          
class MessageBusPSCProxy(PSCProxy):
    """ Proxy for a PSC that is able only to accept RPC calls over
the message bus for whatever reason. """
    pass
          
class LocalPSCProxy(PSCProxy):
    """ Proxy for this 'local' PSC. """
    def call(self, service, method, *args, **kwargs):
        """ Use the following process to call the method:
    - obtain a worker reference
    - call the method in there
    - park the deferred; return a new deferred to the caller of this method
    - if error, reset and try again.
    - if no error, put result onto return deferred.
"""
        while True:
            p = self.kernel.workerStore[service].getRandomProvider()
            try:
                d = p.callRemote('call',method, *args, **kwargs)
                d.addCallback(self.__test)
                return d
            except pb.DeadReferenceError:
                self.kernel.workerStore[service].removeProvider(p)
                
    def __test(self, x):
#        self.kernel.logger.debug("Result: %s" % str(x))
        print("Result: %s" % str(x))
        return x
           
# mapping of proxy to specific RPC mechanisms
# that a PSC may accept
PSC_PROXIES = {'pb'  : TwistedPSCProxy,
               'bus' : MessageBusPSCProxy}
