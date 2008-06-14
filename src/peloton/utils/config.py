# $Id: config.py 110 2008-04-04 17:03:24Z mp $
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
""" The PelotonConfig class loads configuration files from a directory based on the rules 
for Peloton configuration files. 
"""

from configobj import ConfigObj, Section
from fnmatch import fnmatchcase as fnmatch
from types import DictType
from fnmatch import fnmatchcase
import os
import peloton.utils.logging as logging
from peloton.exceptions import ConfigurationError

class PelotonConfigObj(ConfigObj):
    """ Minor extension of ConfigObj that sets the interpolation method
to Template by default (i.e. substitutions using the ${key} format). Also
takes keyword argument 'extraKeys' which may be assigned a dictionary of
values that are copied into the root of the configuration tree. 

Also provides getpath and setpath to facilitate obtaining values from 
deep in the tree."""

    def __init__(self, infile=None, options=None, *args, **kargs):
        """ As per ConfigObj but also uses keyword argument 'extraKeys'
which may be assigned a dictionary of values to be copied into the root of the 
configuration tree. """
        if kargs.has_key('extraKeys') and type(kargs['extraKeys'])==DictType:
            extraKeys = kargs['extraKeys']
            del(kargs['extraKeys'])
        else:
            extraKeys = {}
        ConfigObj.__init__(self, infile=infile, options=options, *args, **kargs)
        self.interpolation = 'Template'
        for k,v in extraKeys.items():
            self.__setitem__(k, v)
            
    def getpath(self, key):
        """ Return the value of key where key is the path to the item
specified as a dot separated string. Thus

  v['a']['test']['name'] == v.getpath('a.test.name')
"""
        ps = self

        for p in key.split('.'):
            ps = ps[p]

        return ps
    
    def setpath(self, key, value, makeTree=True):
        """ Set key=value where key is a dotted path as interpreted
by getpath(). Will make entries in the path along the way if 
makeTree=True (default)

thus::
     v['a']['b']['c'] = 'Jon doe' 
is equivalent to::
    v.setpath('a.b.c', 'Jon doe')
"""
        splitKey = key.split('.')
        ps = self

        if len(splitKey) > 1:
            key = splitKey[-1]
            splitKey=splitKey[:-1]
            
            while splitKey:
                k = splitKey.pop(0)
                try:
                    ps = ps[k]
                except KeyError:
                    if makeTree:
                        ps[k] = {}
                        ps=ps[k]
                    else:
                        raise

        ps[key] = value 
    
    def __repr__(self):
        return "PelotonConfigObj(%s)" % str(self)
    
class PelotonConfig(object):
    """ Load and manage access to the Peloton configuration system.
    
This is a work in progress; the best way to configure grids, domains and PSCs
has yet to be settled upon. 

The scheme implemented here (see the loadConfig documentation for details)
has flaws, partly in that it relies very much on 
filesystem access control which may make it more opaque to casual debugging
than would be ideal.
"""
    
    #: Key is option in the command line options and value is
    #  the configuration item that it overrides if present. This
    #  latter is written as a dotted path, so 'bind' in the 
    #  [network] section is referred to as network.bind
    __CONFIG_OVERRIDES__ = {'bindhost':'psc.bind'}

    def __init__(self, cmdLineOpts):
        self.configdirs = [d for d in cmdLineOpts.configdirs
                           if os.path.exists(d) and os.path.isdir(d)]
        if not self.configdirs:
            raise ConfigurationError("No valid configuration directories found!")
        
        self.domainName = cmdLineOpts.domain
        self.__parsers = {}
        self.runtimeOpts = cmdLineOpts
        self.loadConfig()
    
    def loadConfig(self):
        """Initialise this configuration object with config data
from various configuration files sourced as follows.
    
There are three levels of configuration: 
    - grid level: This defines the properties of the largest
    organisational unit in Peloton, a unit that may contain a number
    of domains and which may span physical sites. 

    In this configuration file the 'gridmode' is assigned
    a value such as 'prod', 'live', 'test', 'uat' or whatever describes
    the overall nature of this group. This value is used to select 
    specific configuration files for the domain and PSC.
    
    There is only ONE grid configuration file called <shortname>.pcfg
    and the first such file found as the config directories are searched is
    the one used.
            
    - domain level: This defines the properties of a group of PSCs. PSCs
    in a domain may communicate directly with each other over Twisted RPC
    (between domains they must use the message bus). There may be many domain
    config files in the various configuration directories. Any file named
    <domain short name>_domain.pcfg will be read regardless of gridmode.
    Subsequently the file <domain short name>_<gridmode>_domain.pcfg will 
    be read. Values read in subsquent files will overide those in previously read
    files. New values will be added to the configuration.
    
    Under each configuration root the directories are structured as follows::
    
        $ROOT/grid.pcfg
             /domain.pcfg    <----- COMMON DOMAIN CONFIG
             /psc.pcfg       <----- COMMON PSC CONFIG
             /domain/<name>/common.pcfg
                            <gridmode>.pcfg
                            ...
             /domain/<name>/psc/common.pcfg
                                <gridmode>.pcfg
                                ...
    
    Beneath a given configuration root configuration files for many domains are found (one for each 
    gridmode) and for many PSCs (again one per gridmode) but these are only for a single grid.
    To describe another grid, a complete new set of configuration directories are made.
    
    If there are two configuration directories: /etc/peloton and /usr/local/share/peloton
    and, the domain short name is 'foo' and the gridmode is 'uat', configuration 
    files will be sought and read in the following order for the domain::
        
        # config common to all domains
        /etc/peloton/domain.pcfg
        /usr/local/share/peloton/domain.pcfg
        /etc/peloton/psc.pcfg
        /usr/local/share/peloton/psc.pcfg
        # config for specific domains
        /etc/peloton/domain/foo/common.pcfg
        /etc/peloton/domain/foo/uat.pcfg
        /usr/local/share/peloton/domain/foo/common.pcfg
        /usr/local/share/peloton/domain/foo/uat.pcfg
                
    - PSC level: This defines properties of the PSC. Configuration files are named
        common.pcfg and <gridmode>.pcfg with the search order being the same as for 
        domains and the files stored in the folder as shown above. By grouping different 
        behaviour into config files in different root directories
        you can switch in properties by adding directories to the search path. So if you 
        had a configuration that switched on debug logging you could add that to a psc pcfg file
        in /path/to/debug, for example.
    
Only files matching the pattern '*.pcfg' will be loaded.

If overrideOptions is assigned an OptionParser and an overrideMapping is provided 
then the command line options specified in the mapping will be used to override
the input configuration as determined by the mapping.

The overrideMapping is a dictionary where the key is an option in the OptionParser 
and the value a path to the configuration entry specified as a dotted path. So
if in the psc configuration file there is a name in the root called bind=0.0.0.0:1111 
it can be referenced as psc.bind.

Items can be deleted with del as usual, e.g.::

    del pc['psc.some.name']
    
Or ineed a whole configuration can be emptied (perhaps before or after a fork to a 
less privileged component) with::

    del pc['psc']    # remove the psc configuration
    del pc['domain'] # remove the domain configuration
"""
        def loadParsers(section, files):
            for cf in files:
                pco = PelotonConfigObj(cf)
    
                if self.__parsers.has_key(section):
                    self.__parsers[section].merge(pco)
                else:
                    self.__parsers[section] = pco

        # First load the grid configuration files
        configFiles = [j for j in 
                            ["%s/grid.pcfg"%i for i in self.configdirs]
                           if (os.path.exists(j) and os.path.isfile(j))]
        loadParsers('grid', configFiles)

        if not self.__parsers['grid']['gridmode']:
            raise ConfigurationError("gridmode is not assigned in the grid configuration file %s" % cf)
         
        gridMode = self.__parsers['grid']['gridmode']
        
        # Now load all domain config files
        configFiles = [k for k in 
                       ["%s/domain.pcfg" % i for i in self.configdirs]
                      if (os.path.exists(k) and os.path.isfile(k))]
        configFilesb = [k for k in 
                       ["%s/domain/%s/%s.pcfg" % (i,self.domainName,j) for i in self.configdirs for j in ['common', gridMode]]
                      if (os.path.exists(k) and os.path.isfile(k))]
        configFiles.extend(configFilesb)
        loadParsers('domain', configFiles)
        
        # Now load all PSC config files
        configFiles = [k for k in 
                       ["%s/psc.pcfg" % i for i in self.configdirs]
                      if (os.path.exists(k) and os.path.isfile(k))]
        configFilesb = [k for k in 
                       ["%s/domain/%s/psc/%s.pcfg" % (i,self.domainName,j) for i in self.configdirs for j in ['common', gridMode]]
                      if (os.path.exists(k) and os.path.isfile(k))]
        configFiles.extend(configFilesb)
        loadParsers('psc', configFiles)

        # apply overrides
        for k,override in PelotonConfig.__CONFIG_OVERRIDES__.items():
            try:
                overrideValue = getattr(self.runtimeOpts, k)
            except AttributeError:
                continue
            if overrideValue:
                overridePath = override.split('.')[::-1]
                v = self.__parsers[overridePath.pop()]
                while len(overridePath)>1:
                    v = v[overridePath.pop()]
                v[overridePath[0]] = overrideValue

    def has_key(self, key):
        """ Emulates a dict.has_key, but not efficient as it ends up
calling __getitem__ and trapping the error. It's convenience that will 
result in people making two calls to do the same thing effectively. """
        try:
            self.__getitem__(key)
            return True
        except:
            return False

    def __getitem__(self, key):
        """ Return a configuration value. The key is [grid|domain|psc].path.to.key.
So the reference psc.test.bindname refers to the psc configuration, section test, name
bindname. The config file might look as follows::
  
  #psc config
  v=10
  [test]
    bindname=localhost:1234
"""
        key = key.split('.')[::-1]
        v =  self.__parsers[key.pop()]
        while key:
            v = v[key.pop()]
        return v
    
    def __setitem__(self, key, value):
        """ Set the key to value. """
        key = key.split('.')[::-1]
        v = self.__parsers[key.pop()]
        while len(key) > 1:
            v = v[key.pop()]
        v[key.pop()] = value
    
    def __delitem__(self, key):
        """ Delete the key or, if it's just 'psc' or 'grid' or 'domain', delete
that whole configuration. """
        key = key.split('.')[::-1]
        if len(key) == 1:
            self.__parsers[key.pop()] = {}
        else:
            v = self.__parsers[key.pop()]
            while len(key) > 1:
                v = v[key.pop()]
            del v[key.pop()]
            
        
from peloton.exceptions import ServiceNotFoundError    
import peloton.profile
def locateService(serviceName, servicePath, gridMode='test', returnProfile=True, runconfig=None):
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
        serviceProfile = loadServiceProfile(servicePath, gridMode, runconfig)
    else:
        serviceProfile = None
    return (servicePath, serviceProfile)

def loadServiceProfile(servicePath, gridMode, runconfig=None):
    """Return the profile for this service"""
    configDir = os.sep.join([servicePath, 'config'])
    serviceProfile = peloton.profile.PelotonProfile()
    # set some defaults that are needed throughout the system so that
    # they do not need to be written into every configuration.
    serviceProfile['resourceRoot'] = servicePath+'/resource'
    
    serviceProfile.loadFromFile("%s/profile.pcfg" % configDir)
    try:
        serviceProfile.loadFromFile("%s/%s_profile.pcfg" % (configDir, gridMode))
    except ConfigurationError:
        # if there is no gridmode-specific config that's no big deal.
        pass
    if runconfig:
        if runconfig[0]=="/":
            serviceProfile.loadFromFile(runconfig)
        else:
            serviceProfile.loadFromFile("%s/%s" % (configDir, runconfig))
    
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