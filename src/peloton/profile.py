# $Id: profile.py 106 2008-04-04 10:47:50Z mp $
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
"""
Every PSC and service has a profile used either declare the capabilities,
requirements and restrictions of a component. Classes here deal with comparing
profiles so as to simplify finding a match between, for example, services
and PSCs.
"""
import re
from fnmatch import fnmatchcase
import os
from types import StringType
from peloton.exceptions import ConfigurationError
from cStringIO import StringIO
                                                       
class BaseProfileComparator(object):
    """ Base class for all profile-comparing classes. In all methods,
if optimistic is set True the test will be generous in the logic of 
the particular implementation.

What is a profile?
==================

A profile enables a component to advertise its properties to others.
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

Comparing profiles
==================

It is not possible simply to ask if profile_A == profile_B or if 
profile_A > profile_B (implying some concept of 'exceeds the requirements'
perhaps) with the simple algebraic comparison operators.

We have instead to specify what keys get involved in the comparison and
how to do that. For example,  if a service has specified mincpus=2 
we have to make clear that a PSC with cpus >= mincpus is OK.

The dynamic requirements of this problem are made clear when it is considered
that arbitrary entries in a profile may be meaningful in certain comparisons.

For this reason comparisons are done with ProfileComparator classes of which
a number of standard ones are provided and others may be written by 
developers. The comparison operators in the PelotonProfile are rendered
un-useable.
    
Where strings are being compared, if a value could logicaly be a 
pattern (e.g. hostname in a service profile) you can indicate
whether it is a straight comparison, a regex or a fname pattern 
as follows:

    - r:<pattern> is a regular expression
    - f:<pattern> is a fnmatch pattern
    - s:<pattern> is a string. 
    - <pattern> is also a string (the default)
    
@todo: cast values for known keys as defined above
"""
    def ge(self, x, y, optimistic=True):
        "Return true if x >= y in the logic of this comparator."
        raise NotImplementedError()
    
    def le(self, x, y, optimistic=True):
        "Return true if x <= y in the logic of this comparator."
        raise NotImplementedError()
    
    def eq(self, x, y, optimistic=True):
        "Return true if x == y in the logic of this comparator."
        raise NotImplementedError()
    
    def gt(self, x, y, optimistic=True):
        "Return true if x > y in the logic of this comparator."
        raise NotImplementedError()
    
    def lt(self, x, y, optimistic=True):
        "Return true if x < y in the logic of this comparator."
        raise NotImplementedError()


class ServicePSCComparator(BaseProfileComparator):
    """ Compares a service profile with a PSC profile
to determine if the PSC is suitable for running the service. In
the logic of this class only equality is checked for; if svcProfile 
is determined equal to pscProfile it means that the PSC is adequate
for the running of this service.

This does not check properties such as the max number of services
that a PSC is permitted to run as the comparison may be made 
on a node not privy to such information. Instead, the comparing
node will request that a host node start a service and the host 
may choose at that point to reject the request.
"""
    def eq(self, sp, pp, optimistic=True):
        """ Comparison based on checking the following keys (listed
as key in service profile -- key in PSC profile):
    - hostname (pattern) -- hostname
    - [min|max]ram -- ram
    - [min|max]cpus -- cpus
    - platform (pattern) -- platform    
    - flags -- flags
    - excludeFlags -- flags
    
Flags are matched True if all the flags in the profile  list are present in 
the service list and none of the flags in the excludeFlags list are present in 
the service profile.

If send only the [profile] or [psclimits] section; keys must be in root of
object provided.
"""
        for service_key in sp.keys():
            if service_key in ['minram', 'mincpus']:
                try:
                    if self.__int_cf__(sp, service_key, pp, service_key[3:]) > 0:
                        return False
                except:
                    if not optimistic:
                        return False

            elif service_key in ['maxram', 'maxcpus']:
                try:
                    if self.__int_cf__(sp, service_key, pp, service_key[3:]) < 0:
                        return False
                except:
                    if not optimistic:
                        return False
                            
            elif service_key in ['hostname', 'platform']:
                if not self.__pattern_cf__(sp, service_key, pp, service_key):
                    return False
            
            elif service_key == 'flags':
                flags = sp['flags']
                pFlags = pp['flags']
                
                for f in flags:
                    if f not in pFlags:
                        return False
            
            elif service_key == 'excludeFlags':
                flags = sp['excludeFlags']
                pFlags = pp['flags']
                
                for f in flags:
                    if f in pFlags:
                        return False

        return True
    
    def __int_cf__(self, profilea, keya, profileb, keyb):
        if profileb.has_key(keyb):
            va = int(profilea[keya])
            vb = int(profileb[keyb])
            return cmp(va, vb)
        else:
            raise ConfigurationError("No key in profile b")


    def __pattern_cf__(self, profilea, keya, profileb, keyb):
        pattern = profilea[keya]
        if not profileb.has_key(keyb):
            return False
        if pattern[:2] == 'r:':
            # this is a regex
            regex = re.compile(pattern[2:])
            if regex.match(profileb[keyb]):
                return True
            else:
                return False
        elif pattern[:2] == 'f:':
            # fnmatch pattern
            pattern = pattern[2:]
            return fnmatchcase(profileb[keyb], pattern)
        else:
            # must be a string; remove initial s: if present
            if pattern[:2] == 's:':
                pattern = pattern[2:]
            return pattern == profileb[keyb]
            
        return False