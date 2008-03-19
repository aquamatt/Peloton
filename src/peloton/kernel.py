# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
from peloton.utils import getClassFromString

# ensure threading is OK with twisted
from twisted.python import threadable
threadable.init()

from twisted.python.reflect import getClass
from peloton.utils import getClassFromString

import ezPyCrypto
import logging
import os
import uuid

from twisted.internet import reactor
from twisted.spread import pb
from types import DictType
from peloton.base import HandlerBase
from peloton.persist.memcache import PelotonMemcache
from peloton.utils import getClassFromString
from peloton.utils import chop
from peloton.utils import locateFile
from peloton.utils.config import PelotonConfig
from peloton.mapping import ServiceLoader, ServiceLibrary
from peloton.profile import PelotonProfile
from peloton.exceptions import ConfigurationError
from peloton.exceptions import PluginError

class PelotonKernel(HandlerBase):
    """ The kernel is the core that starts key services of the 
node, registers with the grid, pulls together all kernel modules
and provides the means via which components find each other. For example, 
it is the kernel that gathers together the event transceiver and the
coreIO interfaces.
"""

    #: List of classes that provide IO adapters for the Peloton node.
    __ADAPTERS__ = ["peloton.adapters.pb.PelotonPBAdapter",
    #            "peloton.adapters.soap.PelotonSoapAdapter",
    #            "peloton.adapters.xmlrpc.PelotonXMLRPCAdapter",
    #            "peloton.adapters.web.PelotonHTTPAdapter",
                ]

    def __init__(self, generatorInterface, options, args, config):
        """ Prepare the kernel. The generatorInterface is a callable via
which the kernel can request a worker to be started for a given service."""
        HandlerBase.__init__(self, options, args)
        self.generatorInterface = generatorInterface
        self.adapters = {}
        self.logger = logging.getLogger()
        self.config = config
        self.plugins = {}
        self.profile = PelotonProfile()
        self.serviceLoader = ServiceLoader(self)
        self.serviceLibrary = ServiceLibrary(self)
        
        # callables are plugin interfaces (pb.Referenceable) that 
        # can be requested by name by clients
        self.callables = {}
        
    def start(self):
        """ Start the Twisted event loop. This method returns only when
the server is stopped. Returns an exit code.

The bootstrap routine is as follows:
    1.  Read the domain and grid keys
    2.  Load the profile for this PSC
    3.  Generate this PSCs session keys and our UID
    4.  Connect to memcache
    5.  Connect to the persistence back-end
    6.  Start all the network protocol adapters
    7.  Inform the worker generator as to the port on which the RPC
        adapter has started.
    8.  Schedule grid-joining workflow to start when the reactor starts
    9.  Start kernel plugins
    10. Start the reactor
    
The method ends only when the reactor stops.

@todo: Workout the kernel plugin API and create a sample plugin
"""        
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
            
        # (3) generate session keys
        self.sessionKey = ezPyCrypto.key(512)
        self.publicKey = self.sessionKey.exportKey()
        self.profile['guid'] = str(uuid.uuid1())
        self.logger.info("Node UUID: %s" % self.profile['guid'])
        
        # (4) hook into cacheing back-end
        self.memcache = PelotonMemcache.getInstance(
                          self.config['domain.memcacheHosts'])

        # (5) hook into persistence back-ends
        
        # (6) hook in the PB adapter and any others listed
        self.logger.info("Adapters list should be in config, not in code!")
        self._startAdapters()
        
        # (7) Write to the generatorInterface to pass host:port of our 
        # twisted RPC interface
        self.generatorInterface.initGenerator(self.config['psc.bind'])

        # (8)schedule grid-joining workflow to happen on reactor start
        #  -- this checks the domain cookie matches ours; quit if not.

        # (9) Start any kernel plugins, e.g. scheduler, shell 
        self._startPlugins()

        # (10) ready to start!
        reactor.run()
        
        return 0

    def _readKeyFile(self, keyfile):
        """ Read in the named keyfile and return a tuple of cookie and
key."""
        try:
            keyfile = locateFile(keyfile, self.initOptions.configdirs)
            if os.path.isfile(keyfile):
                o = open(keyfile, 'rt')
                cookie = chop(o.readline())
                aKey = ""
                while True:
                    aKey = o.readline() 
                    if aKey.startswith("<StartPycryptoKey>"):
                        break
                while True:
                    l = o.readline()
                    aKey = aKey + l
                    if l.startswith("<EndPycryptoKey>"):
                        break
                key =  ezPyCrypto.key(keyobj=aKey)
                o.close()
            else:
                raise ConfigurationError("Domain key file is unreadable, does not exist or is corrupted: %s" % keyfile)
        except:
            raise ConfigurationError("Domain key file is unreadable or does not exist: %s" % keyfile)

        return(cookie, key)

    def closedown(self):
        """Closedown in an orderly fashion."""
        # Closedown all worker nodes
        # tidy up kernel
        
        self.logger.info("Stopping adapters")
        self._stopAdapters()
        self.logger.info("Stopping plugins")
        self._stopPlugins()
        self.logger.info("Stopping generator")
        self.generatorInterface.stop()
        
        # stop the reactor
        reactor.stop()

    def _startPlugins(self):
        pluginConfs = self.config['psc.plugins']
        pluginNames = pluginConfs.keys()
        # iterate over each plugin
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
            plogger.setLevel(getattr(logging,self.initOptions.loglevel))
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
        for p in self.plugins.keys():
            self.stopPlugin(p)

    def _startAdapters(self):
        """Prepare all protocol adapters for use. Each adapter
has a start(config, initOptions) method which does initial setup and 
hooks into the reactor. It is passed the entire config stack 
(self.config) and command line options"""
        for adapter in PelotonKernel.__ADAPTERS__:
            cls = getClassFromString(adapter)
            _adapter = cls(self)
            self.adapters[adapter] = _adapter
            _adapter.start(self.config, self.initOptions)
    
    def _stopAdapters(self):
        """ Close down all adapters currently bound. """
        for adapter in self.adapters.values():
            adapter.stop()

    def launchService(self, serviceName):
        """ Initiate the process of launching a service. """
        self.serviceLoader.launchService(serviceName)

    def getCallable(self, name):
        """ Return the callable as named"""
        if not self.callables.has_key(name):
            raise PluginError("No plugin interface known by name %s" % name)
        return self.callables[name]
    
    def registerCallable(self, name, iface):
        """ Register a pb.Referenceable interface by name so that
it can be obtained by remote clients. This is the mechanism by which
kernel plugins may publish callable interfaces. """
        if isinstance(pb.Referenceable, iface):
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
        