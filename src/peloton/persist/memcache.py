# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details

""" Memcache adapter for Peloton livecache 

DEPRECATED

CACHEING SUPPORT MOVED TO KERNEL PLUGIN AND NO LONGER A 
MEMCACHE CLIENT.
"""
from peloton.persist.livecache import AbstractPelotonCache
import peloton.persist.MemcachePool as MemcachePool
import logging

class PelotonMemcache(AbstractPelotonCache):
    """ Interface to memcache, the distributed cache used by many
high volume websites. Memcache is used primarily for storing the 
return values of service methods so that those which change rarely
need not constantly be re-computed. """

    __INSTANCE__ = None
    @staticmethod
    def getInstance( hosts):
        """ Return the singleton instance of this class """
        if PelotonMemcache.__INSTANCE__ == None:
            PelotonMemcache.__INSTANCE__ = PelotonMemcache(hosts)
        return PelotonMemcache.__INSTANCE__
    
    def __init__(self, hosts):
        """ Initialise the memcache connector. Hosts is a list
of available hosts running a memcache daemon."""
        try:
            self.logger = logging.getLogger()
            MemcachePool.init(hosts)
            MemcachePool.getMC().getConnection()
            self.logger.info("Memcache adapter initialised")
        except:
            self.logger.exception("Failed to connect memcache adapter")
            
    def set(self, key, value, ttl=600):
        """Set key to value with a time to live of ttl seconds (default 600, 10 minutes). 
Setting ttl=0 is not permitted as this would ensure the item never expired 
and thus would persist in the mesh until memcache were bumped. As a result, ttl
of zero results in an exception being raised."""
        if ttl == 0:
            raise ValueError("Cannot set TTL=0!")
        MemcachePool.getMC().set(str(key), value, ttl)
    
    def get(self, key):
        """Retrieve value for key. If the key has expired or does not exist, None is
returned."""
        return MemcachePool.getMC().get(str(key))
    
    def getMulti(self, keys):
        """Get multiple keys, returning only those found and valid as a dictionary"""
        return  MemcachePool.getMC().get_multi(keys)
                
    def delete(self, key):
        """ Remove the key from memcache if it is currently set by replacing
the key with a value None with a TTL of 1. This ensures it will be properly 
purged in 1 second, but until then it returns None anyway which is logicaly
equivalent to it not being set in the semantics of this class.

TODO: TEST THIS - THINK SETTING NONE IS NOT POSSIBLE AS ONLY STRINGS ACCEPTED."""
        MemcachePool.getMC().set(str(key), None, 1)