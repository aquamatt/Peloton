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
from peloton.utils import logging
from peloton.utils.simplexml import HTMLFormatter
from peloton.utils.simplexml import XMLFormatter
from peloton.exceptions import PelotonError

def valueToDict(conf={}):
    """ Takes data and returns the dict {'d':data}. """
    def _fn(data, opts={}):
        return {'d':data, '_sys':opts}
    return _fn

def stripKeys(conf, *args):
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

def upperKeys(conf={}):
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

def string(conf={}):
    """ Stringify output """
    def _fn(data, opts):
        return str(data)
    return _fn

xmlFormatter = XMLFormatter()
htmlFormatter = HTMLFormatter()

def defaultXMLTransform(conf={}):
    def _fn(data, opts):
        return xmlFormatter.format(data)
    return _fn

def defaultHTMLTransform(conf={}):
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

def jsonTransform(conf={}):
    def _fn(data, opts):
        return jsonFormatter.format(data)
    return _fn

from genshi.template import TemplateLoader
templateLoader = TemplateLoader([])
templateLoader.auto_reload = True

try:
    from django.template import Template, Context
    import django.template.loader
    os.environ["DJANGO_SETTINGS_MODULE"] = "__main__"
    from django.conf import settings
    settings.TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)
    # list not tupple so that it can be appended to
    settings.TEMPLATE_DIRS = []
    DJANGO_ENABLED = True
except:
    DJANGO_ENABLED = False

def _expand(conf, f):
    """ If f is ~ return the full path to it. If $NAME is found, substitute
for the published name of the service."""
    if f and f == '~':
        return conf['resourceRoot']
    elif f and f.find('@NAME') > -1:
        return f.replace('@NAME', conf['publishedName'])
    else:
        return f

def template(conf, templateFile):
    """ Passes data through a template. Automaticaly applies valueToDict
if the data is not a dictionary. 

template file is either an absolute path (not recommended practice) or 
relative to the resource folder of the service. The former always starts
'/', the latter always '~/' for absolute clarity. Thus template foo.html.genshi
may be referenced as::

  ~/templates/DuckPond/foo.html.genshi
  
If the path contains the published name of the service, this may be written as
@NAME and will be substituted at runtime. Thus::

  ~/templates/@NAME/foo.html.genshi
  
will translate, when run in a service published as AirforceOne, to::

  ~/templates/AirforceOne/foo.html.genshi
  
Genshi is not the only fruit; if the Django libraries are on the python 
path you may also use Django templating. A Django template is indicated
by the suffix '.django', e.g::
  
  ~/templates/AirforceOne/foo.html.django
"""
    _valueToDict = valueToDict()
    # expand any ~ entries
    path, file = os.path.split(templateFile)
    try:
        path = [_expand(conf, i) for i in path.split('/')]
    except:
        path=[]
    path = os.path.abspath("/".join(path))
    templateFile = "%s/%s" % (path, file)
    if DJANGO_ENABLED and path not in settings.TEMPLATE_DIRS:
        settings.TEMPLATE_DIRS.append(path)
        
    def _fn(data, opts):
        if not type(data) == types.DictType:
            data = _valueToDict(data)
        data['_sys'] = opts
        data['_sys']['templateFile'] = templateFile
        if templateFile[-6:] == 'django':
            if not DJANGO_ENABLED:
                raise PelotonError("DJANGO templates not supported: Django libraries not in path")
            fp = open(templateFile)
            template = Template(fp.read())
            fp.close()
            context = Context(data)
            return template.render(context)
        else:
            template = templateLoader.load(templateFile)
            return template.generate(**data).render()
    return _fn