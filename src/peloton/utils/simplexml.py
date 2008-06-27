# $Id: simplexml.py 123 2008-04-11 10:17:34Z mp $
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
""" Some trivial classes for testing to serialize structures out
to different forms of XML. """
import types

class XMLLanguageSerializer(object):
    """ Translates into similarly structured XML or HTML given
tags at init time."""
    def __init__(self, header, footer, listStart, listEnd, 
                 listItem, dictStart, dictEnd, dictItem, 
                 dataItemStart, dataItemEnd):

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
    
    def _tr_string(self, o):
        substitutions = [('/', r'\/'),
                         ('\\', r'\\'),
                         ('"', r'\"'),
                         ('\b', r'\b'),
                         ('\f', r'\f'),
                         ('\n', r'\n'),
                         ('\r', r'\r'),
                         ('\t', r'\t'),
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

class XMLFormatter(XMLLanguageSerializer):
    """ Noddy serialiser takes Python struct and makes XML. 
Returns tupple of (content-type, value)"""
    def __init__(self):
        XMLLanguageSerializer.__init__(self,
                                     '<?xml version="1.0"?>\n<result>',
                                     "</result>", 
                                     "<list>", 
                                     "</list>", 
                                     "<item>%(value)s</item>", 
                                     "<dict>", 
                                     "</dict>", 
                                     "<item id=%(key)s>%(value)s</item>",
                                     "<data>",
                                     "</data>")
        
    def format(self, v):
        s = XMLLanguageSerializer.write(self, v)
        return s
    
class HTMLFormatter(XMLLanguageSerializer):
    """ Noddy serialiser takes Python struct and makes HTML. 
Returns tupple of (content-type, value)"""
    def __init__(self):
        header = """<html>
        <head>
            <title>Peloton result</title>
        </head>
        <style>
            body {
                font-family: verdana,arial,sans-serif;
                font-size:80%;
                color: #444;
                background-color:#668;
            }
            #main {
                width: 80%;
                border: 2px solid #444;
                padding-left: 20px;
                padding-right: 20px;
                background-color: white;
                margin-left: auto;
                margin-right: auto;
            }
            #titleBar {
                font-size: 200%;
                font-weight: bold;
                color: #335;
            }
            #titleBarTable {
                padding: 0px;
                margin: 0px;
                width: 100%;
            }
            td.tbar {
                padding: 0px;
                margin: 0px;
                font-size: 180%;
                font-weight: bold;
                color: #335;
            }
            td.smallHead {
                font-size: 120%;
            }
            #subTitleBar {
                font-size: 80%;
                color: #88a;
                border-bottom: solid 1px #da7c0d;
                    text-align: right;
            }
        </style>
        <body>
            <div id='main'>
                <div id='titleBar'>
                    <table id='titleBarTable'>
                        <tr>
                            <td class='tbar smallHead'>Response</td>
                            <td class='tbar' align='right'>Peloton</td>
                        </tr>
                    </table>
                </div>
                <div id='subTitleBar'>
                    grid computing, batteries included
                </div>
"""
        XMLLanguageSerializer.__init__(self,
                                     header,
                                     "</div></body></html>", 
                                     "<ol>", 
                                     "</ol>", 
                                     "<li>%(value)s</li>", 
                                     "<ul>", 
                                     "</ul>", 
                                     "<li>%(key)s = %(value)s</li>",
                                     "<p>",
                                     "</p>")
    def format(self,v):
        """ Returns content-type, content. """
        s = XMLLanguageSerializer.write(self, v)
        return s
