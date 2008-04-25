# $Id: service.py 108 2008-04-04 15:39:30Z mp $
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
from peloton.utils.config import locateService
from peloton.utils.config import findTemplateTargetsFor
import peloton.utils.logging as logging

class PelotonService(object):
    """ Base class for all services. Public methods all have names prefixed
'public_', much as twisted spread remote callable methods are prefixed 'remote_'.

Configuration
=============

Services live in a strictly regimented structure on the file system. This simplifies
auto-generation of code and automated loading with minimal magic.

The root path points to a http://news.bbc.co.uk/directory
which contains the service directory. The service directory is laid out as 
follows, where the service is called FooBar::

    service_root/foobar/config/common.pcfg
                              /<gridmode>.pcfg
                              /<gridmode>.pcfg
                              /<...>
                              /profile.pcfg
                              /<gridmode>_profile.pcfg
                       /foobar.py
                       /<supporting code>
                       /resource/... to be defined later ...

Note that nomenclature is relatively simple; the service directory must be called
the same as the service shortname (when lowercased). The configuration files 
are named 'common.pcfg', 'test.pcfg' etc.

The service directory must contain at the very least a file called foobar.py (note
lower case) containing the class FooBar(PelotonService,...). Here FooBar retains
it's original capitalisation and, indeed, it is a matter of convention
that the service name should be camel case.            
"""
    def __init__(self, name, gridmode):
        """ homePath passed in on construction because from this module
cannot find where the concrete sub-class lives. Configurations are found relative to this
homePath in homePath/config. 

If 'init'==True then initialise things like the logger. May wish to initialise
with False if all we want is to load the config (as when launching a service)."""
        self.name = name
        self.gridmode = gridmode

    def initSupportServices(self):
        """ Start supporting services, such as the logger. Kept out of __init__
so that we can instantiate very lightly (as required by the launch sequencer.)"""
        self.logger = logging.getLogger(self.name)
        
    def loadConfig(self, servicePath):
        """ Load service configuration file and then augment with details
of all the methods in this service classed as 'public'. 

In doing this the attributes assigned by any decorators on the public methods
are checked out, especially the transform chain. Defaults are assigned
to, for example. HTML and XML output keys if none has been specified, standard
templates are sought out on the filesystem and attached if required and
the @template keyword is substituted for in the transform chain.

Developers should not use the logger here: loadConfig should be useable prior
to initSupportServices having been called."""
        servicePath, self.profile = locateService(self.name, servicePath, self.gridmode)

        publicMethods = [m for m in dir(self) if m.startswith('public_') and callable(getattr(self, m))]
        
        if not self.profile.has_key('methods'):
            self.profile['methods'] = {}

        methods = self.profile['methods']
        for nme in publicMethods:
            mthd = getattr(self, nme)
            shortname = nme[7:]
            
            templateTargets = findTemplateTargetsFor(servicePath, self.name, shortname)
            if hasattr(mthd, "_PELOTON_METHOD_PROPS"):
                properties = mthd._PELOTON_METHOD_PROPS
            else:
                properties = {}

            # step one, find all template files and insert
            # into transforms
            for target, templateFile in templateTargets:
                key = "transform.%s" % target
                if properties.has_key(key):
                    # look for @template and substitute
                    if "@template" in properties[key]:
                        properties[key][properties[key].index("@template")] \
                            = "template('%s')" % templateFile
                else:
                    # insert an entry
                    properties['transform.%s'%target] = \
                        ["template('%s')" % templateFile]
            
            # step two insert defaults for any empty transforms that
            # need a little something
            defaultTransforms = {'xml' : 'defaultXMLTransform',
                                 'html' : 'defaultHTMLTransform',
                                 'json' : 'jsonTransform'
                          }
            for target in ['xml', 'html', 'json']:
                key = "transform.%s" % target
                if not properties.has_key(key) \
                    or properties[key] == []:
                    properties[key]=[defaultTransforms[target]]
                    
            # step three, look for all transforms which still have
            # @transform in the chain and replace with defaults
            for k, v in properties.items():
                if not k.startswith('transform.'):
                    continue
                target = k[10:]
                if "@template" in v:
                    try:
                        v[v.index('@template')] = defaultTransforms[target]
                    except:
                        v[v.index('@template')] = ''

            if not methods.has_key(shortname):
                methods[shortname] = {}
            record = methods[shortname]
            record['doc'] = mthd.__doc__
            record['properties'] = str(properties)
            
        self.version = self.profile['version']
        
    def start(self):
        """ Executed after configuration is loaded, prior to starting work.
Can be used to setup database pools etc. Overide in actual services. """
        pass
    
    def stop(self):
        """ Executed prior to shuting down this service or the node.
Can be used to cleanup database pools etc. Overide in actual services. """
        pass
    
    def public_index(self):
        """ Default index page for HTTP connections. """
        return "There is no index for this service!"