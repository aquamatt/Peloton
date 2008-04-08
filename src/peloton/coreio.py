# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
from twisted.internet.error import ConnectionDone
""" Core classes referenced by adapters to perform Peloton tasks. No
adapter provides services that are other than published interfaces
to methods in these classes."""

import peloton.utils.logging as logging
from peloton.exceptions import PelotonError
from twisted.internet.threads import defer
from twisted.internet.error import ConnectionDone
from twisted.python.failure import Failure
from twisted.spread import pb

class PelotonInterface(object):
    """ Subclasses of the PelotonInterface will all need access to
common objects, such as a logger and kernel hooks. These are provided 
through this class. """
    def __init__(self, kernel):
        self.logger = logging.getLogger()
        self.config = kernel.config
        self.__kernel__ = kernel

class PelotonRequestInterface(PelotonInterface):
    """ Methods of this class perform the core actions of Peloton nodes
such as executing a method or posting a request on the execution stack. 
These methods are exposed via adapters. For clarity, although for no other
technical reason, methods intended for use via adapters are named
public_<name> by convention."""

    def public_call(self, sessionId, service, method, *args, **kwargs):
        """ Call a Peloton method in the specified service and return 
a deferred for the result. """
        d =  defer.Deferred()
        self._publicCall(d, sessionId, service, method, *args, **kwargs)
        return d
    
    def _publicCall(self, d, sessionId, service, method, *args, **kwargs):
        while True:
            p = None
            try:
                p = self.__kernel__.routingTable.getPscProxyForService(service)
                rd = p.call(service, method, *args, **kwargs)
                rd.addCallback(d.callback)
                rd.addErrback(self.__callError, d, sessionId, service, method, *args, **kwargs)
                break
            except PelotonError, err:
                self.logger.error(str(err))
                if p:
                    self.__kernel__.routingTable.removePscProxyForService(service, p)
                else:
                    raise

    def __callError(self, err, d, sessionId, service, method, *args, **kwargs):
        if isinstance(err, Failure) and \
            (isinstance(err.value, pb.PBConnectionLost) or \
            isinstance(err.value, ConnectionDone)):
            # try for another handler - perhaps the old one was re-started?
            self.logger.error("Lost a PSC: re-issuing request")
            self._publicCall(d, sessionId, service, method, *args, **kwargs)
        else:
            self.logger.error("Error making request of PSC: %s" % err.getErrorMessage())
            if isinstance(err.value, Exception):
                d.errback(err.value)
            else:
                # came from worker so we've just got the bare details.
                # errback must now take a Failure or Exception as a value;
                # passing in err seems not to work - it doesn't get to client,
                # for reasons unknown to me. So I rebuild the exception.
                try:
                    errClass = err.parents[-1]
                except:
                    errClass = 'Unknown'
                d.errback(Exception(repr([err.value, errClass, err.parents])))
            return err
    
    def public_post(self, sessionId, service, method, *args, **kwargs):
        """ Post a method call onto the stack. The return value is the
grid-unique execution ID for this call. The method will be executed 
when it reaches the head of the call stack."""
        raise NotImplementedError
    
    def public_postLater(self, sessionId, delay_seconds, service, method, *args, **kwargs):
        """ Interface to a scheduled call system. Run the given method after
the specified interval. Return value is the grid-unique execution ID for this
call."""
        raise NotImplementedError
    
    def public_postAt(self, sessionId, dateTime, service, method, *args, **kwargs):
        """ Interface to a scheduled call system. Run the given method at the
specified time. Return value is the grid-unique execution ID for this call."""
        raise NotImplementedError


class PelotonEventInterface(PelotonInterface):
    """ Methods for firing events on and listing to events from the event 
framework.
For clarity, although for no other technical reason, methods intended for use 
via adapters are named public_<name> by convention."""

    def public_fireEvent(self, sessionId, eventChannel, eventName, payload):
        """ Fire an event message onto the grid. """
        raise NotImplementedError
    
    def public_subscribeToEvent(self, sessionId, eventChannel, eventName):
        """ Subscribe to recieve notifications of specified events. """
        raise NotImplementedError


class PelotonNodeInterface(PelotonInterface):
    """ Methods of this class relate to the node itself rather than services. 
For clarity, although for no other technical reason, methods intended for use 
via adapters are named public_<name> by convention."""

    def public_ping(self, value=''):
        """ Return the value sent. A basic node-level ping. """
        return value
    
class PelotonInternodeInterface(PelotonInterface):
    """ Methods for communication between nodes only, for example for relaying method
calls and exchanging status and profile information.
For clarity, although for no other technical reason, methods intended for use 
via adapters are named public_<name> by convention."""

    def public_relayCall(self, sessionId, service, method, *args, **kwargs):
        """ Called by a remote node to relay a method request to this node. 
The method is now executed on this node."""
        p = self.__kernel__.routingTable.localProxy
        return p.call(service, method, *args, **kwargs)
    
class PelotonManagementInterface(PelotonInterface):
    """ Methods for use by management tools, such as a console, 
the SSH terminal or similar. All methods prefixed public_ are available 
for use in such tools."""

    def public_shutdown(self):
#        self.__kernel__.closedown()
        self.__kernel__.domainManager.sendCommand('MESH_CLOSEDOWN')
        
    def public_startPlugin(self, plugin):
        self.__kernel__.startPlugin(plugin)
        
    def public_stopPlugin(self, plugin):
        self.__kernel__.stopPlugin(plugin)
        
    def public_listPlugins(self, verbose=True):
        theList = []
        for name, plugin in self.__kernel__.plugins.items():
            if verbose:
                theList.append( (name, plugin.comment) )
            else:
                theList.append(name)
        return theList
    
    def public_showProfile(self):
        return self.__kernel__.profile
    
    def public_launchService(self, serviceName):
        self.__kernel__.launchService(serviceName)
    
    def public_st(self):
        " Start the test service "
        self.__kernel__.launchService('TestService')
        
    def public_noop(self):
        self.__kernel__.domainManager.sendCommand('NOOP')
        