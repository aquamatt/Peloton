# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
""" AbstractPelotonCache is the base class for all cache adapters """

class AbstractPelotonCache(object):
    """ Abstract base class for all cache adapters, e.g.
memcache adapter. """
    def set(self, key, value, ttl):
        """ Set a value with specified key and time to live. """
        raise NotImplementedError()
    
    def get(self, key):
        """ Return a value from the cache with the specified key. """
        raise NotImplementedError()
    
    def getmulti(self, keys):
        """ Return a number of values in a dictionary (only those available); 
keys supplied as a list. """
        raise NotImplementedError()
    
    def delete(self, key):
        """Remove a key from the cache, if the back-end supports this."""
        raise NotImplementedError()
    
    def __getitem__(self, key):
        """ Provide handy access to data through standard notation. """
        return self.get(key)
    
    def __setitem__(self, key, value):
        """ Shortcut to setting values but default 600 second ttl
may not be to everyone's taste. This may not be a great idea. """
        self.set(key, value, 600)
    
    def __delitem(self, key):    
        """ Delete the key if possible. """
        self.delete(key)