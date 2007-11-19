# Copyright 2007 Matthew Pontefract
# See LICENSE for details

""" Useful structures and classes to replace or supplement
core Python structures.
"""
import types

class ReadOnlyDict(dict):
    def __init__(self, *args, **kargs):
        dict.__init__(self, *args, **kargs)
        self.__REWRITEABLE = []
        
    def setRewriteable(self, keys=[]):
        """ Make names in the 'keys' list re-bindable in this 
dictionary."""
        if type(keys) == types.StringType:
            self.__REWRITEABLE.append(keys)
        elif type(keys) == types.ListType:
            self.__REWRITEABLE.extend(keys)
    
    def __setitem__(self, key, value):
        if dict.has_key(self, key) and key not in self.__REWRITEABLE:
            raise KeyError("This key is already assigned and may not be modified")
        dict.__setitem__(self, key, value)