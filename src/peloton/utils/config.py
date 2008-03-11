# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
""" The PelotonConfig class loads configuration files from a directory based on the rules 
for Peloton configuration files. 
"""

from configobj import ConfigObj
from cStringIO import StringIO
from fnmatch import fnmatchcase as fnmatch
import os

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
            raise Exception("No valid configuration directories found!")
        
        self.gridName = cmdLineOpts.grid
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
    
    There is only ONE grid configuration file called <shortname>_grid.pcfg
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
    
    If there are two configuration directories: /etc/peloton and /usr/local/share/peloton
    and, the domain short name is 'foo' and the gridmode is 'uat', configuration 
    files will be sought and read in the following order::
            
        /etc/peloton/foo_domain.pcfg
        /etc/peloton/foo_uat_domain.pcfg
        /usr/local/share/peloton/foo_domain.pcfg
        /usr/local/share/peloton/foo_uat_domain.pcfg
                
    - PSC level: This defines properties of the PSC. Configuration files are named
        psc.pcfg and psc_<gridmode>.pcfg with the search order being the same as for 
        domains. By grouping different behaviour into config files in different directories
        you can switch in properties by adding directories to the search path. So if you 
        had a configuration that switched on debug logging you could add that to a psc.pcfg
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
        configFiles = [[os.sep.join([i,j]) for j in os.listdir(i) if fnmatch(j, "*.pcfg") ] for i in self.configdirs]
        def aext(a,b):
            a.extend(b)
            return a
        configFiles = reduce(aext, configFiles)
        
        # First load the grid configuration file
        for cf in configFiles:
            fn = cf.split(os.sep)[-1]
            if fn == "%s.pcfg" % self.gridName:
                self.__parsers['grid'] = ConfigObj(cf)
                break
        else:
            raise Exception("Could no find grid config file: %s.pcfg" % self.gridName)

        if not self.__parsers['grid']['gridmode']:
            raise Exception("gridmode is not assigned in the grid configuration file %s" % cf)

        # Now load all domain config files
        domainConfigs = [p for p in configFiles 
                         if (p.split(os.sep)[-1]=="%s_domain.pcfg" % self.domainName)
                             or p.split(os.sep)[-1]=="%s_%s_domain.pcfg" % (self.domainName, self.__parsers['grid']['gridmode'])]
        
        self.__parsers['domain'] = ConfigObj(domainConfigs[0])
        for conf in domainConfigs[1:]:
            self.__parsers['domain'].merge(ConfigObj(conf))

        # Now load all PSC config files
        pscConfigs = [p for p in configFiles 
                         if (p.split(os.sep)[-1]=="psc.pcfg")
                             or p.split(os.sep)[-1]=="psc_%s.pcfg" % (self.__parsers['grid']['gridmode'])]
        
        self.__parsers['psc'] = ConfigObj(pscConfigs[0])
        for conf in pscConfigs[1:]:
            self.__parsers['psc'].merge(ConfigObj(conf))

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