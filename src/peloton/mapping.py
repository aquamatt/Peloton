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
    """ The loader is the front-end to the launch sequencer. It's tasks are simply
to locate the service, load the profiles and instantiate the launch sequencer."""
    def __init__(self, kernel):
        self.kernel = kernel
        self.logger = logging.getLogger()
        
    def launchService(self, serviceName):
        """ Start the process of launching a service which will require
the following steps:
    
    1. Locate the profile, extract the psclimits and launch parameters
    3. Create a service launch sequencer with the profile and start it
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
    
        servicePath = locations[0]
        configDir = os.sep.join([servicePath, 'config'])
        profiles = ["profile.pcfg", "%s_profile.pcfg" % self.kernel.config['grid.gridmode']]
        serviceProfile = PelotonProfile()
        for profile in profiles:
            serviceProfile.loadFromFile("%s/%s" % (configDir, profile))
            
        # 2. Start the sequencer
        ServiceLaunchSequencer(kernel, servicePath, serviceName, profile).start()

class ServiceLaunchSequencer(object):
    """ State object used to keep track of a particular request to launch 
a service. Loading is an asynchronous process so an instance of this class is 
used to manage and track the loading of a single service. 

Starting the service involves the following process chain:

    1. Search through routing table for all PSCs, filter on those that 
       match the psclimits for the service.
    2. Request a suitable number of PSCs from the filtered batch
       to start the service.
    3. Any failures/refusals; select from 'spares' list
    6. If run out of PSCs before satisfying launch parameters, sleep until
       more PSCs become available.
"""
    def __init__(self, kernel, servicePath, serviceName, profile):
        self.kernel = kernel
        self. servicePath = servicePath
        self.serviceName = serviceName
        self.profile = profile
        
    def start(self):
        """ Initiate the sequence by calling upon the reactor to schedule the 
first step. """
        # this puts the next step onto the reactor queue thus freeing the reactor
        # to handle other requests that may have arrived since the service launch
        # request came in.
        reactor.callLater(0, self.findPSCs)
        
    def findPSCs(self):
        """ Search the PSC library for all PSCs that could, in principle, run
this service. """
        self.pscList = self.kernel.routingTable.matchPSC(self.profile['psclimits'])
        reactor.callLater(0, self.selectPSCs)
        
    def selectPSCs(self):
        """ Select from the list of valid PSCs a subset that would satisfy
the launch requirements of this service. """
        # split pscs by host
        self.pscsByHost = {}
        for psc in self.pscList:
            self.pscsByHost[psc.host] = psc
        
class PSCProxy(object):        
    """ Base class for PSC proxies through which the routing
table can exchange messages with PSCs. A proxy is required because
the PSC may be the local process, a PSC in the domain or a PSC in
another domain on the grid.
"""
    def __init__(self, profile, services=[]):
        self.profile = profile
        self.services = services
        
class RemotePSCProxy(PSCProxy):        
    """ Proxy for a PSC that is running on the same domain as this 
node."""
    def __init__(self, profile, services=[]):
        PSCProxy.__init__(self, profile, services)
          
class LocalPSCProxy(PSCProxy):
    """ Proxy for this 'local' PSC. """
    def __init__(self, kernel):
        PSCProxy.__init__(self, kernel.profile)          

class RoutingTable(object):
    """ Maintain a live database of all PSCs in the domain complete with their
profiles, the list of all services that they run and a library of all service profiles. """
    def __init__(self, kernel):
        self.kernel = kernel
        self.pscs=[]
        self.pscByHost={}
        self.pscByGUID={}

        self.selfproxy = LocalPSCProxy(kernel)
        self.addPSC(self.selfproxy)
    
    def addPSC(self, pscProxy):
        self.pscs.append(pscProxy)
        self.pscByHost[pscProxy.profile['ipaddress']] = pscProxy
        self.pscByGUID[pscProxy.profile['guid']] = pscProxy
#        for service in pscProxy.services:
#            self.addService(service)
    
    def addService(self, profile):
        self.services[profile.name] = profile
    