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
from peloton.events import MethodEventHandler
from peloton.events import AbstractEventHandler
from peloton.utils import crypto
from peloton.exceptions import ServiceNotFoundError
from peloton.profile import PelotonProfile
from peloton.profile import ServicePSCComparator
import configobj

class ServiceLoader(AbstractEventHandler):
    """ The loader is the front-end to the launch sequencer and the component
which listens for and responds to requests from other PSCs to start a service. 

If this node issues a request to launch a service it locates the service, loads 
the profiles and instantiates the launch sequencer.

If this node is receiving a request to start a service it deals with checking
that it could, in principle, run the service and messaging with the 
requestor to determine whether it should or not. If yes, it instructs
a worker (or workers) to startup via the kernel.
"""
    def __init__(self, kernel):
        self.kernel = kernel
        self.logger = kernel.logger
        self.dispatcher = kernel.dispatcher
        self.spComparator = ServicePSCComparator()
        self.dispatcher.register('psc.service.loader', self, 'domain_control')

        self.callBackChannel = 'psc.service.loader.%s%s' % (kernel.guid, crypto.makeCookie(10))
        self.dispatcher.register(self.callBackChannel, self, 'domain_control')
        
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
        ServiceLaunchSequencer(self.kernel, servicePath, serviceName, serviceProfile).start()

    def eventReceived(self, msg, exchange='', key='', ctag=''):
        """ Handle events related to the starting of services as requested
by another node. """
        if msg['action'] == 'requestForLaunch':
            pp = PelotonProfile()
            pp.loadFromString(msg['serviceProfile'])
            msg['serviceProfile'] = pp
            self.logger.debug("Request to consider ability to launch service: %s (%s)" % (msg['serviceProfile']['name'], msg['serviceProfile']['version']))
            if self.spComparator.eq(msg['serviceProfile']['psclimits'], self.kernel.profile, optimistic=True):
                self.logger.debug("Profile OK - optimistic")
                self.dispatcher.fireEvent(msg['callback'],
                                          'domain_control',
                                          action='SERVICE_PSC_MATCH',
                                          callback=self.callBackChannel)
            else:
                self.dispatcher.fireEvent(msg['callback'],
                                          'domain_control',
                                          action='SERVICE_PSC_NOMATCH')
                
        elif msg['action'] == 'startService':
            pp = PelotonProfile()
            pp.loadFromString(msg['serviceProfile'])
            msg['serviceProfile'] = pp
            self.logger.debug("Instructed to start service %s (%s)" % (msg['serviceProfile']['name'], msg['serviceProfile']['version']))
            self.kernel.startService(msg['serviceName'], int(msg['serviceProfile']['launch']['workersperpsc']))

class ServiceLaunchSequencer(AbstractEventHandler):
    """ State object used to keep track of a particular request to launch 
a service. Loading is an asynchronous process so an instance of this class is 
used to manage and track the loading of a single service. 

Starting the service involves the following process chain:

    1. Message all PSCs with the Service Profile on the 
    2. PSCs check to see if they could run the service and if their
       current load and state permit the starting of a new service.
       If so, respond as willing on the requestors private channel.
    3. As willing node responses are collected, message them back privately
       to start the service. Fill slots in the launch profile (e.g. maybe
       two machines of one sort, one of another required etc., or more simply,
       n service handlers to be started, m per PSC).
    4. After delay, re-launch request if not all launch request slots are
       filled.
       
This class broadcasts on psc.service.loader and listens on a temporary private channel
in psc.service.loader.<key>. Both in the domain_control exchange.
"""
    def __init__(self, kernel, servicePath, serviceName, profile):
        self.kernel = kernel
        self.logger = kernel.logger
        self.dispatcher = kernel.dispatcher
        self.servicePath = servicePath
        self.serviceName = serviceName
        self.profile = profile
        self.callBackChannel = 'psc.service.loader.%s%s' % (kernel.guid, crypto.makeCookie(10))
        self.dispatcher.register(self.callBackChannel, self, 'domain_control')
        
        # on this channel we get notified of a PSC having launched a service.
        self.dispatcher.register('psc.service.notification', self, 'domain_control')
        
        # this counter gets decremented as services are launched. Once 
        # the counter hits zero, our job is done.
        try:
            try:
                self.pscRequired = int(self.profile['launch']['minpscs'])
            except:
                self.logger.error("'minpscs' key in configuration for service %s has an invalid value (%s): default to 2" \
                                  % (self.serviceName, self.profile['launch']['minpscs']))
                self.pscRequired=2
            self.launchPending = 0
            # list of PSCs that have offered to run the service
            self.pscReadyQueue = []
        except KeyError:
            self.pscRequired = 2
            self.profile['launch']['minpscs'] = self.pscRequired
            
            
        try:
            self.workersPerPSC = self.profile['launch']['workserperpsc']
        except KeyError:
            self.workersPerPSC = 2
            self.profile['launch']['workserperpsc'] = self.workersPerPSC
            
    def start(self):
        """ Initiate the service startup sequence. This event will be received by all nodes
including self. We could optimise by checking the local node first etc, but why? This makes
for more code and it's somehow more elegant simply to throw this to the grid as a whole without
making ourselves special."""
        self.dispatcher.fireEvent('psc.service.loader',
                                  'domain_control',
                                  action='requestForLaunch',
                                  callback=self.callBackChannel,
                                  serviceName=self.serviceName,
                                  servicePath=self.servicePath,
                                  serviceProfile=repr(self.profile))
        
    def eventReceived(self, msg, exchange='', key='', ctag=''):
        """ Handle messages placed on the private callback channel for this 
launch sequencer. Type of message is indicated by msg['action'] value. """
        if key == self.callBackChannel:
            if msg['action'] == 'SERVICE_PSC_MATCH':
                self.logger.debug("Service match from %s" % msg['sender_guid'])
                self.pscReadyQueue.insert(0, msg)
                
        elif key == 'psc.service.notification':
            # event fired when a service has been started up
            if msg['serviceName'] == self.serviceName and msg['state'] == 'running':
                self.logger.debug("Launch sequencer notified of service start: %s " % self.serviceName)
                self.launchPending -= 1
                self.pscRequired -= 1

        self.checkQueue()

    def checkQueue(self):
        """ Called to process the queue of pending PSC offers to start
a service."""
        while (self.pscRequired - self.launchPending > 0) and self.pscReadyQueue:
            msg = self.pscReadyQueue.pop()
            self.launchPending += 1
            self.dispatcher.fireEvent(msg['callback'],
                                      'domain_control',
                                      action='startService',
                                      serviceName=self.serviceName,
                                      servicePath=self.servicePath,
                                      serviceProfile=repr(self.profile))
        
        if self.pscRequired == self.launchPending == 0:
            self.done()
        
    def done(self):
        """ Close up the private callback channel; we're done. Called once the launch
requirements of the service have been met."""
        self.logger.info("Service %s successfuly launched. " % self.serviceName)
        self.dispatcher.deregister(self)
        
class PSCProxy(object):        
    """ Base class for PSC proxies through which the routing
table can exchange messages with PSCs. A proxy is required because
the PSC may be the local process, a PSC in the domain or a PSC in
another domain on the grid.
"""
    def __init__(self, profile):
        self.profile = profile
        self.extractServices()
        
    def extractServices(self):
        """ Run through the profile and pull out all the service
information. """
        raise NotImplementedError
    
    def call(self, service, method, *args, **kwargs):
        """ Request the serice method be called on this 
PSC. """
        raise NotImplementedError
        
class TwistedPSCProxy(PSCProxy):        
    """ Proxy for a PSC that is running on the same domain as this 
node and accepts Twisted PB RPC. This is the prefered proxy to use
if a node supports it and if it is suitably located (i.e. same 
domain)."""
    def __init__(self, profile):
        PSCProxy.__init__(self, profile)
    
    def extractServices(self):
        pass
          
class MessageBusPSCProxy(PSCProxy):
    """ Proxy for a PSC that is able only to accept RPC calls over
the message bus for whatever reason. """
    def __init__(self, profile):
        PSCProxy.__init__(self, profile)
          
class LocalPSCProxy(PSCProxy):
    """ Proxy for this 'local' PSC. """
    def __init__(self, kernel):
        PSCProxy.__init__(self, kernel.profile)          

    def extractServices(self):
        pass

class RoutingTable(object):
    """ Maintain a live database of all PSCs in the domain complete with their
profiles, the list of all services that they run and a library of all service profiles. 

The RoutingTable is responsible for broadcasting this PSC profile
to the domain and handling responses. It also listens to and responds
to broadcasts from other new PSCs. The protocol runs as follows:

    1. On startup, RoutingTable.notifyConnect is called to notify
       the domain of our presence.
       
    2. These broadcast PSC profiles are received in 
       RoutingTable.respond_presence which
       checks to see if the profile is valid by verifying
       the domain cookie matches that which we have.
    
    3. Responses are sent on the private call-back channel of
       the new node. The response will either be the profile of
       all other PSC nodes in the domain, or error messages
       indicating that this PSC is not welcome; if this is the
       case the PSC exits.
       
Profiles received are logged into the routing table.
"""
    # mapping of proxy to specific RPC mechanisms
    # that a PSC may accept
    PSC_PROXIES = {'pb'  : TwistedPSCProxy,
                   'bus' : MessageBusPSCProxy}

    def __init__(self, kernel):
        self.kernel = kernel
        self.logger = kernel.logger
        self.dispatcher = kernel.dispatcher
        self.pscs=[]
        self.pscByHost={}
        self.pscByGUID={}

        self.selfproxy = LocalPSCProxy(kernel)
        self.addPSC(self.selfproxy)
        self._setHandlers()
    
    def notifyConnect(self):
        """ Call to publish our own profile over the bus """
        self.dispatcher.fireEvent(key="psc.presence", 
                                exchange="domain_control", 
                                action='connect',
                                myDomainCookie=self.kernel.domainCookie,
                                profile=repr(self.kernel.profile))

    def notifyDisconnect(self):
        """ Call to unhook ourselves from the mesh """
        self.dispatcher.fireEvent(key="psc.presence",
                                  exchange="domain_control",
                                  action='disconnect')

    def respond_presence(self, msg, exch, key, ctag):
        """ Receiving end of a publishProfile. Send a message back
to this node on its private channel psc.<guid>.init"""
        if msg['sender_guid'] == self.kernel.guid:            # don't process messages from self
            return
        
        if msg['action'] == 'connect':
            ### Reject anyone with an invalid cookie.
            if msg['myDomainCookie'] != self.kernel.domainCookie:
                self.dispatcher.fireEvent(key="psc.%s.init" % msg['profile']['guid'],
                                        exchange="domain_control",
                                        INVALID_COOKIE = True)
                return

            pp = PelotonProfile()
            pp.loadFromString(msg['profile'])
            msg['profile'] = pp
    
            if msg['profile']['guid'] != msg['sender_guid']:
                self.dispatcher.fireEvent(key="psc.%s.init" % msg['profile']['guid'],
                                        exchange="domain_control",
                                        GUID_MISMATCH = True)
                return
    
            self.dispatcher.fireEvent(key="psc.%s.init" % msg['profile']['guid'],
                                    exchange="domain_control",
                                    profile=repr(self.kernel.profile))
        

            try:
                clazz = self._getProxyForProfile(msg['profile'])
                self.addPSC(clazz(msg['profile']))
            except:
                self.logger.error("Cannot register PSC (%s) with RPC mechanisms %s" \
                                  % (msg['profile']['guid'], str(msg['profile']['rpc'])))                
            
        elif msg['action'] == 'disconnect':
            self.kernel.logger.info("Received disconnect from %s" % msg['sender_guid'])
            self.removePSC(msg['sender_guid'])
            
    def respond_pscProfile(self, msg, exch, key, ctag):
        self.logger.debug("Profile response from node %s" % msg['sender_guid'])
        if msg.has_key("INVALID_COOKIE"):
            self.kernel.logger.error("Cannot join domain: Invalid cookie")
            self.kernel.closedown()
            return
        elif msg.has_key("GUID_MISMATCH"):
            self.kernel.logger.error("Cannot join domain: profile GUID and sender GUID mis-match")
            self.kernel.closedown()
            return
        pp = PelotonProfile()
        pp.loadFromString(msg['profile'])
        msg['profile'] = pp
        try:
            clazz = self._getProxyForProfile(msg['profile'])
            self.addPSC(clazz(msg['profile']))
        except Exception, ex:
            self.logger.error("Cannot register PSC (%s) with RPC mechanisms %s" \
                              % (msg['profile']['guid'], str(msg['profile']['rpc'])))                

    def _getProxyForProfile(self, profile):
        """ Return a proxy appropriate for the PSC described by this profile."""
        rpcAllowed = profile['rpc']
        # prioritise PB as the RPC mechanism of choice;
        # failing that just skip through the list until one
        # is found that we can handle. This allows the config
        # writer to imply preference in mechanisms whilst disallowing
        # de-prioritisation of PB.
        if 'pb' in rpcAllowed:
            return TwistedPSCProxy
        else:
            for r in rpcAllowed:
                if RoutingTable.PSC_PROXIES.has_key(r):
                    return RoutingTable.PSC_PROXIES.has_key(r)
                    break
            else:
                raise Exception("No suitable proxy for profile.")
    

    def _setHandlers(self):
        """ Register for events relevant to routing. """
        # receive broadcast presence notifications here
        self.dispatcher.register("psc.presence",
               MethodEventHandler(self.respond_presence),
               "domain_control")
        
        # private channel on which this node can be contacted to
        # initialise with other nodes' profiles etc.
        self.dispatcher.register("psc.%s.init" % self.kernel.guid,
               MethodEventHandler(self.respond_pscProfile),
               "domain_control")
    
    def addPSC(self, pscProxy):
        """ Store the PSC provided. """
        self.kernel.logger.info("Adding profile for node: %s" % pscProxy.profile['guid'])
        self.pscs.append(pscProxy)
        self.pscByHost[pscProxy.profile['ipaddress']] = pscProxy
        self.pscByGUID[pscProxy.profile['guid']] = pscProxy
#        for service in pscProxy.services:
#            self.addService(service)
    
    def removePSC(self, guid):
        """ Remove the PSC record for the PSC with specified GUID. """
        try:
            del(self.pscByGUID[guid])
        except KeyError:
            self.logger.error("Received disconnect from stranger node: %s" % guid)
    
    def addService(self, profile):
        self.services[profile.name] = profile
    