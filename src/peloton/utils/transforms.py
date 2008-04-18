# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
""" A selection of useful transforms for the chainable transform
layer.

Each method is a closure that must return a transform method, the 
instance of the transform. 
Each returned method take one argument, the data to transform, and output 
a single value, the transformed data. Optionally static arguments 
may be passed in after the input data argument to control the transform
"""
import types
from peloton.utils.simplexml import HTMLFormatter
from peloton.utils.simplexml import XMLFormatter

def valueToDict():
    """ Takes data and returns the dict {'value':data}. """
    def _fn(data):
        return {'d':data}
    return _fn

def stripKeys(*args):
    """ Data must be a dict; each arg is taken as a key which,
if it exists in data, is removed. """
    def _fn(data):
        if not type(data) == types.DictType:
            return
        for k in args:
            if data.has_key(k):
                del(data[k])
        return data
    return _fn

def upperKeys():
    """ A rather pointless transform, largely for testing purposes. 
Transforms all keys in data (assuming it is a dictionary) to uppercase.
"""
    def _fn(data):
        if not type(data) == types.DictType:
            return
        for k,v in data.items():
            if type(k) == types.StringType:
                data[k.upper()] = v
                del(data[k])
        return data
    return _fn

xmlFormatter = XMLFormatter()
htmlFormatter = HTMLFormatter()

def defaultXMLTransform():
    def _fn(data):
        return xmlFormatter.format(data)
    return _fn

def defaultHTMLTransform():
    def _fn(data):
        return htmlFormatter.format(data)
    return _fn

from peloton.utils.json import JSONSerializer
class JSONFormatter(object):
    def __init__(self):
        self.writer = JSONSerializer()
        
    def format(self,v):
        """ Returns content-type, content. """
        try:
            s = self.writer.write(v)
        except:
            s = u'"Unserialisable response: %s"' % str(v)
        return s
jsonFormatter = JSONFormatter()

def jsonTransform():
    def _fn(data):
        return jsonFormatter.format(data)
    return _fn

from genshi.template import TemplateLoader
templateLoader = TemplateLoader([])
templateLoader.auto_reload = True
def template(templateFile):
    """ Passes data through a template. Automaticaly applies valueToDict
if the data is not a dictionary. """
    _valueToDict = valueToDict()
    def _fn(data):
        if not type(data) == types.DictType:
            data = _valueToDict(data)
        template = templateLoader.load(templateFile)
        return template.generate(**data).render()
    return _fn