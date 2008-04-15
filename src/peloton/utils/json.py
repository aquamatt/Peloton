# $Id: json.py 122 2008-04-11 08:22:28Z mp $
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
""" Provides utility classes for reading and writing JSON formatted
objects. 
"""

class UnSerializableError(Exception): pass
import types

class JSONSerializer(object):
    """ Takes python object and returns a JSON string. """
    def __init__(self):
        self.TR_FUNCS = {types.ListType: self._tr_list,
                    types.TupleType: self._tr_list,
                    types.DictType: self._tr_dict,
                    types.StringType: self._tr_string,
                    types.UnicodeType: self._tr_unicode,
                    types.FloatType: self._tr_float,
                    types.IntType: self._tr_int,
                    types.LongType: self._tr_int,
                    types.BooleanType: self._tr_boolean,
                    types.NoneType: self._tr_none}
        
    def write(self, obj):
        """ Takes object obj and translates into a JSON string. If
obj or a component of obj is not serializable, UnSerializableError
is raised. """
        try:
            return self.TR_FUNCS[type(obj)](obj)
        except KeyError:
            raise UnSerializableError("Cannot serialize %s" % str(obj))
        
    def _tr_list(self, o):
        tokens =[]
        for i in o:
            tokens.append(self.TR_FUNCS[type(i)](i))

        return u"[" + u", ".join(tokens) + u"]"
    
    def _tr_dict(self, o):
        tokens=[]
        for k,v in o.items():
            key = self.TR_FUNCS[type(k)](k)
            val = self.TR_FUNCS[type(v)](v)
            tokens.append("%s: %s" % (key, val))
        return u"{" + u", ".join(tokens) + u"}"
    
    def _tr_string(self, o):
        substitutions = [('\\', r'\\'),
                         ('"', r'\"'),
                         ('\r', r'\r'),
                         ('\n', r'\n'),
                         ('\t', r'\t'),
                         ('\f', r'\f'),
                         ('\b', r'\b'),
                         ]
        for s, r in substitutions:
            o = o.replace(s, r)
        return u'"%s"' % o
    
    def _tr_unicode(self, o):
        return self._tr_string(o)
    
    def _tr_float(self, o):
        return u"%f" % o
    
    def _tr_int(self, o):
        return u"%d" % o
        
    def _tr_boolean(self, o):
        if o:
            return u"true"
        else:
            return u"false"
    
    def _tr_none(self, o):
        return u"null"