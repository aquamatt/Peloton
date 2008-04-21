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
from peloton.events import EventDispatcher
from peloton.events import MethodEventHandler
from peloton.utils import crypto
from peloton.utils import getClassFromString
from peloton.utils import locateFile
from peloton.utils import getExternalIPAddress
from peloton.utils.structs import RoundRobinList
from peloton.mapping import ServiceLoader
from peloton.mapping import RoutingTable
from peloton.mapping import ServiceLibrary
from peloton.profile import PelotonProfile
from peloton.exceptions import ConfigurationError
from peloton.exceptions import PluginError
from peloton.exceptions import WorkerError
from peloton.exceptions import NoWorkersError

class PelotonKernel(HandlerBase):
    """ The kernel is the core that starts key services of the 
node, registers with the grid, pulls together all kernel modules
and provides the means via which components find each other. For example, 
it is the kernel that gathers together the event transceiver and the
coreIO interfaces.
"""

    #: List of classes that provide IO adapters for the Peloton node.
    __ADAPTERS__ = ["peloton.adapters.pb.PelotonPBAdapter",
                "peloton.adapters.http.PelotonHTTPAdapter",
                ]

    def __init__(self, options, args, config):
        """ Prepare the kernel."""
        HandlerBase.__init__(self, options, args)
        self.adapters = {}
        self.serviceLibrary = ServiceLibrary()
        self.workerStore = {}
        self.config = config
        self.plugins = {}
        self.profile = PelotonProfile()
        self.dispatcher = EventDispatcher(self)
        
        # used to validate new worker connections
        self.serviceLaunchTokens = {}
        
        # callables are plugin interfaces (pb.Referenceable) that 
        # can be requested by name by clients
        self.callables = {}

        # get path to pwp - it'll be in the same directory
        # as this file. pwp.py starts Peloton workers.
        fspec = __file__.split('/')[:-1]
        fspec.append('pwp.py')
        self.pwp = os.sep.join(fspec)
        if not os.path.isfile(self.pwp):
            raise Exception("Cannot find worker process launcher %s!" % self.pwp)
        
    def start(self):
        """ Start the Twisted event loop. This method returns only when
the server is stopped. Returns an exit code.

The bootstrap routine is as follows:
    1.  Read the domain and grid keys
    2.  Load the profile for this PSC
    3.  Generate this PSCs session keys and our UID
    4.  Start all the network protocol adapters
    5.  Start kernel plugins
    6.  Initialise routing table, schedule grid-joining workflow to 
        start when the reactor starts
    7. Start the reactor
    
The method returns only when the reactor stops.
"""        
        self.logger.info("Using Twisted version %s" % twistedVersion)
        
        # (1) read in the domain and grid key - all PSCs in a domain must have 
        # access to the same key file (or identical copy, of course)
        self.domainCookie, self.domainKey = \
            self._readKeyFile(self.config['domain.keyfile'])
        self.gridCookie, self.gridKey = \
            self._readKeyFile(self.config['grid.keyfile'])

        # (2) Load the PSC profile
        # First try to load from a profile section in the main config
        try:
            self.profile.loadFromConfig(self.config['psc'])
        except ConfigurationError:
            # no profile section.. no big deal
            pass
        
        # PSC configuration in a file
        if self.initOptions.profile:
            self.profile.loadFromFile(self.initOptions.profile)
        
        if not self.profile:
            raise ConfigurationError("There is no profile for the PSC!")
        
        # load and overlay with any profile from file
        if self.initOptions.profile:
            self.profile.loadFromFile(self.initOptions.profile, 
                                      self.initOptions.configdirs)

        # add flags from the command line to any flags that may be
        # in the profile from disk
        if self.profile.has_key('flags'):
            self.profile.flags.extend(self.initOptions.flags)
        else:
            self.profile['flags'] = self.initOptions.flags
            
        # (3) generate session keys
        self.sessionKey = crypto.newKey(512)
        self.publicKey = self.sessionKey.publickey()
        self.guid = str(uuid.uuid1())
        self.profile['guid'] = self.guid
        self.logger.info("Node UUID: %s" % self.profile['guid'])
        
        # (4) hook in the PB adapter and any others listed
        self.logger.info("Adapters list should be in config, not in code!")
        self._startAdapters()
        # the profile address may be different to the bind interface
        # as this should be the address that other nodes can contact
        # us on, ie an external address. So we check to see if the
        # configured interface is 0.0.0.0 or 127.* in which case
        # we use another method to determine our external interface
        if self.config['psc.bind_interface'].startswith('0.0.0.0') or \
            self.config['psc.bind_interface'].startswith('127.'):
            self.profile['ipaddress'] = getExternalIPAddress()
            self.logger.info("Auto-detected external address: %s" % self.profile['ipaddress'])
        else:
            self.profile['ipaddress'] = self.config['psc.bind_interface']
        self.profile['port'] = self.config['psc.bind_port']        
        self.profile['hostname'] = socket.getfqdn()

        # (5) Start any kernel plugins, e.g. message bus, shell and
        #     then instruct the dispatcher to get the external bus
        self._startPlugins()
        self.dispatcher.joinExternalBus()

        # (6) Initialise the routing table and schedule grid-joining 
        #     workflow to happen on reactor start
        #  -- this checks the domain cookie matches ours; quit if not.
        self.serviceLoader = ServiceLoader(self)
        self.routingTable = RoutingTable(self)
        self.domainManager = DomainManager(self)
        reactor.callWhenRunning(self.routingTable.notifyConnect)

        # (7) ready to start!
        reactor.run()
        
        return 0

    def _readKeyFile(self, keyfile):
        """ Read in the named keyfile and return a tuple of cookie and
key."""
        try:
            keyfile = locateFile(keyfile, self.initOptions.configdirs)
            if os.path.isfile(keyfile):
                cookie, key = crypto.loadKeyAndCookieFile(keyfile)
            else:
                raise ConfigurationError("Key file is unreadable, does not exist or is corrupted: %s" % keyfile)
        except Exception, ex:
            raise ConfigurationError("Key file is unreadable, does not exist or is corrupted: %s (%s)" % (keyfile, str(ex)))
        return(cookie, key)

    def hasFlag(self, flag):
        """ Return true if 'flag' was set on the command line. """
        return flag in self.initOptions.flags

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
        pluginConfs = self.config['psc.plugins']
        pluginNames = pluginConfs.keys()
        # iterate over each plugin
        self.logger.info("@todo: add an optional startPos integer to profiles to sort for startup.")
        for plugin in pluginNames:
            self.startPlugin(plugin)
    
    def startPlugin(self, plugin):
        """ Start the plugin named 'plugin'. """
        pconf = self.config['psc.plugins'][plugin]
        # check that has children, including 'class' otherwise this
        # is just some random key in the 'plugins' section of the 
        # config
        if not pconf.has_key('class'):
            return

        if (pconf.has_key('enabled') and \
            pconf['enabled'].upper() == 'TRUE' and \
            plugin not in self.initOptions.disable) \
            or \
            plugin in self.initOptions.enable:
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
            pluginClass = getClassFromString(pconf['class'])
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

    def _startAdapters(self):
        """Prepare all protocol adapters for use. Each adapter
has a start(config, initOptions) method which does initial setup and 
hooks into the reactor. It is passed the entire config stack 
(self.config) and command line options"""
        for adapter in PelotonKernel.__ADAPTERS__:
            cls = getClassFromString(adapter)
            _adapter = cls(self)
            self.adapters[_adapter.name] = _adapter
            _adapter.start(self.config, self.initOptions)
    
    def _stopAdapters(self):
        """ Close down all adapters currently bound. """
        for adapter in self.adapters.values():
            adapter.stop()

    def launchService(self, serviceName):
        """ Initiate the process of launching a service. """
        self.serviceLoader.launchService(serviceName)

    def startService(self, serviceName, version, launchTime, numWorkers=None):
        """ Instruct start of worker processes running service named serviceName. 
The number of workers is determined from the profile but can be overridden with 
numWorkers if set.
"""
        tok = crypto.makeCookie(20)
        profile = self.serviceLibrary.getProfile(serviceName, version, launchTime)
        if numWorkers == None:
            numWorkers = int( profile.getpath('launch.workersperpsc') )
        self.serviceLaunchTokens[tok] = [serviceName, version, launchTime, numWorkers, 0]
        d = deferToThread(self._startWorkerProcess, numWorkers, tok)
        d.addCallback(self._workerStarted, serviceName)
        
    def _startWorkerProcess(self, numWorkers, token):
        """ Run in a thread by startService to spawn the 
worker processes and initialise them. """
        for _ in range(numWorkers):
            pipe= subprocess.Popen(['python', self.pwp, 
                              self.profile['ipaddress'], 
                              str(self.profile['port'])],
                              stdin=subprocess.PIPE).stdin
            pipe.write("%s\n" % token)

    def _workerStarted(self, _, service):
        self.logger.info("Workers spawned for %s" % service)

    def addWorker(self, ref, token):
        """ Store a reference to a worker keyed on tuple of 
(name, version, launchTime). 

Returns the name of the service referenced by this token"""
        try:
            launchRecord = self.serviceLaunchTokens[token]
        except KeyError:
            raise WorkerError("Invalid start request.")

        launchRecord[-1]+=1
        serviceName, version, launchTime = launchRecord[:3]
        if not self.workerStore.has_key(serviceName):
            self.workerStore[serviceName] = ServiceProvider(self, serviceName)
        self.workerStore[serviceName].addProvider(ref, version, launchTime)
        if launchRecord[-1] == launchRecord[-2]:
            del self.serviceLaunchTokens[token]
        return serviceName
    
    def removeWorker(self, ref):
        """ Remove the worker referenced from the worker store. """
        self.logger.debug("Worker being removed but NOT stopped, kernel.py removeWorker")
        for k,v in self.workerStore:
            if v == ref:
                del(self.workerStore[k])
                break

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
            reactor.callLater(0.01,self.kernel.closedown)
        
        elif command['command'] == 'NOOP':
            self.kernel.logger.debug("NOOP Called on domain_control")
            
    def sendCommand(self, command, *args):
        """ Send a command in the manner described in respond_commandRequest. """
        now = time.time()
        msg = {'command':command, 
               'args':args,
               'cookie':crypto.makeCookie(20),
               'time':now,
               'issuer':self.kernel.guid }
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
        
class ServiceProvider(object):
    """ Manages providers for a service - keeps records of what
versions are available and the PSC 'providers' running the service. """
    
    def __init__(self, kernel, name):
        """ Initialise a providers store with the name of the service."""
        self.kernel = kernel
        self.name = name
        self.versions = {}
        self.allProviders = []
        LoopingCall(self._checkHeartBeat).start(3, False)
            
    def addProvider(self, provider, version, launchTime, closeOldProviders=True):
        """ Add a provider. By default and unless closeOldProviders is set False,
if there are providers for an older launchTime they will be closed down once
a new launchTime provider for that version is added."""
        if not self.versions.has_key(version):
            self.versions[version]={}
        vrec = self.versions[version]
        if not vrec.has_key(launchTime):
            self.versions[version][launchTime] = RoundRobinList()
        vrec[launchTime].append(provider)
        self.allProviders.append(provider)
        
        # close down all providers with older launchTime stamps
        if closeOldProviders:
            oldLaunchTimes = [i for i in vrec.keys() if i!=launchTime]
            for olt in oldLaunchTimes:
                for provider in vrec[olt]:
                    try:
                        try:
                            self.allProviders.remove(provider)
                        except:
                            pass
                        provider.callRemote('stop').addBoth(self._removeClosed, version, olt, provider)
                    except pb.DeadReferenceError:
                        pass
                
    def _removeClosed(self, _, version, launchTime, ref):
        try:
            if ref in self.versions[version][launchTime]:
                self.versions[version][launchTime].remove(ref)
                try:
                    self.allProviders.remove(ref)
                except:
                    pass
                if not self.versions[version][launchTime]:
                    del( self.versions[version][launchTime] )
        except KeyError:
            # launchTime no longer there
            pass

    def getProviders(self):
        """ Return all providers of the latest version."""
        versions = self.versions.keys()
        versions.sort()
        try:
            vrecs = self.versions[versions[-1]]
        except IndexError:
            # all the providers are gone but we're still listed
            # as supplying this service.... for now just wash over
            raise NoWorkersError("Service no longer available.")
        lts = vrecs.keys()
        lts.sort()
       
        return vrecs[lts[-1]]
        
    def getRandomProvider(self):
        """ Return a single provider at random from the pool for the latest
version """
        providers = self.getProviders()
        np = len(providers)
        if np == 0:
            raise NoWorkersError("No workers for service!")
        ix = random.randrange(np)
        return providers[ix]
    
    def getNextProvider(self):
        """ Return a single provider from the pool for the latest
version (picks in round-robin fashion from pool)."""
        providers = self.getProviders()
        v = providers.rrnext()
        if v==None:
            raise NoWorkersError("No workers for service!")
        return v

    def removeProvider(self, provider):
        """ Remove the provider from this mapping, calling stop() on it
as we go. Returns the number of occurences removed."""
        emptyVersions=[]
        n = 0
        for v, lts in self.versions.items():
            keysToRemove = []
            for k, p in lts.items():
                if provider in p:
                    p.remove(provider)
                    n+=1
                if not p:
                    keysToRemove.append(k)
            for k in keysToRemove:
                del(lts[k])
            if not lts:
                emptyVersions.append(v)
        for k in emptyVersions:
            del(self.versions[k])
        try:
            provider.callRemote('stop')
        except pb.DeadReferenceError:
            pass

        try:
            self.allProviders.remove(provider)
        except:
            pass

        return n

    def getLatestVersion(self):
        """ Return a (version, launchTime) tuple. """
        vnums = self.versions.keys()
        if not vnums:
            raise NoWorkersError("No workers currently for %s" % self.name)
        vnums.sort()
        vrec = self.versions[vnums[-1]]
        lts = vrec.keys()
        lts.sort()
        return vnums[-1], lts[-1]
        
    def notifyDeadProvider(self, provider):
        """ Remove this dead provider and trigger its replacement. """
        try:
            version, launchTime = self.getLatestVersion()
            n = self.removeProvider(provider)
            if n:
                self.kernel.startService(self.name, version, launchTime, 1)
            # else there were no occurences removed so this is likely already 
            # being re-stated.
        except NoWorkersError:
            # again; nothing to worry about as the re-start will be underway.
            pass
                
    def _checkHeartBeat(self):
        """ Iterate over all providers, calling check heart beat. """
        deadProviders = [p for p in self.allProviders if not p.checkBeat()]
        for p in deadProviders:
            self.notifyDeadProvider(p)
                
    def setCurrent(self, version):
        """ Re-set the 'current' version. """
        pass

    def closeAll(self):
        """ Close down ALL providers. """
        self.kernel.routingTable.localProxy.stop()
        for version in self.versions.values():
            # version is dict keyed on launchTime
            for providerList in version.values():
                # providerList is list of providers
                for p in providerList:
                    try:
                        self.allProviders.remove(p)
                    except:
                        pass
                    p.callRemote('stop').addErrback(lambda _: None)
                    
    
        