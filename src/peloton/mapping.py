# $Id: mapping.py 118 2008-04-09 22:20:43Z mp $
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

import random
import time
from peloton.events import MethodEventHandler
from peloton.events import AbstractEventHandler
from peloton.utils import crypto
from peloton.utils.config import PelotonConfigObj
from peloton.utils.structs import RoundRobinList
from peloton.profile import PelotonProfile # needed for eval
from peloton.profile import ServicePSCComparator
from peloton.utils import getClassFromString
from peloton.exceptions import NoProvidersError
from peloton.pscproxies import LocalPSCProxy
from peloton.pscproxies import PSC_PROXIES

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
        
    def launchService(self, serviceName, runconfig=None):
        """ Start the process of launching a service which will require
the following steps:
    
    1. Locate the profile, extract the psclimits and launch parameters
    3. Create a service launch sequencer with the profile and start it
 """
        self.logger.info("Mapping launch request for service %s" % serviceName)
        # 1. locate and load the profile
        pqcn = "%s.%s.%s" % (serviceName.lower(), serviceName.lower(), serviceName)
        cls = getClassFromString(pqcn, reload=True)
        self.__service = cls(serviceName, self.kernel.config['grid.gridmode'], None, None)
        self.__service.loadConfig(self.kernel.initOptions.servicepath, runconfig)
        # 2. Start the sequencer
        ServiceLaunchSequencer(self.kernel, serviceName, self.__service.profile).start()

    def eventReceived(self, msg, exchange='', key='', ctag=''):
        """ Handle events related to the starting of services as requested
by another node. """
        if msg['action'] == 'requestForLaunch':
            msg['serviceProfile'] = eval(msg['serviceProfile'])
            # store service profile in the library
            self.kernel.serviceLibrary.setProfile(msg['serviceProfile']['version'],
                                                  msg['launchTime'],
                                                  msg['serviceProfile'])
            
            self.logger.debug("Request to consider ability to launch service: %s (%s) as %s" % (msg['serviceProfile']['name'], msg['serviceProfile']['version'], msg['serviceProfile']['publishedName']))
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
            self.logger.debug("Instructed to start service %s as %s" % (msg['serviceName'], msg['publishedName']))
            self.kernel.startService(msg['serviceName'],msg['publishedName'], msg['version'], msg['launchTime'])

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
    4. :todo: After delay, re-launch request if not all launch request slots are
       filled.
       
This class broadcasts on psc.service.loader and listens on a temporary private channel
in psc.service.loader.<key>. Both in the domain_control exchange.
"""
    def __init__(self, kernel, serviceName, profile):
        self.kernel = kernel
        self.logger = kernel.logger
        self.dispatcher = kernel.dispatcher
        self.serviceName = serviceName
        self.publishedName = profile['publishedName']
        self.profile = profile
        # launchTime is tagged to the service version in all the
        # node's routing tables so as to be able to differentiate
        # between different launches of the same versioned service.
        self.launchTime = long(time.time()*1000.0)
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
            
        self.workersRequired = self.pscRequired * self.workersPerPSC
                
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
                                  launchTime = self.launchTime,
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
            if msg['serviceName'] == self.serviceName and \
                msg['state'] == 'running' and \
                msg['publishedName'] == self.publishedName:
                self.logger.debug("Launch sequencer notified of service start: %s - %s " % (self.serviceName, msg['token']))
                self.launchPending -= 1
                self.workersRequired -= 1

        self.checkQueue()

    def checkQueue(self):
        """ Called to process the queue of pending PSC offers to start
a service."""
        while (self.workersRequired - self.launchPending > 0) and self.pscReadyQueue:
            msg = self.pscReadyQueue.pop()
            self.launchPending += 1
            self.dispatcher.fireEvent(msg['callback'],
                                      'domain_control',
                                      action='startService',
                                      launchTime=self.launchTime,
                                      serviceName=self.serviceName,
                                      publishedName=self.publishedName,
                                      version=self.profile['version'])
        
        if self.workersRequired == self.launchPending == 0:
            self.done()
        
    def done(self):
        """ Close up the private callback channel; we're done. Called once the launch
requirements of the service have been met."""
        self.logger.info("Service %s successfuly launched. " % self.publishedName)
        self.dispatcher.deregister(self)
        

class ServiceLibrary(PelotonConfigObj):
    """ Extension of PelotonProfile to be a service library with
handy utility methods. """
    def __init__(self, *args, **kwargs):
        PelotonConfigObj.__init__(self, *args, **kwargs)
        self.__transformCache = {}
        
    def setProfile(self, version, launchTime, profile):
        """ Sets the profile into the tree. Version will have dots which
need converting to underscore otherwise the tree will have branches
for each of major, minor and patch number. This would be OK but I think
it will be more convenient to have version stored at one level in its
entirety.
"""
        outputTransforms = {}
        self.setpath("lastversion.%s" % (profile['publishedName']), profile)
        self.__transformCache["lastversion.%s" % profile['publishedName']] = outputTransforms
        self.__transformCache["lastversion.%s" % profile['publishedName']] = outputTransforms
        version = version.replace('.','_')
        
        # evaluate some of the stringified entries
        for method in profile['methods'].keys():
            profile['methods'][method]['properties'] = \
                eval(profile['methods'][method]['properties'])

        self.setpath("%s.%s.%s" % 
                     (profile['publishedName'], version, str(launchTime)), profile)
        self.__transformCache["%s.%s.%s" % (profile['publishedName'], version, str(launchTime))] = outputTransforms
        
    def getLastProfile(self, publishedName):
        """ Return latest version of this profile and any computed 
output transforms as a tupple of (profile, transforms). """
        transforms = self.__transformCache["lastversion.%s" % publishedName]
        return self.getpath("lastversion.%s" % publishedName), transforms

    def getProfile(self, publishedName, version, launchTime=None):
        """ Return the specified profile and output transforms dict; if 
launchTime is not specified return the last one entered. """
        version = version.replace('.','_')
        transforms = "%s.%s.%s" % (publishedName, version, str(launchTime))
        if launchTime:
            return self.getpath("%s.%s.%s" % (publishedName, version, str(launchTime))), transforms
        else:
            times = self.getpath("%s.%s"%(publishedName, version))
            lts = times.keys()
            lts.sort()
            return times[lts[-1]]

    def __repr__(self):
        return("ServiceLibrary(%s)" % str(self) )

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

    def __init__(self, kernel):
        self.kernel = kernel
        self.logger = kernel.logger
        self.dispatcher = kernel.dispatcher
        self.pscs=[]
        self.pscByService={}
        self.pscByGUID={}

        self.addPSC(kernel.profile)
        self._setHandlers()
    
    def notifyConnect(self):
        """ Call to publish our own profile over the bus """
        self.dispatcher.fireEvent(key="psc.presence", 
                                exchange="domain_control", 
                                action='connect',
                                myDomainCookie=self.kernel.domainCookie,
                                profile=repr(self.kernel.profile),
                                serviceList=self.kernel.routingTable.shortServiceList)

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
                                        action='FAIL',
                                        exchange="domain_control",
                                        INVALID_COOKIE = True)
                return

            profile = eval(msg['profile'])            
            if profile['guid'] != msg['sender_guid']:
                self.dispatcher.fireEvent(key="psc.%s.init" % profile['guid'],
                                        action='FAIL',
                                        exchange="domain_control",
                                        GUID_MISMATCH = True)
                return
    
            self.dispatcher.fireEvent(key="psc.%s.init" % profile['guid'],
                                    exchange="domain_control",
                                    action='pscReturn',
                                    profile=repr(self.kernel.profile),
                                    serviceList=self.kernel.routingTable.shortServiceList)

            self.addPSC(profile, msg['serviceList'])
            
        elif msg['action'] == 'disconnect':
            self.kernel.logger.info("Received disconnect from %s" % msg['sender_guid'])
            self.removePSC(msg['sender_guid'])
            
    def respond_initChannel(self, msg, exch, key, ctag):
        self.logger.debug("Init chan cmd %s from node %s" % (msg['action'], msg['sender_guid']))
        if msg['action'] == 'FAIL':
            if msg.has_key("INVALID_COOKIE"):
                self.kernel.logger.error("Cannot join domain: Invalid cookie")
                self.kernel.closedown()
                return
            elif msg.has_key("GUID_MISMATCH"):
                self.kernel.logger.error("Cannot join domain: profile GUID and sender GUID mis-match")
                self.kernel.closedown()
                return
            
        elif msg['action'] == 'pscReturn':
            profile = eval(msg['profile'])
            self.addPSC(profile, msg['serviceList'])
        
        elif msg['action'] == 'requestServiceLibrary':
            sender = msg['sender_guid']
            self.dispatcher.fireEvent('psc.%s.init' % sender,
                                      'domain_control',
                                      action='serviceLibrary',
                                      serviceLibrary=repr(self.kernel.serviceLibrary))
            
        elif msg['action'] == 'serviceLibrary':
            self.kernel.serviceLibrary.merge(eval(msg['serviceLibrary']))
#            self.logger.debug("Service library from %s: %s" % (msg['sender_guid'], str(self.kernel.serviceLibrary)))

    def respond_serviceNotification(self, msg, exch, key, ctag):
        """ Service notifications are sent out when a service is started.
We need to update the routing table. """
        if msg['state'] == 'running':
            self.logger.info("Service %s started on %s" % (msg['publishedName'], msg['sender_guid']))
            self.addHandlerForService(msg['publishedName'], 
                                      guid=msg['sender_guid'])
        elif msg['state'] == 'stopped':
            self.removeHandlerForService(msg['publishedName'], 
                                         guid=msg['sender_guid'])
            self.logger.info("Service %s stopped on %s" % (msg['publishedName'], msg['sender_guid']))
            
    
    def _getProxyForProfile(self, profile):
        """ Return a proxy appropriate for the PSC described by this profile."""

        # first check it's not the local PSC
        if profile['guid'] == self.kernel.guid:
            return LocalPSCProxy
        
        rpcAllowed = profile['rpc']
        # prioritise PB as the RPC mechanism of choice;
        # failing that just skip through the list until one
        # is found that we can handle. This allows the config
        # writer to imply preference in mechanisms whilst disallowing
        # de-prioritisation of PB.
        if 'pb' in rpcAllowed:
            return PSC_PROXIES['pb']
        else:
            for r in rpcAllowed:
                if PSC_PROXIES.has_key(r):
                    return PSC_PROXIES.has_key(r)
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
               MethodEventHandler(self.respond_initChannel),
               "domain_control")
    
        self.dispatcher.register('psc.service.notification', 
                                 MethodEventHandler(self.respond_serviceNotification), 
                                 'domain_control')
        
    def removePSC(self, guid):
        try:
            proxy = self.pscByGUID[guid]
        except KeyError:
            # already removed
            return

        self.logger.info("Removing PSC: %s" % guid)
        proxy.stop()
        
        # iter over services and remove from proxy by service
        # with removeHandlerForService
        for service, handlers in self.pscByService.items():
            while proxy in handlers:
                self.logger.info("Removing PSC %s for service %s" % (guid, service))
                n=len(handlers)
                handlers.remove(proxy)
                        
        del(self.pscByGUID[guid])
        self.pscs.remove(proxy)
    
    def addPSC(self, profile, serviceList=[]):
        """ Store the PSC provided. """
        try:
            clazz = self._getProxyForProfile(profile)
            pscProxy = clazz(self.kernel, profile)
        except Exception, ex:
            self.logger.error("Cannot register PSC (%s) with RPC mechanisms %s : %s" \
                              % (profile['guid'], str(profile['rpc']), str(ex)))                
            raise

        self.kernel.logger.info("Adding profile for node: %s" % profile['guid'])

        # if we have an empty serviceLibrary and there is a service list
        # here, and the __LIBRARY_INITIALISING__ flag isn't set, 
        # ask the node to initialise our service library.
        if not self.kernel.serviceLibrary and serviceList:
            self.dispatcher.fireEvent('psc.%s.init' % profile['guid'],
                                         'domain_control',
                                         action='requestServiceLibrary')
            
        if isinstance(pscProxy, LocalPSCProxy):
            self.localProxy = pscProxy
        self.pscs.append(pscProxy)
        self.pscByGUID[pscProxy.profile['guid']] = pscProxy

        for svc in serviceList:
            self.addHandlerForService(svc, proxy=pscProxy)
     
    def getPscProxyForService(self, service):
        """ Return a PSC Proxy for the named service at random from the
list of available proxies. """
        try:
            proxies = self.pscByService[service]
            np = len(proxies)
            if np == 0:
                del(self.pscByService[service])
                raise KeyError
            ix = random.randrange(np)
            return proxies[ix]
        except KeyError:
            raise NoProvidersError("No Proxy for service %s" % service)

    def removeHandlerForService(self, service, guid=None, proxy=None, removeAll=False):
        """ Remove proxy from the list of proxies available for this 
service. Note that the list of proxies will include multiple references to
the same proxy if more than worker is associated with the PSC referenced.

Remove will remove only one of these which is the correct behaviour as
remove is called once per signal received from a dying worker. 

If you really do want all proxies removed, specify removeAll=True"""
        if guid and not proxy:
            try:
                proxy = self.pscByGUID[guid]
            except KeyError:
                # guess it's already gone!
                return
    
        try:
            proxies = self.pscByService[service]
            if removeAll:
                while proxy in proxies:
                    proxies.remove(proxy)
            else:
                proxies.remove(proxy)
        except ValueError:
            pass
        except KeyError:
            pass

    def addHandlerForService(self, serviceName, guid=None, proxy=None):
        """ Add the handler for the PSC referenced by guid as a handler
for the named service. 

Because one event is fired for every *worker* that is launched by a PSC, the
lists of handlers for each service will contain multiple references to the
same proxy on account of it having n workers to reference at the other end.

This isn't so bad as it naturally introduces an element of weighting. To
ensure that one host doesn't get unduly hit in the event of round robin
routing we insert the new entries into a random point in the list.
"""
        if guid and not proxy:
            proxy = self.pscByGUID[guid]

        if not self.pscByService.has_key(serviceName):
            self.pscByService[serviceName] = []
        handlers = self.pscByService[serviceName]
        
        insertPoint = random.randint(0, len(handlers))
        handlers.insert(insertPoint, proxy)
        
    def _getShortServiceList(self):
        """ Return a list only of service names. """
        return self.kernel.workerStore.keys()
    shortServiceList = property(_getShortServiceList)
            