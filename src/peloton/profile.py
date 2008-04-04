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
import re
from fnmatch import fnmatchcase
import os
from types import StringType
from peloton.utils.config import PelotonConfigObj
from peloton.exceptions import ConfigurationError
from cStringIO import StringIO

class PelotonProfile(PelotonConfigObj):
    """A profile enables a component to advertise its properties to others.
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

Structure of a profile
======================

A profile is a set of nested dictionaries that can be written also
as an INI file. It fully describes a component via a set of keys, some
of which are mandatory, some pre-defined in meaning and the rest 
free-form

Services include a description of methods and restrictions in them. 
A service profile looks as follows::

    name=<published name>
    comment=<short comment>
    author=<optional author(s)>
    buildversion=1234
    version=1.0.1
    
    [methods]
      # would generally be auto-generated at run-time
      [[method_a]]
          # security names map to definitions in
          # the authorisation system. Peloton imbues
          # no name with specific meaning.
          security=public
        
          # a transform (or sequence of transforms) is specified
          # for a protocol. When the edge node receives the result
          # it will apply the given transform(s) if the client request
          # is on a protocol for which a transform is specified.
          # For example, this line transforms the result into a dictionary
          # (key='value', value= the value) and passes to a template if
          # and only if the call was for an html response:
          transform_html=peloton.transform.toDict,peloton.transform.genshi(tmplate)

          # value is passed to the transform callable after any optional arguments
          # specified in the transform clause (as in the genshi transform above).
        
          # the following might do some magic foo to make an FPML document from
          # this data if that were requested (in some RESTful way, perhaps).
          transform_fpml=my.transform.toFPML
    
          # we may allow for type-casting (useful with HTTP requests where
          # everything comes in as a string):
          type_0=int
          type_1=float
          type_income=float
        
      [[method_b]]
          # describe method_b 
          # ...

    [psclimits]
        # describe minimum requirements for a host PSC
        minram=2048 # Mb
        maxram=4096
        mincpus=2
        hostname=r:rc.* # regex the name of a host!
        flags=list,of,flags,required
        excludeFlags=list,of,bad,flags
        
    [launch]
        # parameters describing configuration of service in the domain
        # e.g. require that it run in two PSCs spread over two hosts
        minpscs=2
        minhosts=2
        
Note that many of the entries in, for example, a method section will be set
from the code (the security setting may be determined by a decorator, for
example, as also the type cast info).

A PSC is configured with a different profile describing its characteristics::
    id=<runtime UID on domain>
    started=<timestamp>
    hostname=<hostname>
    ram=4096
    cpus=4
    platform=linux
    # optional specification of the max number of 
    # services to be managed by the PSC
    maxservices=10 
    
    # weight is a dimensionless unit that quantifies the 
    # administrators' idea of how powerful or 'big' this PSC
    # is relative to the others. It's used in routing: if there
    # are two PSCs, the one with weight 3 will get three times as
    # many hits as one with weight 1 (in principle).
    weight=2.0
    
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
    def loadFromConfig(self, conf):
        """ Supply a config object with a [profile] section from which
to pull key/value pairs. """
        if not conf.has_key('profile'):
            raise ConfigurationError("Config must have a [profile] section!")
        self.merge(conf['profile'])
            
    def loadFromFile(self, _file, configDirs=[]):
        """ Expects either:
        1. an absolute path or one relative to one of the configuration
           paths specified with -c|--config and supplied as the second argument.
           or...
           
        2. a file-like object

The profile is considered as the entire
file, from the root. It is merged with the current contents, if any, of this 
profile.
"""
        if type(_file) == StringType:
            filesToSearch = [_file]
            filesToSearch.extend([os.sep.join(i, _file) for i in configDirs])
            
            for f in filesToSearch:
                if os.path.exists(f) and os.path.isfile(f):
                    confobj = PelotonConfigObj(f)
                    self.merge(confobj)
                    break
            else:
                raise ConfigurationError("Could not find or open profile %s" % _file)
        else:
            confobj = PelotonConfigObj(_file)
            self.merge(confobj)

    def __repr__(self):
#        r = PelotonConfigObj.__repr__(self)
#        r = r.replace('ConfigObj', 'PelotonProfile')
#        return r
        return "PelotonProfile(%s)" % str(self)
                                                        
class BaseProfileComparator(object):
    """ Base class for all profile-comparing classes. In all methods,
if optimistic is set True the test will be generous in the logic of 
the particular implementation.
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