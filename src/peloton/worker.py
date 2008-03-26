# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
from peloton.exceptions import ServiceNotFoundError
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

# ensure threading is OK with twisted
from twisted.python import threadable
threadable.init()

from twisted.internet import reactor
from twisted.spread import pb
from peloton.base import HandlerBase
from peloton.exceptions import WorkerError
from peloton.exceptions import ServiceConfigurationError
from peloton.exceptions import ServiceNotFoundError    
from peloton.exceptions import ServiceError
from peloton.utils.config import locateService

class PelotonWorker(HandlerBase):
    """ A Peloton Worker manages services, executes methods and returns
results to its controling PSC. 
"""
    def __init__(self, pscHost, pscPort, name, token, options, args):
        """ The parent PSC is found at pscHost:pscPort - the host
will in general be the host on which this worker resides but we
allow for other scenarios by passing the host through at this point.

options and args are the options and args passed into the application
from the command line.
"""
        HandlerBase.__init__(self, options, args)
        self.pscHost = pscHost
        self.pscPort = pscPort
        self.name = name
        self.token = token
    
    def start(self):
        """ Start this worker; returns an exit code when worker 
closes down. """
        reactor.callWhenRunning(self._initialise)
        reactor.run()
        return 0
    
    def _initialise(self):
        """ Start the boot-strap process of connecting to the 
master PSC,  starting the service and announcing ourselves ready to 
rock. """
     
        self.kernelInterface = KernelInterface(self)
        factory = pb.PBClientFactory()
        try:
            reactor.connectTCP(self.host, self.port, factory)
            d = factory.getRootObject()
            d.addCallback(self._clientConnect)
            d.addErrback(self._clientConnectError)
        except Exception, ex:
            raise WorkerError("Could not connect to PSC: %s" % str(ex))

    def _clientConnect(self, rootObj):
        """ Root object obtained; now offer our interface and the token we
were given to start with to validate our presence. """
        self.psc = rootObj
        d = self.psc.callRemote("")
        d.addCallback(self._pscOK)
        d.addErrback(self._clientConnectError)

    def _pscOK(self):
        """ Now start the service. If OK, message the PSC accordingly;
if not, let the PSC know we've failed and why, then initiate closedown. """
        raise NotImplementedError
        
    
    def _clientConnectError(self, err):
        raise WorkerError("Error connecting with PSC: %s" % str(err))
    
    def closedown(self):
        self.stopService()
        reactor.stop()
        
    def loadService(self, name):
        """ Loading a service happens as follows:
    - Locate service class
    - Validate its signature cookie ???
    - Instantiate: Here the configuration files are read and 
internals are organised. This is generally NOT overidden by the
service writer who instead provides the startup() method to do logical
business level initialisation.

Raises ServiceConfigurationError if the name is invalid.
        """
        
        #### got to be in service path and we know it's in 
        #### servicename.servicename.ServiceName
        #### So why not import, instantiate, call loadConfig and
        #### let that load using relative path?
        try:
            servicePath, serviceProfile = \
                locateService(self.name, 
                                self.kernel.initOptions.servicepath, 
                                self.kernel.config['grid.gridmode'])
        except ServiceNotFoundError:
            raise
        
        self.__service = None
    
    def startService(self):
        """ Call serviceClass.startup(): this is the method which sets up
loggers, starts connection pools and does any other initialisation 
the service might require. 
"""
        try:
            self.__service.startup()
        except Exception, ex:
            raise ServiceConfigurationError("Error starting service %s" % self.name, ex)
    
    def stopService(self):
        """ Calls shutdown() on the managed service. """
        try:
            self.__service.shutdown()
        except Exception, ex:
            raise ServiceError("Error stopping service %s" % self.name, ex)

    def call(self, method, *args, **kwargs):
        """ Call and excecute the specified method with args as provided. """
        raise NotImplementedError
        
class KernelInterface(pb.Referenceable):
    """ This class mediates between the worker and the kernel; it
is the means by which the kernel makes method requests etc."""
    def __init__(self, pw):
        """ pw is the parent PelotonWorker class. """
        self.worker = pw
            
    def remote_getState(self):
        """ Return a dictionary of state information. """
        pass
    
    def remote_stop(self, name):
        """ Stop this worker"""
        self.worker.closedown()
    
    def remote_call(self, method, *args, **kwargs):
        """ Return the result of calling method(*args, **kwargs)
on this service. """
        return self.worker.call(method, *args, **kwargs)
