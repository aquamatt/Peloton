# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
""" Load configuration files from a directory based on run mode.

Loads config files frome each dir in sorted order, so you can control
load sequence by prefixing two digit number, say. This is probably not
a useful feature, but it's there if we need it.

"""
from configobj import ConfigObj
from cStringIO import StringIO
from fnmatch import fnmatchcase as fnmatch
import os

def loadConfig(configDir, runMode, 
               defaultConfig='', defaultConfigFile=None,
               overideOptions=None, overideMapping={}):
    """Return a configuration object with config data
from all configuration files found in configDir. Looks
first in configDir then configDir/runMode.

Files are loaded in sort order from each dir. In this way 
arguments can be overlayed, with common properties being 
reset by those in runMode files.

Only files matching the pattern '*.pcfg' will be loaded.

A default configuration can be passed as a string (defaultConfig) or a file
name (defaultConfigFile). This default initialises the configuration object. If
both arguments are supplied the file is used and the string ignored.

If overideOptions is assigned an OptionParser and an overideMapping is provided 
then the command line options specified in the mapping will be used to overide
the input configuration as determined by the mapping.

The overideMapping is a dictionary where the key is an option in the OptionParser 
and the value a path to the configuration entry specified as a dotted path. So
if there is a section [network] with name bind=0.0.0.0:1111 in the configuration
file it can be referenced as network.bind.
"""
    dirsToSearch = [i for i in [configDir, os.sep.join([configDir, runMode])] 
                    if os.path.isdir(i)]
    
    configFiles = [[j for j in os.listdir(i) if fnmatch(j, "*.pcfg")] for i in dirsToSearch]
    # sort in each directory and append to the master list 
    orderedFiles = []
    for i in configFiles: 
        i.sort()
        orderedFiles.extend(i) 
    
    if defaultConfigFile:
        parser = ConfigObj(defaultConfigFile)
    else:
        parser = ConfigObj(StringIO(defaultConfig))
        
    for conf in orderedFiles:
        parser.merge(ConfigObj(conf))

    # apply overides
    if overideMapping and overideOptions:
        for k,overide in overideMapping.items():
            overideValue = getattr(overideOptions, k)
            if overideValue:
                overidePath = overide.split('.')[::-1]
                v = parser
                while len(overidePath) > 1:
                    v = v[overidePath.pop()]
                v[overidePath[0]] = overideValue

    return parser