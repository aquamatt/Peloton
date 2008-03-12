# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
from peloton.utils import getClassFromString
from twisted.python.reflect import getClass
from peloton.utils import getClassFromString

import ezPyCrypto
import logging
import os

from twisted.internet import reactor
from types import DictType
from peloton.base import HandlerBase
from peloton.persist.memcache import PelotonMemcache
from peloton.utils import getClassFromString
from peloton.utils import chop
from peloton.utils import locateFile
from peloton.utils.config import PelotonConfig

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
    
    def start(self):
        """ Start the Twisted event loop. This method returns only when
the server is stopped. Returns an exit code.

The bootstrap routine is as follows:
    1. Read the domain and grid keys
    2. Generate this PSCs session keys
    3. Connect to memcache
    4. Connect to the persistence back-end
    5. Connect to the message bus
    6. Start all the network protocol adapters
    7. Inform the worker generator as to the port on which the RPC
       adapter has started.
    8. Schedule grid-joining workflow to start when the reactor starts
    9. Start kernel plugins
    10. Start the reactor
    
The method ends only when the reactor stops.

@todo: Workout the kernel plugin API and create a sample plugin
"""        
        # (1) read in the domain key - all PSCs in a domain must have access
        # to this same key file (or identical copy, of course)
        keyfile = self.config['domain.keyfile']
        try:
            keyfile = locateFile(keyfile, self.initOptions.configdirs)
            if os.path.isfile(keyfile):
                o = open(keyfile, 'rt')
                self.domainCookie = chop(o.readline())
                aDomainKey = ""
                while True:
                    aDomainKey = o.readline() 
                    if aDomainKey.startswith("<StartPycryptoKey>"):
                        break
                while True:
                    l = o.readline()
                    aDomainKey = aDomainKey + l
                    if l.startswith("<EndPycryptoKey>"):
                        break
                self.domainKey =  ezPyCrypto.key(keyobj=aDomainKey)
                o.close()
            else:
                raise Exception("Domain key file is unreadable, does not exist or is corrupted: %s" % keyfile)
        except:
            raise Exception("Domain key file is unreadable or does not exist: %s" % keyfile)
        
        # (2) generate session keys
        self.sessionKey = ezPyCrypto.key(512)
        self.publicKey = self.sessionKey.exportKey()

        # (3) hook into cacheing back-end
        self.memcache = PelotonMemcache.getInstance(
                          self.config['domain.memcacheHosts'])

        # (4) hook into persistence back-ends
        
        # (5) hook into message bus
        
        # (6) hook in the PB adapter and any others listed
        self._startAdapters()
        
        # (7) Write to the generatorInterface to pass host:port of our 
        # twisted RPC interface
        self.generatorInterface.initGenerator(self.config['psc.bind'])

        # (8)schedule grid-joining workflow to happen on reactor start
        #  -- this checks the domain cookie matches ours; quit if not.

        # (9) Start any kernel plugins, e.g. scheduler, manhole
        self._startPlugins()

        # (10) ready to start!
        reactor.run()
        
        return 0

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

        if pconf.has_key('enabled') and \
            pconf['enabled'].upper() == 'TRUE':
            self.logger.info("Starting plugin: %s" % plugin)
        else:
            self.logger.info("Plugin %s disabled" % plugin)
            
        if self.plugins.has_key(plugin):
            if not self.plugins[plugin].started:
                self.plugins[plugin].start()
        else:
            pluginClass = getClassFromString(pconf['class'])
            plogger = logging.getLogger(plugin)
            plogger.setLevel(self.initOptions.loglevel)
            pluginInstance = pluginClass(self, pconf, plogger)
            pluginInstance.initialise()
            pluginInstance.start()
            self.plugins[plugin] = pluginInstance

    def stopPlugin(self, plugin):
        if self.plugins.has_key(plugin):
            if self.plugins[plugin].started:
                self.logger.info("Stopping plugin: %s"%plugin)
                self.plugins[plugin].stop()
            else:
                self.logger.info("Plugin not started: %s" % plugin)
        else:
            raise Exception("Invalid plugin: %s" % plugin)
            
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
            _adapter = cls()
            self.adapters[adapter] = _adapter
            _adapter.start(self.config, self.initOptions)
    
    def _stopAdapters(self):
        """ Close down all adapters currently bound. """
        for adapter in self.adapters.values():
            adapter.stop()
