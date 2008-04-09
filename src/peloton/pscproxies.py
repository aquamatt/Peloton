# $Id: mapping.py 104 2008-04-02 17:22:55Z mp $
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details

from twisted.python.failure import Failure
from twisted.spread import pb
from twisted.internet import reactor
from twisted.internet.error import ConnectionRefusedError
from twisted.internet.threads import defer
from peloton.exceptions import PelotonConnectionError
from peloton.exceptions import PelotonError
from peloton.exceptions import NoProvidersError

from types import StringType

class PSCProxy(object):        
    """ Base class for PSC proxies through which the routing
table can exchange messages with PSCs. A proxy is required because
the PSC may be the local process, a PSC in the domain or a PSC in
another domain on the grid.
"""
    def __init__(self, kernel, profile):
        self.profile = profile
        self.kernel = kernel
        self.logger = kernel.logger
        
    def call(self, service, method, *args, **kwargs):
        """ Request the serice method be called on this 
PSC. """
        raise NotImplementedError
        
    def stop(self):
        """ May be implemented if some action on stop is required. """
        pass
        
class TwistedPSCProxy(PSCProxy):        
    """ Proxy for a PSC that is running on the same domain as this 
node and accepts Twisted PB RPC. This is the prefered proxy to use
if a node supports it and if it is suitably located (i.e. same 
domain)."""
    def __init__(self, kernel, profile):
        PSCProxy.__init__(self, kernel, profile)
        self.peer = None
        self.remoteRef = None
        self.CONNECTING = False
        self.ACCEPTING_REQUESTS = True
        self.requestCache = []
        
    def call(self, service, method, *args, **kwargs):
        if not self.ACCEPTING_REQUESTS:
            raise PelotonError("Cannot accept requests.")
        d = defer.Deferred()
        if self.remoteRef == None:
            self.requestCache.append([d, service, method, args, kwargs])
            if not self.CONNECTING:
                self.CONNECTING = True
                self.__connect()
        else:
            self.__call(d, service, method, args, kwargs)
        return d
          
    def __call(self, d, service, method, args, kwargs):
        try:
            cd = self.remoteRef.callRemote('relayCall', service, method, *args, **kwargs)
            cd.addCallback(d.callback)
            cd.addErrback(self.__callError, service, method, d)
        except pb.DeadReferenceError, ex:
            self.ACCEPTING_REQUESTS = False
            d.errback(PelotonConnectionError("Dead reference error", ex))
        
    def __callError(self, err, service, method, d):
        self.logger.error("Call error calling %s.%s: %s" % (service, method, err.getErrorMessage()))
        d.errback(err)
          
    def __connect(self):
        """ Connections to peers are made on demand so that only
links that are actively used get made. This is the start of the
connect sequence."""
        factory = pb.PBClientFactory()
        reactor.connectTCP(self.profile['ipaddress'], 
                           self.profile['port'], 
                           factory)
        cd = factory.getRootObject()
        cd.addCallback(self.__peerConnect)
        cd.addErrback(self.__connectError, "Error connecting to peer")
    
    def __peerConnect(self, peer):
        self.peer = peer
        pd = peer.callRemote('registerPSC', self.kernel.guid)
        pd.addCallback(self.__refReceived)
        pd.addErrback(self.__connectError, "Error receiving remote reference")
        
    def __refReceived(self, ref):
        self.remoteRef = ref
        self.CONNECTING = False
        self.logger.info("Referenced received from peer; flushing %d requests" % len(self.requestCache))
        while self.requestCache:
            req = self.requestCache.pop(0)
            d = req[0]
            request = req[1:]
            self.__call(d, *request)
        
    def __connectError(self, err, msg):
        self.ACCEPTING_REQUESTS = False
        self.CONNECTING = False
        self.logger.error("TwistedPSCProxy: %s" % msg)

        if type(err.value) == StringType:
            error = PelotonConnectionError(str([err.value, err.parents[-1], err.parents]))
        else:
            error = PelotonConnectionError(msg, err.value)
            
        while self.requestCache:
            req = self.requestCache.pop(0)
            d = req[0]
            d.errback(error)

    def stop(self):
        self.peer = self.remoteRef = None
          
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
            try:
    #            p = self.kernel.workerStore[service].getRandomProvider()
                p = self.kernel.workerStore[service].getNextProvider()
                return p.callRemote('call',method, *args, **kwargs)
            except NoProvidersError, ex:
                self.logger.error("No workers for service %s" % service)
                raise
            except pb.DeadReferenceError:
                self.logger.error("Dead reference for %s provider" % service)
                self.kernel.workerStore[service].notifyDeadProvider(p)                           
   
# mapping of proxy to specific RPC mechanisms
# that a PSC may accept
PSC_PROXIES = {'pb'  : TwistedPSCProxy,
               'bus' : MessageBusPSCProxy}
