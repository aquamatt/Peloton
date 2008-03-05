# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
""" The PelotonWorker and related classes are defined in this module.

A worker is started by a generator that is tied to a PSC. Separating 
workers from PSC by process ensures that user code running in a service
is unable to derail a PSC or cause such issues that may interfere with 
other services. In this way a service may even make use of the event loop
in its worker container, thus becoming asynchronous without risking 
over-burdening the PSC event loop, nor of locking it.

The PSC and Generator communicate as follows::

   PSC                                   Generator
    | --- setHostParams(host, port) -------->|
    | --- startWorker(key) ----------------->|
                                     <fork a worker>
    |                                        |
    |                                      Worker
    | <--- getRoot() (initialise RPC) -------|
    | ---- return Root object (1) ---------->|
    | <--- setWorker(key, workerRemote (2)) -|
    | ---- return PSC Referenceable(3) ----->|

(1) is the peloton.kernel.PSCRoot; (2) is the peloton.worker.KernelInterface 
referenceable and (3) is the peloton.kernel.WorkerInterface referenceable.

The worker is now able to receive instructions from the PSC and is also
able to register with events on the PSC as well as pass other messages back.
"""

from twisted.internet import reactor
from twisted.spread import pb
from peloton.base import HandlerBase

class PelotonWorker(HandlerBase):
    """ A Peloton Worker manages services, executes methods and returns
results to its controling PSC. 
"""

    def __init__(self, pscHost, pscPort, options, args):
        """ The parent PSC is found at pscHost:pscPort - the host
will in general be the host on which this worker resides but we
allow for other scenarios by passing the host through at this point.

options and args are the options and args passed into the application
from the command line.
"""
        HandlerBase.__init__(self, options, args)
        self.pscHost = pscHost
        self.pscPort = pscPort
        self.serviceManager = ServiceManager()     
    
    def start():
        """ Start this worker; returns an exit code when worker closes down. """
        return 0
    
    def closedown(self):
        self.serviceManager.stopAllServices()
        reactor.stop()
    
class ServiceManager(object):
    """ The class which manages all services in a worker and through
which methods are called."""
    def __init__(self):
        self.services = {}
    
    def loadService(self, name):
        """ Loading a service happens as follows:
    - Locate service class
    - Validate it's signature cookie ???
    - Instantiate: Here the configuration files are read and 
internals are organised. This is generally NOT overidden by the
service writer who instead provides the startup() method to do logical
business level initialisation.

Raises Exception if the name is invalid.
        """
        pass
    
    def startService(self, name):
        """ Call serviceClass.startup(): this is the method which sets up
loggers, starts connection pools and does any other initialisation 
the service might require. 

Raises Exception if the name is invalid."""
        try:
            self.services[name].startup()
        except KeyError:
            raise Exception("Unknown service named: %s" % name)
        except:
            raise
    
    def stopService(self, name):
        """ Calls shutdown() on the named service. 
        
Raises Exception if the name is invalid."""
        try:
            self.services[name].shutdown()
        except KeyError:
            raise Exception("Unknown service named: %s" % name)
        except:
            raise
        
    def stopAllServices(self):
        for s in self.serices.values():
            s.stop()

class KernelInterface(pb.Referenceable):
    """ This class mediates between the worker and the kernel; it
is the means by which the kernel requests services be started and stopped,
and calls methods to be run."""

    def __init__(self):
        pb.Referenceable.__init__(self)
        
    def remote_startService(self, name):
        """ Start the named service. The service must be present in the
service path configured at runtime."""
        raise NotImplementedError("Cannot yet start service")
    
    def remote_stopService(self, name):
        """ Stop the named service."""
        raise NotImplementedError("Cannot yet stop service")
    
    def remote_call(self, service, method, *args, **kwargs):
        raise NotImplementedError("Cannot yet call a method")
