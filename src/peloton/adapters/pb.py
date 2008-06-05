# $Id: pb.py 120 2008-04-10 17:54:14Z mp $
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details

from twisted.internet import reactor
from twisted.spread import pb
from twisted.internet.error import CannotListenError
from peloton.adapters import AbstractPelotonAdapter
from peloton.profile import PelotonProfile
from peloton.coreio import PelotonRequestInterface
from peloton.coreio import PelotonInternodeInterface
from peloton.events import RemoteEventHandler
from peloton.exceptions import PelotonError

class PelotonPBAdapter(AbstractPelotonAdapter, pb.Root):
    """ The primary client adapter for Peloton is the Python Twisted PB
RPC mechanism. This provides the most complete and sophisticated
interface to the Peloton grid. This adapter is just a gate-keeper though;
anything obtaining this must gain trust and obtain a Referenceable 
through which real work can be done.
"""
    def __init__(self, kernel):
        AbstractPelotonAdapter.__init__(self, kernel, 'TwistedPB')
        self.logger = self.kernel.logger
    
    def start(self, configuration, cmdOptions):
        """ In this startup the adapter seeks to bind to a port. It obtains
the host/port to which to bind from the configuration offered to it, but it
may, according to whether the 'anyport' switch is set or not, seek an 
alternative port should its chosen target be bound by another application.
"""
        interface,port = configuration['psc.bind'].split(':')
        port = int(port)
        
        svr = pb.PBServerFactory(self)
        while True:
            try:
                self.connection = reactor.listenTCP(port, svr, interface=interface)
                configuration['psc.bind'] = "%s:%d" % (interface, port)
                configuration['psc.bind_interface'] = interface
                configuration['psc.bind_port'] = port
                break
            except CannotListenError:
                if cmdOptions.anyport:
                    port += 1
                else:
                    raise RuntimeError("Cannot bind to port %d" % port)
            except Exception:
                self.logger.exception("Could not connect %s" % self.adapterName)

        self.logger.info("Bound to %s:%d" % (interface, port))
         
    def _stopped(self, x):
        """ Handler called when reactor has stopped listening to this
protocol's port."""
        pass

    def stop(self):
        """ Close down this adapter. """
        d = self.connection.stopListening()
        d.addCallback(self._stopped)
                
    def remote_registerPSC(self, token):
        """ A remote PSC will call registerPSC with a token encrypted
with the domain key. Provided this decrypts we know the remote PSC is
permitted to join in this domain. the remotePSC is a remote instance of
PelotonGridAdapter which provides methods for inter-PSC work.

@todo: it may be that the token can be included in the remotePSC using
copyable type stuff.
"""
        self.logger.info("RegisterPSC %s: ref returned with NO VALIDATION" % token)
        ref = PelotonInternodeAdapter(self.kernel, token)
        return ref
    
    def remote_registerWorker(self, worker, token):
        """ A worker registers by sending a KernelInterface
referenceable and a token. The token was passed to the worker
generator and is used simply to verify that this is indeed a valid
and wanted contact."""
        self.logger.info("Starting worker, token=%s NOT VALIDATED" % token)        
        serviceName, publishedName, runtimeConfig = self.kernel.addWorker(worker, token)
        pwa = PelotonWorkerAdapter(self, serviceName, self.kernel)
        worker.checkBeat = pwa.checkBeat
        
        workerInfo = { 'pwa' : pwa,
                      'serviceName' : serviceName,
                      'publishedName' : publishedName,
                      'runtimeConfig' : runtimeConfig,
                      'loglevel' : self.kernel.initOptions.loglevel,
                      'logdir' : self.kernel.initOptions.logdir,
                      'servicePath' : self.kernel.initOptions.servicepath,
                      'gridMode' : self.kernel.config['grid.gridmode'],
                      }
        
        return workerInfo
    
    def remote_login(self, clientObj):
        """ Login to Peloton. The clientObj contains the credentials to be
used. Returns a PelotonClientAdapter"""
        return PelotonClientAdapter(self.kernel, clientObj)

class PelotonInternodeAdapter(pb.Referenceable):
    """ Used to call between PSCs. """
    def __init__(self, kernel, peerGUID):
        self.requestInterface = PelotonInternodeInterface(kernel)
        self.logger = kernel.logger
        self.peerGUID = peerGUID
        self.kernel = kernel
        
    def remote_relayCall(self, service, method, *args, **kwargs):
        """ Relay a method call between PSCs. """
        return self.requestInterface.public_relayCall(self.peerGUID, service, method, *args, **kwargs)
   
    def remote_getInterface(self, name):
        """ Return the named interface to a plugin. """
        return self.kernel.getCallable(name)
    
class PelotonClientAdapter(pb.Referenceable):
    """ Referenceable used by client to call methods on the PSC. """
    def __init__(self, kernel, clientObj):
        self.dispatcher = kernel.dispatcher
        self.profile = kernel.profile
        self.routingTable = kernel.routingTable
        self.requestInterface = PelotonRequestInterface(kernel)
        self.logger = kernel.logger
        self.clientObj = clientObj
        self.eventHandlers=[]
        
    def remote_call(self, service, method, *args, **kwargs):
        """ Make a call to the specified service.method and return the result."""
        return self.requestInterface.public_call(self.clientObj, 'raw', service, method, args, kwargs)
   
    def remote_post(self, service, method, *args, **kwargs):
        """ Put a call on the call queue for later execution. Do not
return result to client; this call will execute regardless of what the
client does subsequently. """
        raise NotImplementedError
    
    def remote_postLater(self, delay_seconds, service, method, *args, **kwargs):
        """ Post call onto the call queue after a delay of delay_seconds. """
        raise NotImplementedError

    def remote_postAt(self, dateTime, service, method, *args, **kwargs):
        """ Post call onto the call queue at some future time. """
        raise NotImplementedError
    
    def remote_fireEvent(self, key, exchange='events', **kwargs):
        """ Fire an event onto the bus. """
        self.dispatcher.fireEvent(key, exchange, **kwargs)
    
    def remote_register(self, key, handler, exchange='events'):
        """ Register to receive events with the given handler. Handler
must be a Referenceable providing remote_eventReceived."""
        handler = RemoteEventHandler(handler)
        self.eventHandlers.append(handler)
        self.dispatcher.register(key, handler, exchange)
    
    def remote_deregister(self, handler):
        """ De-register handler as a listener. """
        for h in self.eventHandlers:
            if h.remoteHandler == handler:
                handler = h
                break
        else:
            # no handler registered
            self.logger.error("Attempt to de-register handler for event that is not registered.")
            return

        self.dispatcher.deregister(handler)
        self.eventHandlers.remove(handler)
   
    def remote_getPSCProfile(self, guid=None):
        """ Returns the serialised profile for the referenced PSC or self if guid
is None. """
        if not guid:
            return repr(self.profile)
        else:
            try:
                return repr(self.routingTable.pscByGUID[guid].profile)
            except KeyError:
                raise PelotonError("%s is unknown" % guid)
    
    def remote_getRegisteredExchanges(self):
        """ Return a list of event exchanges registered in the dispatcher. """
        return self.dispatcher.getRegisteredExchanges()
        
class PelotonWorkerAdapter(pb.Referenceable):
    """ Interface by which a worker may invoke actions on the kernel. """
    def __init__(self, name, pscRef, kernel):
        self.name = name
        # each time the worker calls, this sets to zero
        # each time the PSC checks it increments the value by
        # one... if the value hits a threshold, e.g. 5, the
        # worker is considered dead.
        self.heartBeat = 0
        self.kernel = kernel
        self.pscRef = pscRef
        self.eventHandlers = []
        
    def remote_notifyClosedown(self):
        """ Called when the worker is closing down. """
        pass
    
    def remote_fireEvent(self, key, exchange, **kwargs):
        """ Fire an event onto the bus. """
        self.kernel.dispatcher.fireEvent(key, exchange, **kwargs)
    
    def remote_register(self, key, handler, exchange='events'):
        """ Register to receive events with the given handler. Handler
must be a Referenceable providing remote_eventReceived."""
        handler = RemoteEventHandler(handler)
        self.eventHandlers.append(handler)
        self.kernel.dispatcher.register(key, handler, exchange)
    
    def remote_deregister(self, handler):
        """ De-register handler as a listener. """
        for h in self.eventHandlers:
            if h.remoteHandler == handler:
                handler = h
                break
        else:
            # no handler registered
            self.logger.error("Attempt to de-register handler for event that is not registered.")
            return

        self.kernel.dispatcher.deregister(handler)
        self.eventHandlers.remove(handler)

    def remote_heartBeat(self):
        """ Called by the client to provide proof of life."""
        self.heartBeat = 0

    def checkBeat(self, threshold=5):
        """ Called from the PSC to check whether the worker
is OK. the heartBeat counter is incremented. If the counter 
exceeds the threshold value (default 5) checkBeat returns False,
otherwise returns True. """
        self.heartBeat += 1
        return self.heartBeat <= threshold

    def remote_serviceStartOK(self, version):
        """ Called to indicate safe start of service requested. """
        self.kernel.logger.info("Worker reports start OK for %s %s" % (self.name, version))
    
    def remote_serviceStartFailed(self, ex):
        """ Called with exception if service failed to start. """
        self.kernel.logger.info("Worker reports start failed for %s : %s" % (self.name, ex))
    