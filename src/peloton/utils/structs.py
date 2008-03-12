# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details


""" Useful structures and classes to replace or supplement
core Python structures.
"""
import types
from optparse import OptionParser

class ReadOnlyDict(dict):
    """ A dictionary that has entries that may not be
overwritten once assigned UNLESS the key has been explicitly
defined as re-writeable by adding it to the rewritable list
with setRewriteable. """
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
        

class FilteredOptions(object):
    """ Takes options from OptionParser and provides a similar access
interface but one which performs on-the-fly translation of values.

Values to substitute are written as $NAME where NAME is one of:
    
    - the uppercase version of a key in the options dictionary
    - the uppercase version of a key in the optional list of values
      supplied to the constructor as the 'data' argument

Substitutions supplied in the data argument override those in the command
line so this is not a means to add defaults - they should be set with the
add_option method.
      
As with options returned by OptionParser, you reference an option as::

    options.<key>
"""
    def __init__(self, options, data={}):
        self.substitutions = {}
        self.options = options
        self.data = data

        for k,v in self.options.__dict__.items():
            if type(v) == types.StringType:
                self.substitutions[k.upper()] = v
        for k,v in self.data.items():
            if type(v) == types.StringType:
                self.substitutions[k.upper()] = v
            else:
                raise TypeError("Can only provide strings as substitutions.")
            
        self.substKeys = self.substitutions.keys()
        
    def __getattr__(self, attr):
        """ First check to see if the attribute is in the override
list so that overides always get returned. If not, get from the underlying
options then apply substitutions """
        if self.data.has_key(attr):
            return self.__substitute__(self.data[attr])
        
        v = getattr(self.options, attr)
        return self.__substitute__(v)
    
    def __substitute__(self, v):
        """ Substitute all $<KEY> values in v for which we have a KEY"""
        if type(v) == types.StringType:
            for k in self.substKeys:
                v = v.replace('$%s'%k, self.substitutions[k])
        return v
    
    def __str__(self):
        return "Options: %s\nOveride: %s " % (str(self.options), str(self.data) )
        
    def filterList(self, l):
        """ Helper utility, this method will take a list of
values and apply the substitution to all values in it. """
        return [self.__substitute__(v) for v in l]

class FilteredOptionParser(OptionParser):
    def __init__(self, *args, **kargs):
        OptionParser.__init__(self, *args, **kargs)
        self.substitutions = {}
        
    def setSubstitutions(self, **kargs):
        self.substitutions = kargs
        
    def parse_args(self, *args, **kargs):
        opts, argList = OptionParser.parse_args(self, *args, **kargs)
        fo = FilteredOptions(opts, self.substitutions)
        fa = fo.filterList(argList)
        return (fo,fa)
