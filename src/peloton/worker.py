# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
""" The PelotonWorker and related classes are defined in this module.

A worker is started by a PSC. Separating 
workers from PSC by process ensures that user code running in a service
is unable to derail a PSC or cause such issues that may interfere with 
other services. In this way a service may even make use of the event loop
in its worker container, thus becoming asynchronous without risking 
over-burdening the PSC event loop, nor of locking it.

The PSC and Generator communicate as follows::

   PSC                                   Generator
    | --- setHostParams(host, port) -------->|
    | --- startWorker(key) ----------------->|
                                  <start worker process>
    |                                        |
    |                                      Worker
    | <--- getRoot() (initialise RPC) -------|
    | ---- return Root object (1) ---------->|
    | <--- registerWorker(...) --------------|
    | ---- return PSC Referenceable(3) ----->|

(1) is the peloton.kernel.PSCRoot; (2) is the peloton.worker.KernelInterface 
referenceable and (3) is the peloton.kernel.WorkerInterface referenceable.

The worker is now able to receive instructions from the PSC and is also
able to register with events on the PSC as well as pass other messages back.

"""

from peloton.utils import bigThreadPool

from twisted.internet import reactor
from twisted.internet.threads import deferToThread
from twisted.spread import pb
from peloton.base import HandlerBase
from peloton.exceptions import WorkerError
from peloton.exceptions import ServiceConfigurationError
from peloton.exceptions import ServiceError
from peloton.utils import getClassFromString
import peloton.utils.logging as logging
import sys

class PelotonWorker(HandlerBase):
    """ A Peloton Worker manages services, executes methods and returns
results to its controling PSC. 
"""
    def __init__(self, pscHost, pscPort, token):
        """ The parent PSC is found at pscHost:pscPort - the host
will in general be the host on which this worker resides but we
allow for other scenarios by passing the host through at this point.
"""
        HandlerBase.__init__(self, None, None)
        self.pscHost = pscHost
        self.pscPort = pscPort
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
            reactor.connectTCP(self.pscHost, self.pscPort, factory)
            d = factory.getRootObject()
            d.addCallback(self._clientConnect)
            d.addErrback(self._clientConnectError)
        except Exception, ex:
            raise WorkerError("Could not connect to PSC: %s" % str(ex))

    def _clientConnect(self, rootObj):
        """ Root object obtained; now offer our interface and the token we
were given to start with to validate our presence. """
        self.psc = rootObj
        d = self.psc.callRemote("registerWorker", self.kernelInterface, self.token)
        d.addCallback(self._pscOK)
        d.addErrback(self._clientConnectError)

    def _pscOK(self, details):
        """ Now start the service. If OK, message the PSC accordingly;
if not, let the PSC know we've failed and why, then initiate closedown. """
        rref, self.name, loglevel, logdir, self.servicepath, self.gridMode = details
        logging.closeHandlers()
        logging.initLogging(rootLoggerName='WORKER: %s' % self.name, 
                            logLevel=getattr(logging, loglevel),
                            logdir=logdir,
                            logfile="worker_%s.log" % self.name,
                            logToConsole=False)

        # add any sevice directories to sys.path if not already there
        for sd in self.servicepath:
            if sd not in sys.path:
                sys.path.append(sd)

        self.loadService()
        self.pscReference = rref
        try:
            self.startService()
            self.pscReference.callRemote('fireEvent', 
                                  'psc.service.notification',
                                  'domain_control',
                                  serviceName=self.name,
                                  state='running',
                                  token=self.token)
            self.pscReference.callRemote('serviceStartOK', self.__service.version)
        except Exception, ex:
            self.pscReference.callRemote('serviceStartFailed', str(ex))
        
    def _clientConnectError(self, err):
        print("Error connecting with PSC: %s" % err.getErrorMessage())
        reactor.stop()
    
    def closedown(self):
        self.stopService()
        reactor.stop()
        
    def loadService(self):
        """ Loading a service happens as follows:
    - Load service class
    - Validate its signature cookie ???
    - Load configs: Here the configuration files are read and 
internals are organised. This is generally NOT overidden by the
service writer who instead provides the startup() method to do logical
business level initialisation.

Raises ServiceConfigurationError if the name is invalid.
        """        
        try:
            pqcn = "%s.%s.%s" % (self.name.lower(), self.name.lower(), self.name)
            cls = getClassFromString(pqcn)
            self.__service = cls(self.name, self.gridMode)
            self.__service.initSupportServices()
            self.__service.loadConfig(self.servicepath)
        except Exception, ex:
            raise ServiceConfigurationError("Could not find class for service %s" % self.name, ex)
    
    def startService(self):
        """ Call serviceClass.start(): this is the method which sets up
loggers, starts connection pools and does any other initialisation 
the service might require. 
"""
        try:
            self.__service.start()
        except Exception, ex:
            raise ServiceConfigurationError("Error starting service %s" % self.name, ex)
    
    def stopService(self):
        """ Calls stop() on the managed service. """
        try:
            self.__service.stop()
        except Exception, ex:
            raise ServiceError("Error stopping service %s" % self.name, ex)

    def call(self, method, *args, **kwargs):
        """ Call and excecute the specified method with args as provided. """
        mthd = getattr(self.__service, "public_%s"%method)
        d = deferToThread(mthd, *args, **kwargs)
        d.addErrback(self.__error)
        return d
    
    def __error(self, err):
        logging.getLogger().debug("ERROR IN WORKER THREAD: %s" % str(err))
        
class KernelInterface(pb.Referenceable):
    """ This class mediates between the worker and the kernel; it
is the means by which the kernel makes method requests etc."""
    def __init__(self, pw):
        """ pw is the parent PelotonWorker class. """
        self.worker = pw
            
    def remote_getState(self):
        """ Return a dictionary of state information. """
        pass
    
    def remote_stop(self):
        """ Stop this worker"""
        self.worker.closedown()
    
    def remote_call(self, method, *args, **kwargs):
        """ Return the result of calling method(*args, **kwargs)
on this service. """
        return self.worker.call(method, *args, **kwargs)
    