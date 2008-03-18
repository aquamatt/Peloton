# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
"""The BackPack plugin consists of a pair of kernel modules
that provide the two ends of a distributed persistent storage
mechanism.

The back-end storage system is pluggable but will initially use
ZODB. Each ZODB is only for the node to which it connects; no ZEO 
is used here. Instead, a group of BackPack nodes each have their own
store and manage their own region of the DHT namespace. There is only
one BackPack storage node per physical host.

Clients, i.e. any Peloton node not providing BackPack services, make a request
of any BackPack node for keys. They clients cache all results and, subsequently,
if a change is made to a key an invalidation message is propagated to the 
clients. 

When a write is made the following steps occur:

  - a hash of the key is computed
  - the 'difference' between key hash and all BackPack node hashes is computed
  - the node for which there was the smallest difference is selected to store
    this key
  - the node stores/updates the key and issues invalidation messages to all
    interested parties.

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

