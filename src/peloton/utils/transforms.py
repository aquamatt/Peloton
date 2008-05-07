# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
""" A selection of useful transforms for the chainable transform
layer.

Each method is a closure that must return a transform method, the 
instance of the transform. 
Each returned method takes two arguments, the data to transform and a
dictionary of additional data, and output 
a single value, the transformed data. Optionally static arguments 
may be passed in after the input data argument to control the transform
"""
import sys
import os
import types
from peloton.utils.simplexml import HTMLFormatter
from peloton.utils.simplexml import XMLFormatter
from peloton.exceptions import PelotonError

def valueToDict():
    """ Takes data and returns the dict {'d':data}. """
    def _fn(data):
        return {'d':data}
    return _fn

def stripKeys(*args):
    """ Data must be a dict; each arg is taken as a key which,
if it exists in data, is removed. """
    def _fn(data, opts):
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
    def _fn(data, opts):
        if not type(data) == types.DictType:
            return
        for k,v in data.items():
            if type(k) == types.StringType:
                data[k.upper()] = v
                del(data[k])
        return data
    return _fn

def string():
    """ Stringify output """
    def _fn(data, opts):
        return str(data)
    return _fn

xmlFormatter = XMLFormatter()
htmlFormatter = HTMLFormatter()

def defaultXMLTransform():
    def _fn(data, opts):
        return xmlFormatter.format(data)
    return _fn

def defaultHTMLTransform():
    def _fn(data, opts):
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
    def _fn(data, opts):
        return jsonFormatter.format(data)
    return _fn

from genshi.template import TemplateLoader
templateLoader = TemplateLoader([])
templateLoader.auto_reload = True
def _expand(f):
    """ If f is @-prefixed string assume the name is a service
name and return the full path to it. """
    if f and f[0] == '@':
        svcName = f[1:]
        svcFolderName = svcName.lower()
        # iterate over python path looking for sub-dirs svcFolderName.
        # return first to be found or raise PelotonError
        for p in sys.path:
            fname = p+'/'+svcFolderName+'/resource'
            if os.path.exists(fname):
                return fname
        raise PelotonError("Could not locate servcie for %s" % f)
    else:
        return f

def template(templateFile):
    """ Passes data through a template. Automaticaly applies valueToDict
if the data is not a dictionary. 

template file is either an absolute path (bad form) or relative to the 
resource folder in a service
where the service is referenced as @ServiceName. This allows a template
in another service to be referenced. So, if the template foo.html.genshi
in the DuckPond service one would reference::

  @DuckPond/templates/DuckPond/foo.html.genshi
  
"""
    _valueToDict = valueToDict()
    # expand any @ entries
    path, file = os.path.split(templateFile)
    try:
        path = [_expand(i) for i in path.split('/')]
    except:
        path=[]
    templateFile = "%s/%s" % ("/".join(path), file)

    def _fn(data, opts):
        if not type(data) == types.DictType:
            data = _valueToDict(data)
        template = templateLoader.load(templateFile)
        return template.generate(**data).render()
    return _fn