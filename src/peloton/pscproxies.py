# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details

from twisted.spread import pb
from twisted.internet import reactor
from twisted.internet.error import ConnectionRefusedError
from twisted.internet.error import ConnectionDone
from twisted.internet.defer import Deferred
from peloton.exceptions import PelotonConnectionError
from peloton.exceptions import PelotonError
from peloton.exceptions import DeadProxyError
from peloton.exceptions import NoWorkersError

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
        self.ACCEPTING_REQUESTS = True
        self.RUNNING = True
        
    def call(self, service, method, *args, **kwargs):
        """ Request the serice method be called on this 
PSC. """
        raise NotImplementedError
        
    def stop(self):
        """ May be implemented if some action on stop is required. """
        self.RUNNING = False
        
class LocalPSCProxy(PSCProxy):
    """ Proxy for this 'local' PSC. """
    
    def call(self, service, method, *args, **kwargs):
        """ Use the following process to call the method:
    - obtain a worker reference
    - call the method in there
    - park the deferred; return a new deferred to the caller of this method
    - if error, reset and try again.
    - if no error, put result onto return deferred.
    
The coreio call method will receive a deferred OR a NoProvidersError
will be raised.
"""
        rd = Deferred()
        rd._peloton_loopcount = 0 # used in _call
        self._call(rd, service, method, args, kwargs)
        return rd
    
    def _call(self, rd, service, method, args, kwargs):
        while True:
            try:
    #            p = self.kernel.workerStore[service].getRandomProvider()
                p = self.kernel.workerStore[service].getNextProvider()
                d = p.callRemote('call',method, *args, **kwargs)
                d.addCallback(rd.callback)
                d.addErrback(self.__callError, rd, p, service, method, args, kwargs)
                break
            except pb.DeadReferenceError:
                self.logger.error("Dead reference for %s provider" % service)
                self.kernel.workerStore[service].notifyDeadProvider(p)
                
            except NoWorkersError:
                # Clearly we expect to be able to provide this service
                # otherwise we'd not be here so it is quite likely that
                # for some reason all the workers got zapped and more are
                # in the process of starting. We'll try periodicaly to see 
                # if this is true but after 3 seconds timeout and give up 
                # for good.
                if rd._peloton_loopcount >= 300:
                    rd.errback(NoWorkersError("No workers for service %s" % service))
                else:
                    rd._peloton_loopcount+=1
                    reactor.callLater(0.01, self._call, rd, service, method, args, kwargs)
                break
   
    def __callError(self, err, rd, p, service, method, args, kwargs):
        """ A twisted error occured when making the remote call. This is going
to be one of:

    - An application error raised in the service - this must pass through. It
      will be characterised by err.value being a string
    - A connection was broken whilst the call was being made; flag the provider
      as dead and start again. This is signified by err.value being a 
      pb.PBConnectionLost error.
    - The connection was closed cleanly whilst performing the operation; likely
      the service was re-started. Current protocol is to re-issue the request but
      in future the old worker may well finish the job so this error will not
      be raised. This condition is signified by err.value being a ConnectionDone
      instance.
"""
        if isinstance(err.value, pb.PBConnectionLost) or \
             isinstance(err.value, ConnectionDone):
            if self.RUNNING:
                self.kernel.workerStore[service].notifyDeadProvider(p)
                self._call(rd, service, method, args, kwargs)
            else:
                rd.errback(NoWorkersError("No workers for service %s" % service))
        else:
            rd.errback(err)
        
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
            raise DeadProxyError("Cannot accept requests.")
        d = Deferred()
        if self.remoteRef == None:
            self.requestCache.append([d, service, method, args, kwargs])
            if not self.CONNECTING:
                self.__connect()
        else:
            try:
                self.__call(d, service, method, args, kwargs)
            except pb.DeadReferenceError:
                self.ACCEPTING_REQUESTS = False
                raise DeadProxyError("Dead reference to remote PSC")
        return d
    
    def __call(self, d, service, method, args, kwargs):
        cd = self.remoteRef.callRemote('relayCall', service, method, *args, **kwargs)
        cd.addCallback(d.callback)
        cd.addErrback(self.__callError, d, service, method)
    
    def __callError(self, err, d, service, method):
#        self.logger.error("** Call error calling %s.%s: %s" % (service, method, err.parents[-1]))
        if err.parents[-1] == 'twisted.spread.pb.PBConnectionDone' or \
           err.parents[-1] == 'twisted.spread.pb.PBConnectionLost':
#            self.logger.error("CALL ERROR %s CALLING %s.%s" % (err.parents[-1], service, method))
            d.errback(DeadProxyError("Peer closed connection"))
        else:
            d.errback(err)
          
    def __connect(self):
        """ Connections to peers are made on demand so that only
links that are actively used get made. This is the start of the
connect sequence."""
        self.CONNECTING = True
#        self.logger.debug("CONNECT TO REMOTE PSC")
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

        while self.requestCache:
            req = self.requestCache.pop(0)
            d = req[0]
            d.errback(DeadProxyError("Peer not present before connect"))

    def stop(self):
        if self.RUNNING:
            self.ACCEPTING_REQUESTS = False
            PSCProxy.stop(self)
            self.peer = self.remoteRef = None
          
class MessageBusPSCProxy(PSCProxy):
    """ Proxy for a PSC that is able only to accept RPC calls over
the message bus for whatever reason. """
    pass


# mapping of proxy to specific RPC mechanisms
# that a PSC may accept
PSC_PROXIES = {'pb'  : TwistedPSCProxy,
               'bus' : MessageBusPSCProxy}
          