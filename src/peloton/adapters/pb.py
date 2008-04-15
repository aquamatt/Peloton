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
        serviceName = self.kernel.addWorker(worker, token)
        pwa = PelotonWorkerAdapter(self, serviceName, self.kernel)
        worker.checkBeat = pwa.checkBeat
        
        return (pwa,
                serviceName,
                self.kernel.initOptions.loglevel,
                self.kernel.initOptions.logdir,
                self.kernel.initOptions.servicepath,
                self.kernel.config['grid.gridmode'])
    
    def remote_login(self, clientObj):
        """ Login to Peloton. The clientObj contains the credentials to be
used. Returns a PelotonClientAdapter"""
        return PelotonClientAdapter(self.kernel, clientObj)

    def remote_getInterface(self, name):
        """ Return the named interface to a plugin. """
        return self.kernel.getCallable(name)
    
class PelotonInternodeAdapter(pb.Referenceable):
    def __init__(self, kernel, peerGUID):
        self.requestInterface = PelotonInternodeInterface(kernel)
        self.logger = kernel.logger
        self.peerGUID = peerGUID
        
    def remote_relayCall(self, service, method, *args, **kwargs):
        return self.requestInterface.public_relayCall(self.peerGUID, service, method, *args, **kwargs)
   

class PelotonClientAdapter(pb.Referenceable):
    def __init__(self, kernel, clientObj):
        self.requestInterface = PelotonRequestInterface(kernel)
        self.logger = kernel.logger
        self.clientObj = clientObj
        
    def remote_call(self, service, method, *args, **kwargs):
        return self.requestInterface.public_call(self.clientObj, 'raw', service, method, args, kwargs)
   
    def remote_post(self, service, method, *args, **kwargs):
        raise NotImplementedError
    
    def remote_postLater(self, delay_seconds, service, method, *args, **kwargs):
        raise NotImplementedError

    def remote_postAt(self, dateTime, service, method, *args, **kwargs):
        raise NotImplementedError
    
    def remote_fireEvent(self, eventChannel, eventName, payload):
        raise NotImplementedError
    
    def remote_subscribeToEvent(self, eventChannel, eventName=None):
        raise NotImplementedError
    
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
        
    def remote_notifyClosedown(self):
        """ Called when the worker is closing down. """
        pass
    
    def remote_fireEvent(self, key, exchange, **kwargs):
        """ Fire an event onto the bus. """
        self.kernel.dispatcher.fireEvent(key, exchange, **kwargs)
    
    def remote_register(self, key, handler, exchange='events'):
        pass
    
    def remote_deregister(self, key, handler, exchange='events'):
        pass

    def remote_heartBeat(self):
        self.heartBeat = 0

    def checkBeat(self, threshold=5):
        """ Called from the PSC to check whether the worker
is OK. the heartBeat counter is incremented. If the counter 
exceeds the threshold value (default 5) checkBeat returns False,
otherwise returns True. """
        self.heartBeat += 1
        return self.heartBeat <= threshold

    def remote_serviceStartOK(self, version):
        self.kernel.logger.info("Worker reports start OK for %s %s" % (self.name, version))
    
    def remote_serviceStartFailed(self, ex):
        self.kernel.logger.info("Worker reports start failed for %s : %s" % (self.name, ex))
    