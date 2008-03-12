# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
"""
Every PSC and service has a profile used either declare the capabilities,
requirements and restrictions of a component. The PelotonProfile class
manages a profile and provides for comparing profiles.
"""

class PelotonProfile(dict):
    """ A profile enables a component to advertise its properties to others.
So a PSC will have a profile indicating, perhaps, what kind of host it is
running on, how much memory is available to it and the maximum number of
services it is permitted to manage. A service may have a profile describing
its requirements, e.g. that it needs to run on a UN*X host with more than
8Gb of RAM, and that it needs to be run on a minimum of 4 PSCs across a minimum
of 2 distinct hosts, for example. 

When a service is launched the service profile will be compared with PSC profiles 
to determine which host or combination of hosts might best be able to provide
for this service.

A profile may be built up from terms in a configuration file (in the [profile] 
section - all keys will be added to the profile) or at startup (so a PSC will
put its details discovered at runtime into its own profile).

Profiles are essentially dictionaries and may indeed be initialised from or
serialised to such form.
"""
    def loadFromConfig(self, conf):
        """ Supply a config object with a [profile] section from which
to pull key/value pairs. """
        if not conf.has_key('profile'):
            raise Exception("Config must have a [profile] section!")
        self.update(conf['profile'])
            
    
#    def __cmp__(self, pc):
#        """ Comparing two profiles seems a little tricky, and indeed more than
#one method is provided for doing so. However it's handy to be able to get a 
#meaningful response from a test such as "if hostpc >= servicepc" and this is
#what we hope loosely to achieve here.
#
#Equality is determined if both
#"""
