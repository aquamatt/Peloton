# $Id: kernel.py 120 2008-04-10 17:54:14Z mp $
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details

from peloton.utils import bigThreadPool

import os
import random
import socket
import subprocess
import time
import uuid

import peloton.utils.logging as logging

from twisted import __version__ as twistedVersion
from twisted.internet import reactor
from twisted.internet.task import LoopingCall
from twisted.internet.threads import deferToThread
from twisted.spread import pb

from peloton.base import HandlerBase
from peloton.utils.config import PelotonSettings
from peloton.events import EventDispatcher
from peloton.events import MethodEventHandler
from peloton.utils import crypto
from peloton.utils import getClassFromString
from peloton.utils import getExternalIPAddress
from peloton.utils.structs import RoundRobinList
from peloton.mapping import ServiceLoader
from peloton.mapping import RoutingTable
from peloton.mapping import ServiceLibrary
from peloton.exceptions import ConfigurationError
from peloton.exceptions import PluginError
from peloton.exceptions import WorkerError
from peloton.exceptions import NoWorkersError

from sets import Set

class PelotonKernel(HandlerBase):
    """ The kernel is the core that starts key services of the 
node, registers with the grid, pulls together all kernel modules
and provides the means via which components find each other. For example, 
it is the kernel that gathers together the event transceiver and the
coreIO interfaces.
"""

    #: List of classes that provide IO adapters for the Peloton node.
    __PRIMARY_ADAPTERS__ = ["peloton.adapters.pb.PelotonPBAdapter",]
    
    def __init__(self, settings):
        """ Prepare the kernel."""
        HandlerBase.__init__(self, settings)
        self.adapters = {}
        self.serviceLibrary = ServiceLibrary()
        self.workerStore = {}
        self.plugins = {}
        self.dispatcher = EventDispatcher(self)
        
        # used to validate new worker connections
        self.serviceLaunchTokens = {}
        
        # callables are plugin interfaces (pb.Referenceable) that 
        # can be requested by name by clients
        self.callables = {}

        # get path to pwp - it'll be in the same directory
        # as this file. pwp.py starts Peloton workers.
        self.pwp = os.path.split(__file__)[0] + os.sep + 'pwp.py'
        if not os.path.isfile(self.pwp):
            raise Exception("Cannot find worker process launcher %s!" % self.pwp)
        
    def start(self):
        """ Start the Twisted event loop. This method returns only when
the server is stopped. Returns an exit code.

The bootstrap routine is as follows:
    1.  Read the domain and grid keys
    2.  Generate this PSCs session keys and our UID
    3.  Start all the network protocol adapters
    4.  Start kernel plugins
    5.  Initialise routing table, schedule grid-joining workflow to 
        start when the reactor starts
    6. Start the reactor
    
The method returns only when the reactor stops.
"""        
        self.logger.info("Using Twisted version %s" % twistedVersion)
        
        # (1) read in the domain and grid key - all PSCs in a domain must have 
        # access to the same key file (or identical copy, of course)
        self.domainCookie, self.domainKey = \
            self._readKeyFile(self.settings.domainKeyfile)
        self.gridCookie, self.gridKey = \
            self._readKeyFile(self.settings.gridKeyfile)

        # (2) generate session keys
        self.sessionKey = crypto.newKey(512)
        self.publicKey = self.sessionKey.publickey()
        self.guid = str(uuid.uuid1())
        self.profile['guid'] = self.guid
        self.logger.info("Node UUID: %s" % self.profile.guid)
        
        # (3) hook in the PB adapter and any others listed
        self._startAdapters(PelotonKernel.__PRIMARY_ADAPTERS__)
        # the profile address may be different to the bind interface
        # as this should be the address that other nodes can contact
        # us on, ie an external address. So we check to see if the
        # configured interface is 0.0.0.0 or 127.* in which case
        # we use another method to determine our external interface
        if self.profile['bind_interface'].startswith('0.0.0.0') or \
            self.profile['bind_interface'].startswith('127.'):
            self.profile['ipaddress'] = getExternalIPAddress()
            self.logger.info("Auto-detected external address: %s" % self.profile['ipaddress'])
        else:
            self.profile['ipaddress'] = self.profile['bind_interface']
        self.profile['port'] = self.profile['bind_port']        
        self.profile['hostname'] = socket.getfqdn()
        self._startAdapters(self.settings.adapters)

        # (4) Start any kernel plugins, e.g. message bus, shell and
        #     then instruct the dispatcher to get the external bus
        self._startPlugins()
        self.dispatcher.joinExternalBus()

        # (5) Initialise the routing table and schedule grid-joining 
        #     workflow to happen on reactor start
        #  -- this checks the domain cookie matches ours; quit if not.
        self.serviceLoader = ServiceLoader(self)
        self.routingTable = RoutingTable(self)
        self.domainManager = DomainManager(self)
        reactor.callWhenRunning(self.routingTable.notifyConnect)

        # (6) ready to start!
        reactor.run()
        
        return 0

    def _readKeyFile(self, keyfile):
        """ Read in the named keyfile and return a tuple of cookie and
key. Keyfile is relative to the config file or an absolute path"""
        try:
            if keyfile[0]!='/':
                keyfile = os.path.abspath( \
                        os.path.split(self.settings.configfile)[0] \
                        +os.sep+keyfile)
            if os.path.isfile(keyfile):
                cookie, key = crypto.loadKeyAndCookieFile(keyfile)
            else:
                raise ConfigurationError("Key file is unreadable, does not exist or is corrupted: %s" % keyfile)
        except Exception, ex:
            raise ConfigurationError("Key file is unreadable, does not exist or is corrupted: %s (%s)" % (keyfile, str(ex)))
        return(cookie, key)

    def hasFlag(self, flag):
        """ Return true if 'flag' was set on the command line. """
        return flag in self.profile.flags

    def closedown(self, x=0):
        """Closedown in an orderly fashion."""
            
        # tidy up kernel
        if x == 0:
            # Closedown all worker nodes
            self.logger.info("Closing down workers")
            for v in self.workerStore.values():
                try:
                    v.closeAll()
                except:
                    pass

            self.logger.info("Notifying domain")
            self.routingTable.notifyDisconnect()
            # this  is a really cheap and nasty hack - 
            # not putting in this delay meant that sometimes
            # the notification above would not get out before
            # the application quit. need to look to using ACK
            # in the message bus.
            reactor.callLater(1, self.closedown, 1)
        elif x == 1:
            self.logger.info("Stopping adapters")
            self._stopAdapters()
            self.logger.info("Stopping plugins")
            self._stopPlugins()
            # stop the reactor
            reactor.stop()

    def _startPlugins(self):
        """ Start plugins as in configuration adhering to the sort order
implied by any plugin configurations specifying the 'order' attribute. """

        def pluginsort(pa, pb):
            """ Sort plugins according to the 'order' attribute. If 
'order' not specified for either pa or pb, return 0 (equality); if
'order' specified only for one - that is considered the smallest; 
otherwise compare based on 'order' values. 

Note that pa/pb are actually tupples of (name, profile)"""
            _pa = pa[1]
            _pb=pb[1]
            if not _pa.has_key('order'):
                _pa.order=9999
            if not _pb.has_key('order'):
                _pb.order=9999

            return cmp(_pa.order, _pb.order)

        pluginConfs = self.settings['plugins']
        plugins = pluginConfs.items()
        plugins.sort(pluginsort)
        for plugin, _ in plugins:
            self.startPlugin(plugin)
    
    def startPlugin(self, plugin):
        """ Start the plugin named 'plugin'. """
        pconf = self.settings['plugins'][plugin]
        # check that has children, including 'class' otherwise this
        # is just some random key in the 'plugins' section of the 
        # config
        if not pconf.has_key('classname'):
            self.logger.error("No classname specified for plugin %s" % plugin)
            return

        if (pconf.has_key('enabled') and \
            pconf['enabled'] == True and \
            plugin not in self.settings.disable) \
            or \
            plugin in self.settings.enable:
            self.logger.info("Starting plugin: %s" % plugin)
        else:
            self.logger.info("Plugin %s disabled" % plugin)
            return
            
        if self.plugins.has_key(plugin):
            if not self.plugins[plugin].started:
                try:
                    self.plugins[plugin].start()
                    self.plugins[plugin].started=True
                except:
                    raise
        else:
            pluginClass = getClassFromString(pconf['classname'])
            plogger = logging.getLogger(plugin)
            try:
                pluginInstance = pluginClass(self, plugin, pconf, plogger)
                pluginInstance.initialise()
                pluginInstance.start()
                pluginInstance.started=True
                self.plugins[pluginInstance.name] = pluginInstance
            except:
                raise

    def stopPlugin(self, plugin):
        if self.plugins.has_key(plugin):
            if self.plugins[plugin].started:
                self.logger.info("Stopping plugin: %s"%plugin)
                self.plugins[plugin].stop()
                self.plugins[plugin].started=False
            else:
                self.logger.info("Plugin not started: %s" % plugin)
        else:
            raise PluginError("Invalid plugin: %s" % plugin)
            
    def _stopPlugins(self):
        ## I realise order is not preserved here... 
        for p in self.plugins.keys()[::-1]:
            self.stopPlugin(p)

    def _startAdapters(self, adapterList):
        """Prepare all protocol adapters for use. Each adapter
has a start(config, initOptions) method which does initial setup and 
hooks into the reactor. It is passed the entire config stack 
(self.config) and command line options"""
        for adapter in adapterList:
            self.logger.info("Starting adapter: %s" % adapter)
            cls = getClassFromString(adapter)
            _adapter = cls(self)
            self.adapters[_adapter.name] = _adapter
            _adapter.start()
    
    def _stopAdapters(self):
        """ Close down all adapters currently bound. """
        for adapter in self.adapters.values():
            adapter.stop()

    def launchService(self, serviceName, runconfig=None):
        """ Initiate the process of launching a service. """
        self.serviceLoader.launchService(serviceName, runconfig)

    def stopService(self, publishedName):
        """ Signal the grid to stop the named service on this domain. """
        profile, _ = self.serviceLibrary.getProfile(publishedName)
        serviceName = profile['name']
        self.logger.debug("Instructed to stop %s (%s)" % (serviceName, publishedName))
        self.domainManager.sendCommand('SERVICE_SHUTDOWN', serviceName=serviceName, 
                                       publishedName=publishedName)
    
    def _stopService(self, publishedName):
        """ Stop all workers running the named service. """
        self.logger.info("Stopping service: %s" % publishedName)
        try:
            workers = self.workerStore[publishedName]
            workers.closeAll()
            del(self.workerStore[publishedName])
        except KeyError:
            # not running this service 
            pass

    def startServiceGroup(self, serviceName, publishedName, numWorkers=None):
        """ Instruct start of a new group of worker processes running service named serviceName. 
The number of workers is determined from the profile but can be overridden with 
numWorkers if set. The previous service group for this service, if one was running,  is
stopped by the process started here.
"""
        profile, _ = self.serviceLibrary.getProfile(publishedName)
        if numWorkers == None:
            numWorkers = profile.launch.workersperpsc
            
        self.workerStore[publishedName] = \
            ServiceWorkerGroup(self, serviceName, publishedName)
            
        for i in xrange(numWorkers):
            self.startService(serviceName, publishedName, profile)
        
    def startService(self, serviceName, publishedName, profile=None):
        """ Instruct start of a single worker process running service 
named serviceName. """
        tok = crypto.makeCookie(20)
        if not profile:
            profile, _ = self.serviceLibrary.getProfile(publishedName)
        self.serviceLaunchTokens[tok] = [serviceName, 
                                         profile]
        
        d = deferToThread(self._startWorkerProcess, tok)
        d.addCallback(self._workerStarted, serviceName)

    def _startWorkerProcess(self, token):
        """ Run in a thread by startService to spawn the 
worker process and initialise. """
        pipe= subprocess.Popen(['python', self.pwp, 
                          self.profile['ipaddress'], 
                          str(self.profile['port'])],
                          stdin=subprocess.PIPE).stdin
        pipe.write("%s\n" % token)

    def _workerStarted(self, _, service):
        self.logger.info("Workers spawned for %s" % service)

    def addWorker(self, ref, token):
        """ Store a reference to a worker keyed on name.
Returns the name of the service referenced by this token"""
        try:
            launchRecord = self.serviceLaunchTokens[token]
        except KeyError:
            raise WorkerError("Invalid start request.")

        serviceName, profile = launchRecord
        publishedName = profile['publishedName']
        runtimeConfig = profile['_sysRunConfig']
        self.workerStore[publishedName].addWorker(ref)
        del self.serviceLaunchTokens[token]
        return serviceName, publishedName, runtimeConfig
    
    def getCallable(self, name):
        """ Return the callable as named"""
        if not self.callables.has_key(name):
            raise PluginError("No plugin interface known by name %s" % name)
        return self.callables[name]
    
    def registerCallable(self, name, iface):
        """ Register a pb.Referenceable interface by name so that
it can be obtained by remote clients. This is the mechanism by which
kernel plugins may publish callable interfaces. """
        if isinstance(iface, pb.Referenceable):
            self.logger.info("Registering interface: %s" % name)
            self.callables[name] = iface
        else:
            raise PluginError("Cannot register interface for %s: Not referenceable" % name)
        
    def deregisterCallable(self, name):
        """ Un-register the named interface """
        if not self.callables.has_key(name):
            self.logger.info("De-Registering interface: %s not registered!" % name)
        else:
            del(self.callables[name])
            self.logger.info("De-Registering interface: %s" % name)

class DomainManager(object):
    """ Wrapper for communications over the domain_control channel
on the event bus. This manages:

    - monitoring the domain command channel for instructions such
      as 'closedown', 'restart' etc.
""" 
    def __init__(self, kernel):
        self.kernel = kernel
        self.dispatcher = self.kernel.dispatcher
        self._setHandlers()

        # dictionary holding cookies for the command processor
        # this is purged every so often by the reactor task
        self.commandCookies={}
        LoopingCall(self._purgeCommandCookies).start(120, False)

    def respond_commandRequest(self, msg, exch, key, ctag):
        """ Processes domain mesh control signals such as:
        
    - MESH_CLOSEDOWN
    - NOOP (a special debug-only command that does nothing)

Clearly we wish only to accept these commands from valid nodes
so the command and its arguments are encrypted as follows:

    - A dict is constructed:
    - key 'cookie' is a random key
    - key 'time' is the time of issue
    - key 'issuer' is the GUID of the issuer: must match envelope
    - remaining keys are the 'command' and 'args'
    - the domain public key is used to encrypt the dict
    - Upon receipt all nodes decrypt and obtain the cookie.
    - Any command where the message envelope sender GUID does not
      match the 'issuer' field in the encrypted command is
      discarded
    - Any command with issue time > 30 seconds ago is discarded
    - Any command with issue time < 30 second and a cookie that
      is found in the command cookie cache for that host is discarded
    - If command still valid, it is executed.
    
The key cache is flushed periodically of all keys for commands issued
more than 30 seconds ago.

A man in the middle may capture the encrypted packet but cannot re-issue
as the cookie will indicate a repeat or the issue time will be too far in
the past. Without the domain key he cannot decrypt the command or encrypt 
his own commands.
"""
        envelopeSender = msg['sender_guid']
        command = crypto.decrypt(msg['command'], self.kernel.domainKey)
        sender = command['issuer']
        
        if envelopeSender != sender:
            self.kernel.logger.warning("Potential intruder: domain command issued with mis-match sender GUID")
        now = time.time()
        
        if command['time']+30 < now:
            self.kernel.logger.warning("Potential intruder: Out of date command received.")
            return
        
        k = "%s%s" % (sender, command['cookie'])
        if k in self.commandCookies.keys():
            self.kernel.logger.warning("Potential intruder: Repeat command received.")
            return
        
        self.commandCookies[k] = now
        
        if command['command'] == 'MESH_CLOSEDOWN':
            # call later to allow the remaining events
            # to be processed otherwise there can be a messy
            # shutdown...
            reactor.callLater(0.01, self.kernel.closedown)
            
        if command['command'] == 'SERVICE_SHUTDOWN':
            reactor.callLater(0.01, self.kernel._stopService, command['publishedName'])
        
        elif command['command'] == 'NOOP':
            self.kernel.logger.debug("NOOP Called on domain_control")
            
    def sendCommand(self, command, *args, **kwargs):
        """ Send a command in the manner described in respond_commandRequest. 
*args are placed in msg['args'] and any keyword arguments are added to msg.
If kwargs are supplied that conflict with required msg arguments (ie
command, args, cookie, time or issuer) an exception will be raised."""
        now = time.time()
        msg = {'command':command, 
               'args':args,
               'cookie':crypto.makeCookie(20),
               'time':now,
               'issuer':self.kernel.guid }
        # raise Exception if any keys in kwargs match those in the
        # msg which are all considered 'protected'. Prevents accidental
        # overwriting
        msgKeySet = Set(msg.keys())
        kwargsKeySet = Set(kwargs.keys())

        if (msgKeySet-kwargsKeySet) != msgKeySet:
            raise Exception("Send command given kwargs that attempt overwrite of restricted keys. ")
        
        msg.update(kwargs)
        
        ct = crypto.encrypt(msg, self.kernel.domainKey)
        self.dispatcher.fireEvent(key="psc.command",
                                exchange="domain_control",
                                command=ct)
        
        # special debug condition - tests the security mechanism
        if command=='NOOP':
            reactor.callLater(5, self.dispatcher.fireEvent, key="psc.command",
                                exchange="domain_control",
                                command=ct)

            reactor.callLater(31, self.dispatcher.fireEvent, key="psc.command",
                                exchange="domain_control",
                                command=ct)

    def _purgeCommandCookies(self):
        """ Called from a reactor task loop, this simply purges the
cookie jar of cookies > 30 seconds old. """
        now = time.time()
        n=0
        for k,v in self.commandCookies.items():
            if v+30<now:
                del(self.commandCookies[k])
                n+=1
        if n:
            self.kernel.logger.debug("Purging command cookies (%d)" % n)
    
    def _setHandlers(self):
        """ Register for all the events we are interested in. """
        # the command channel
        self.dispatcher.register("psc.command",
                MethodEventHandler(self.respond_commandRequest),
                "domain_control" )
        
class ServiceWorkerGroup(object):
    """ Manages workers for a service - keeps records of 
all the PWP workers running a given service. """
    
    def __init__(self, kernel, serviceName, publishedName):
        """ Initialise a workers store with the name of the service."""
        self.kernel = kernel
        self.serviceName = serviceName
        self.publishedName = publishedName
        self.workers = RoundRobinList()
        self.started = time.time()
        self.__CLOSING = False
        self.__eventHandlerInstance = MethodEventHandler(self._workerLaunchedHandler)
        self.kernel.dispatcher.registerInternal("kernel.workerlaunch", \
                                self.__eventHandlerInstance)
        self.loopTimer = LoopingCall(self._checkHeartBeat)
        self.loopTimer.start(3, False)

    def _workerLaunchedHandler(self, msg, _, key, __):
        """ Receives events on kernel.workerlaunch; if the msg indicates
launch of a worker for the same named service as this instance, but different
start time, indicates a re-start and this group should closedown. """
        if self.__CLOSING:
            return

        if msg['serviceName'] == self.serviceName \
            and msg['publishedName'] == self.publishedName \
            and msg['startTime'] != self.started:
            self.closeAll()
            self.kernel.logger.info("Service Worker Group closing for %s [%f]" \
                                    % (self.publishedName, self.started))
            
    def addWorker(self, worker):
        """ Add a worker to the list."""
        self.workers.append(worker)
        self.kernel.dispatcher.fireInternalEvent("kernel.workerlaunch", 
                                                 serviceName = self.serviceName, 
                                                 publishedName = self.publishedName,
                                                 startTime = self.started)
        
    def getWorkers(self):
        """ Return all workers in this group."""
        if not self.workers:
            # all the workers are gone but we're still listed
            # as supplying this service.... for now just wash over
            raise NoWorkersError("Service no longer available.")
        return self.workers
        
    def getRandomWorker(self):
        """ Return a single worker at random from the pool for the latest
version """
        workers = self.getWorkers() # raises error if no workers
        ix = random.randrange( len(workers) )
        return workers[ix]
    
    def getNextWorker(self):
        """ Return a single worker from the pool for the latest
version (picks in round-robin fashion from pool)."""
        workers = self.getWorkers()
        v = workers.rrnext()
        if v==None:
            raise NoWorkersError("No workers for service!")
        return v

    def removeWorker(self, worker):
        """ Remove the worker from this mapping, calling stop() on it
as we go. Return True if worker was found and removed; False if not"""
        try:
            worker.callRemote('stop')
        except:
            pass

        if worker in self.workers:
            try:
                self.workers.remove(worker)
            except:
                pass
            return True
        else:
            return False
    
    def notifyDeadWorker(self, worker):
        """ Remove this dead worker and trigger its replacement. """
        try:
            if self.removeWorker(worker):
                # replaces only if worker was still in the pool
                self.kernel.startService(self.serviceName, self.publishedName)
            # else there were no occurences removed so this is likely already 
            # being re-stated.
        except NoWorkersError:
            # again; nothing to worry about as the re-start will be underway.
            pass
                
    def _checkHeartBeat(self):
        """ Iterate over all workers, calling check heart beat. """
        try:
            deadWorkers = [p for p in self.workers if not p.checkBeat(threshold=2)]
            for p in deadWorkers:
                self.notifyDeadWorker(p)
        except AttributeError:
            # checkBeat not yet in place...
            self.kernel.logger.debug("Check heart beat skipped... workers not initialised")

    def closeAll(self):
        """ Close down ALL workers. """
        self.__CLOSING = True
        try:
            self.loopTimer.stop()
        except:
            self.kernel.logger.debug("loopTimer.stop() called twice!")
        self.kernel.dispatcher.deregisterInternal(self.__eventHandlerInstance)
        for worker in self.workers:
            worker.callRemote('stop').addErrback(lambda _: None)        
