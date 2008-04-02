# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details

from peloton.profile import PelotonProfile
from peloton.exceptions import ConfigurationError
import os

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
    def __init__(self, name, profile, gridmode, versionMajor, versionMinor, versionPatch):
        """ homePath passed in on construction because from this module
cannot find where the concrete sub-class lives. Configurations are found relative to this
homePath in homePath/config. """
        self.name = name
        self.gridmode = gridmode
        self.profile = profile
        self.versionMajor = versionMajor
        self.versionMinor = versionMinor
        self.versionPatch = versionPatch
        
    def loadConfig(self):
        
        publicMethods = [m for m in dir(self) if m.startswith('public_') and callable(getattr(self, m))]
        if not self.profile.has_key('methods'):
            self.profile['methods'] = {}

        methods = self.profile['methods']
        for nme in publicMethods:
            mthd = getattr(self, nme)
            shortname = nme[7:]
            if not methods.has_key(shortname):
                methods[shortname] = {}
            record = methods[shortname]
            record['doc'] = mthd.__doc__

    def start(self):
        """ Executed after configuration is loaded, prior to starting work.
Can be used to setup database pools etc. Overide in actual services. """
        pass
    
    def stop(self):
        """ Executed prior to shuting down this service or the node.
Can be used to cleanup database pools etc. Overide in actual services. """
        pass
    