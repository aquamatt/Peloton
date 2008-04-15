# $Id: backpack.py 83 2008-03-21 00:20:56Z mp $
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
"""The BackPack plugin consists of a pair of kernel modules
that provide the two ends of a distributed persistent storage
mechanism.

The back-end storage system is pluggable but will initially use
ZODB. Each ZODB is only for the node to which it connects; no ZEO 
is used here. 

Instead, a master BackPack node has its own store and manages the 
ZODB database. There is optionaly a slave node on a different 
host.

There may optionaly be a number of level 1 (L1) caches connected to 
the master. These cache reads and pass through writes. A set of L1 
caches can lighten the load on the master immensley.

Clients run the same code as the L1 cache but do not announce themselves
publicly. They read/write either to a randomly chosen L1 cache or 
direct to the master.

All writes are reflected to the slave node and this node will become
autoritative in the event of a failure of the master.

With this scheme it is hoped to have a simple yet robust system capable
of reasonable scaling provided the system is predominantly read-heavy.

Acceptable write-ratios have to be determined through benchmarking. In
the event of issues a more sophisticated system where the namespace
is manually or dynamicaly chunked (as in a DHT) would be required.
"""
from peloton.plugins import PelotonPlugin
from peloton.utils import getClassFromString
from twisted.spread import pb

class BackPackPlugin(PelotonPlugin):
    """ The Peloton plugin interface to the BackPack system through which
requests are made and nodes managed."""
    def initialise(self):
        # get class for persistence and initialise
        self.backEnd = \
            getClassFromString(self.config['storageBackend'])(self.config)
        
        # create the callable
        self.iface = BackPackIO(self)
    
    def start(self):
        self.backEnd.start()
        self.kernel.registerCallable('backpack', self.iface)
    
    def stop(self):
        self.backEnd.stop()
        self.kernel.deregisterCallable('backpack')
        
class BackPackIO(pb.Referenceable):
    """ Referenceable used by nodes to communicate with each other. Used
both by nodes that are Storage Nodes and nodes that are just clients. The
clients persist their cache in the same way that a server persists the master 
list for its domain. """
    def __init__(self, backpack):
        self.backpack = backpack
        
    def remote_get(self, key):
        pass
    
    def remote_set(self, key, value):
        pass
    
    def remote_getmulti(self, key):
        pass
    
    def remote_del(self, key):
        pass
    
    def remote_invalidate(self, key):
        pass

class BackPackPersistentStore(object):
    """ Base class for all persistence back-ends for the BackPack system. """
    def __init__(self, config):
        self.config = config
    
    def start(self):
        raise NotImplementedError()
    
    def stop(self):
        raise NotImplementedError()

class BackPackZODB(BackPackPersistentStore):
    def __init__(self, config):
        BackPackPersistentStore.__init__(self, config)

