# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details

from twisted.internet import reactor
from twisted.spread import pb
from twisted.internet.error import CannotListenError
from peloton.adapters import AbstractPelotonAdapter
import logging

class PelotonPBAdapter(AbstractPelotonAdapter, pb.Root):
    """ The primary client adapter for Peloton is the Python Twisted PB
RPC mechanism. This provides the most complete and sophisticated
interface to the Peloton grid. This adapter is just a gate-keeper though;
anything obtaining this must gain trust and obtain a Referenceable 
through which real work can be done.
"""
    def __init__(self, kernel):
        AbstractPelotonAdapter.__init__(self, kernel, 'TwistedPB')
        self.logger = logging.getLogger()
    
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
                self.enabled = True
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
        self.enabled = False

    def stop(self):
        """ Close down this adapter. """
        d = self.connection.stopListening()
        d.addCallback(self._stopped)
                
    def remote_registerPSC(self, remotePSC, token):
        """ A remote PSC will call registerPSC with a token encrypted
with the domain key. Provided this decrypts we know the remote PSC is
permitted to join in this domain. the remotePSC is a remote instance of
PelotonGridAdapter which provides methods for inter-PSC work.

@todo: it may be that the token can be included in the remotePSC using
copyable type stuff.
"""
        pass

    def remote_registerWorker(self, worker, token):
        """ A worker registers by sending a KernelInterface
referenceable and a token. The token was passed to the worker
generator and is used simply to verify that this is indeed a valid
and wanted contact. """
        pass
    
    def remote_getInterface(self, name):
        """ Return the named interface to a plugin. """
        return self.kernel.getCallable(name)
    
class PelotonGridAdapter(pb.Referenceable):
    def remote_call(self, clientObj, service, method, *args, **kwargs):
        raise NotImplementedError
    
    def remote_login(self, clientObj):
        """ Login to Peloton. The clientObj contains the credentials to be
used."""
        raise NotImplementedError
    
    def remote_post(self, clientObj, service, method, *args, **kwargs):
        raise NotImplementedError
    
    def remote_postLater(self, sessionId, delay_seconds, service, method, *args, **kwargs):
        raise NotImplementedError

    def remote_postAt(self, sessionId, dateTime, service, method, *args, **kwargs):
        raise NotImplementedError
    
    def remote_fireEvent(self, sessionId, eventChannel, eventName, payload):
        raise NotImplementedError
    
    def remote_subscribeToEvent(self, sessionId, eventChannel, eventName=None):
        raise NotImplementedError
    
class PelotonWorkerAdapter(pb.Referenceable):
    """ Interface by which a worker may invoke actions on the kernel. """
    pass