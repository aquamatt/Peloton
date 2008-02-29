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

def loadConfig(configDir, runMode, defaultConfig='', defaultConfigFile=None):
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

    return parser