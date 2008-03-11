# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details

import ezPyCrypto
import logging
import os

from twisted.internet import reactor
from peloton.base import HandlerBase
from peloton.persist.memcache import PelotonMemcache
from peloton.utils import getClassFromString
from peloton.utils import chop
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

    def __init__(self, generatorInterface, options, args):
        """ Prepare the kernel. The generatorInterface is a callable via
which the kernel can request a worker to be started for a given service."""
        HandlerBase.__init__(self, options, args)
        self.generatorInterface = generatorInterface
        self.adapters = {}
        self.logger = logging.getLogger()
    
    def start(self):
        """ Start the Twisted event loop. This method returns only when
the server is stopped. Returns an exit code.

The bootstrap routine is as follows:
    1. Load configuration from configuration path and also read
       the domain key
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
        # (1) load the configuration
        self.configuration = PelotonConfig(self.initOptions)
        
        # read in the domain key - all PSCs in a domain must have access
        # to this same key file (or identical copy, of course)
        if os.path.exists(self.initOptions.domainkey) and \
            os.path.isfile(self.initOptions.domainkey):
            o = open(self.initOptions.domainkey, 'rt')
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
            raise Exception("Domain key file is unreadable, does not exist or is corrupted: %s" % self.initOptions.domainkey)
        
        # (2) generate session keys
        self.sessionKey = ezPyCrypto.key(512)
        self.publicKey = self.sessionKey.exportKey()

        # (3) hook into cacheing back-end
        self.memcache = PelotonMemcache.getInstance(
                          self.configuration['external']['memcacheHosts'])

        # (4) hook into persistence back-ends
        
        # (5) hook into message bus
        
        # (6) hook in the PB adapter and any others listed
        self._startAdapters()
        
        # (7) Write to the generatorInterface to pass host:port of our 
        # twisted RPC interface
        self.generatorInterface.initGenerator(self.configuration['network']['bind'])

        # (8)schedule grid-joining workflow to happen on reactor start
        #  -- this checks the domain cookie matches ours; quit if not.

        # (9) Start any kernel plugins, e.g. scheduler

        # (10) ready to start!
        ##### REMOVE THESE LINEs ####
        self.logger.warn("DEBUG LINE CAUSING SHUTDOWN IN 5 SECONDS ACTIVE!")
        reactor.callLater(5, self.closedown)
        ##### END REMOVE ############
        reactor.run()
        
        return 0

    def closedown(self):
        """Closedown in an orderly fashion."""
        # Closedown all worker nodes
        # tidy up kernel
        
        self._stopAdapters()
        self.generatorInterface.stop()
        
        # stop the reactor
        reactor.stop()

    def _startAdapters(self):
        """Prepare all protocol adapters for use. Each adapter
has a start(config, initOptions) method which does initial setup and 
hooks into the reactor. It is passed the entire config stack 
(self.configuration) and command line options"""
        for adapter in PelotonKernel.__ADAPTERS__:
            cls = getClassFromString(adapter)
            _adapter = cls()
            self.adapters[adapter] = _adapter
            _adapter.start(self.configuration, self.initOptions)
    
    def _stopAdapters(self):
        """ Close down all adapters currently bound. """
        for adapter in self.adapters.values():
            adapter.stop()
