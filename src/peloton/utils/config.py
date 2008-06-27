# $Id: config.py 110 2008-04-04 17:03:24Z mp $
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
""" The PelotonConfig class loads configuration files from a directory based on the rules 
for Peloton configuration files. 
"""

from fnmatch import fnmatchcase as fnmatch
from types import DictType
from fnmatch import fnmatchcase
import os
import peloton.utils.logging as logging
from peloton.exceptions import ConfigurationError
from cStringIO import StringIO

class PelotonSettings(dict):
    """ Dict-like object into which configuration is read. Can 
be initialised by reading a configuration file (Python format) 
or manipulated in the usual dict way. getattr is overridden so that
you can x.y == x['y'] if there is otherwise no 'y' attribute.
"""
    def __init__(self, initDict={}, initFile = None, **kwargs):
        """ Initialise empty or via any combination of:     
 - Providing an dictionary with which to initialise the profile with the
   initDict keyword argument
 - Specifying a file to read in (this is a python-format file) with the
   initFile keyword
 - Specifying keyword arguments (other than initDict and initFile) to be
   collected together and added to the settings.

    When a PelotonSettings is initialised afresh it is assigned the filename
    from which it was imported. Subsequent calls to load made from in the config
    do not overwrite this. This record of the origin source is used to process
    relative paths.
"""        
        
        if initFile:
            d,f = os.path.split(initFile)
            self.update({'__sourcedir__' : d,
                         '__sourcefile__' : f})
            self.load(initFile)
            
        self.update(initDict)
        self.update(kwargs)
            
    def load(self, fileName, target=None):
        """ Load from a file. This may be called multiple times; each
time this instance is passed as the LocalDict so subsiquent  loads will
modify and possibly reset the content. 

Target is optional. If set to a string, a new PelotonSettings will be
bound to that name within this instance and initialised from the file.
"""
        global_dict = {'PelotonSettings' : PelotonSettings,
                       'load' : self.load}

        origFilename = fileName
        if not os.path.exists(fileName):
            if self.has_key('__sourcedir__'):
                fileName = os.path.abspath(self['__sourcedir__']+os.path.sep+fileName)

            if not os.path.exists(fileName):
                raise ConfigurationError("Cannot import %s from %s/%s" % \
                        (origFilename, self['__sourcedir__'], self['__sourcefile__']))

        if target:
            self[target] = PelotonSettings(initFile=fileName)
        else:
            execfile(fileName, global_dict, self)       
        
    def __repr__(self):
        return("PelotonSettings(%s)" % dict.__repr__(self))
 
    def __getattr__(self, attr):
        return self.__getitem__(attr)
    
    def __setattr__(self, attr, value):
        self.__setitem__(attr, value)
        
    def prettyprint(self, padding=0, padchr='  '):
        prepad = padding*padchr
        pad = padchr*(padding+1)
        s = StringIO()
        s.write('PelotonSettings {\n')
        for k,v in self.items():
            if isinstance(v, PelotonSettings):
                s.write("%s%s = %s\n" % (pad, k, v.prettyprint(padding+1, padchr)))
            else:
                s.write("%s%s = %s\n" % (pad, k, str(v)))
        s.write("%s}\n"%prepad)
        return s.getvalue()
        
 
from peloton.exceptions import ServiceNotFoundError    
import peloton.profile
def locateService(serviceName, servicePath, returnProfile=True, runconfig=None):
    """ Searches for the service named serviceName in the service path
and loads the profile. Returns (serviceDirectory, profile) unless 
returnProfile is False in which case (serviceDirectory, None) returned.

Raises ServiceNotFoundError if the service is not found (surprise)."""
    #    search through service path
    logger = logging.getLogger()
    serviceDir = serviceName.lower()
    locations = ["%s/%s" % (i, serviceDir) 
                 for i in servicePath 
                 if os.path.exists("%s/%s" % (i, serviceDir)) 
                    and os.path.isdir("%s/%s" % (i, serviceDir))]
    
    # locations will hopefuly only be one item long; if not make 
    # a note in the logs and take the first location
    if len(locations) > 1:
        logger.info("Found more than one location for service %s (using first)" % serviceName)
    if not locations:
        raise ServiceNotFoundError("Could not find service %s" % serviceName)
    
    servicePath = locations[0]
    if returnProfile:
        serviceProfile = loadServiceProfile(servicePath, runconfig)
    else:
        serviceProfile = None
    return (servicePath, serviceProfile)

def loadServiceProfile(servicePath, runconfig=None):
    """Return the profile for this service"""
    configDir = os.sep.join([servicePath, 'config'])
    serviceProfile = PelotonSettings(initFile = "%s/service.pcfg" % configDir)
    # set some defaults that are needed throughout the system so that
    # they do not need to be written into every configuration.
    serviceProfile.profile.resourceRoot = servicePath+'/resource'

    if runconfig:
        if runconfig[0]=="/":
            serviceProfile.load(runconfig)
        else:
            serviceProfile.load(os.path.abspath("%s/%s" % (configDir, runconfig)))
    
    # validate
    logging.getLogger().warn("IMPLEMENT PROFILE VALIDATION")
    # -- confirm that resource root is in a valid location (allows restrictions
    #    to ensure that you can't accidentally publish /
    
    return serviceProfile

def findTemplateTargetsFor(resourceRoot, serviceName, method):
    """ A template will automatically be found for service methods
called over a given protocol if the file is placed in the right folder
and named as follows::

  $RESOURCEROOT/templates/<serviceName>/<method>.<transform key>.genshi
  OR
  $RESOURCEROOT/templates/<serviceName>/<method>.<transform key>.django
  
So, for example, a template to make HTML for MyService.getUserNames when
called over http might be as follows::

  /var/services/myservice/resource/templates/MyService/getUserNames.html.genshi
  OR
  /var/services/myservice/resource/templates/MyService/getUserNames.html.django

As can be seen from these examples either django or genshi templating may 
be used.
  
This method looks for all templates for a method and returns a list of 
transform targets for which templates exist.
"""
    try:
        rootDir = "%s/templates/%s" % (resourceRoot, serviceName)
        rootDir = os.path.abspath(rootDir)
        files = [ (i[i.find('.')+1:-7], "%s/%s"%(rootDir,i)) for i in 
                 os.listdir(rootDir)
                 if (fnmatchcase(i, "%s.*.genshi" % method) or fnmatchcase(i, "%s.*.django" % method))]
        try:
            import django
        except:
            # remove all django templates from the files list as 
            # django is not in this installation
            files = [f for f in files if not fnmatchcase(f[1], "*.django")]
        return files
    except OSError, ex:
        # path doesn't exist
        return []