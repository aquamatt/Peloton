# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details

"""Mapping consists of the following core tasks, each represented by
a class in this module:

    - Loading: determining what PSCs should be asked to start a service, and
      getting them to do so (i.e. maps service to PSC).
      
    - Routing: Working out where a request should be sent to be satisfied, then
      sending it (ie maps request to psc.service). 
      
The RoutingTable is required by all.
"""

import os
import logging
from twisted.internet import reactor
from peloton.exceptions import ServiceNotFoundError
from peloton.profile import PelotonProfile

class ServiceLoader(object):
    """ The loader consults the routing table to find a set of PSCs 
that conform to a service profile's [psclimits]. Once a subset has been 
found that could run it, a number are chosen to conform to the profile's
[launch] configuration (ie n hosts, m PSCs etc).

The chosen PSCs are instructed to start the service; if a PSC refuses for
whatever reason then another is chosen. If there are  no suitable PSCs 
remaining the issue is logged and the request for the un-satisfied launches
is placed on a queue to be re-tried in some seconds.
"""

    def __init__(self, kernel):
        self.kernel = kernel
        self.logger = logging.getLogger()
        
    def launchService(self, serviceName):
        """ Start the process of launching a service which will require
the following steps:
    
    1. Locate the profile, extract the psclimits and launch parameters
    2. Search through routing table for all PSCs, filter on those that 
       match the psclimits for the service.
    3. Create a service launch request
    4. Request a suitable number of PSCs from the filtered batch
       to start the service.
    5. Any failures/refusals; select from 'spares' list
    6. If run out of PSCs before satisfying launch parameters, put
       the serivce launch request onto the stack for trying later.
 """
        self.logger.info("Mapping launch request for service %s" % serviceName)
        # 1. locate and load the profile
        #    search through service path
        serviceDir = serviceName.lower()
        locations = ["%s/%s" % (i, serviceDir) 
                     for i in self.kernel.initOptions.servicepath 
                     if os.path.exists("%s/%s" % (i, serviceDir)) 
                        and os.path.isdir("%s/%s" % (i, serviceDir))]
        
        # locations will hopefuly only be one item long; if not make 
        # a note in the logs and take the first location
        if len(locations) > 1:
            self.logger.info("ServiceLoader found more than one location for service %s (using first)" % serviceName)
        if not locations:
            raise ServiceNotFoundError("Could not find service %s" % serviceName)
    
        configDir = os.sep.join([locations[0], 'config'])
        profiles = ["profile.pcfg", "%s_profile.pcfg" % self.kernel.config['grid.gridmode']]
        serviceProfile = PelotonProfile()
        for profile in profiles:
            serviceProfile.loadFromFile("%s/%s" % (configDir, profile))
        print(serviceProfile)
        
class ServiceLaunchRequest(object):
    """ State object used to keep track of a particular request to launch 
a service. As the loading is an asynchronous process it is easiest to track
by keeping all state in one object. """
    def __init__(self):
        pass