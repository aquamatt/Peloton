# $Id$
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
""" Some trivial classes for testing to serialize structures out
to different forms of XML. """
import types
from peloton.utils.json import JSONSerializer

class XMLLanguageSerializer(JSONSerializer):
    """ Translates into similarly structure XML or HTML given
tags at init time. Simple extension of the JSON code"""
    def __init__(self, header, footer, listStart, listEnd, listItem, dictStart, dictEnd, dictItem, dataItemStart, dataItemEnd):
        JSONSerializer.__init__(self)
        self.header = header
        self.footer = footer
        self.listStart = listStart
        self.listEnd = listEnd
        self.listItem = listItem
        self.dictStart = dictStart
        self.dictEnd = dictEnd
        self.dictItem = dictItem
        self.dataItemStart = dataItemStart
        self.dataItemEnd = dataItemEnd
    
    def write(self, obj):
        try:
            s = self._format(obj)
            return "%s\n%s\n%s" % (self.header, s, self.footer)
        except KeyError, ke:
            return "Cannot serialize %s with type %s" \
                            % (str(obj), str(type(obj)))

#            raise Exception("Cannot serialize %s with type %s" \
#                            % (str(obj), str(type(obj))))

    def _format(self, obj, solo=True):
        """ Takes object obj and translates into a JSON string. If
obj or a component of obj is not serializable, Exception
is raised. If solo==True the item is surrounded in dataItemstart and 
dataItemEnd tags."""
        s = self.TR_FUNCS[type(obj)](obj)
        if solo and type(obj) not in \
            [types.ListType, types.TupleType, types.DictType]:
            return "%s%s%s" % (self.dataItemStart, s, self.dataItemEnd)
        else:
            return s
        
    def _tr_list(self, o):
        tokens =[]
        for i in o:
            tokens.append(self.listItem % \
                    {'value': self._format(i, False)})

        return "%s\n%s\n%s" % (self.listStart, "\n".join(tokens), self.listEnd)
        
    def _tr_dict(self, o):
        tokens=[]
        for k,v in o.items():
            key = self._format(k, False)
            val = self._format(v, False)
            tokens.append(self.dictItem % \
                    {'key': key, 'value': val})
        return "%s\n%s\n%s" % (self.dictStart, "\n".join(tokens), self.dictEnd)
    
#    def _tr_string(self, o):
#        substitutions = [('\\', r'\\'),
#                         ('"', r'\"'),
#                         ('\r', r'\r'),
#                         ('\n', r'\n'),
#                         ('\t', r'\t'),
#                         ('\f', r'\f'),
#                         ('\b', r'\b'),
#                         ]
#        for s, r in substitutions:
#            o = o.replace(s, r)
#        return '"%s"' % o
#    
#    def _tr_unicode(self, o):
#        return self._tr_string(o)
#    
#    def _tr_float(self, o):
#        return "%f" % o
#    
#    def _tr_int(self, o):
#        return "%d" % o
#        
#    def _tr_boolean(self, o):
#        if o:
#            return "true"
#        else:
#            return "false"
#    
#    def _tr_none(self, o):
#        return "null"    
