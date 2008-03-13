# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
""" Core classes referenced by adapters to perform Peloton tasks. No
adapter provides services that are other than published interfaces
to methods in these classes."""

import logging

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
        raise NotImplementedError
    
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

    def public_relayCall(self, callerSessionId, callerProtocol, service, method, *args, **kwargs):
        """ Called by a remote node to relay a method request to this node. """
        raise NotImplementedError
    
    def public_getProfile(self):
        """ Return this nodes profile data. """
        raise NotImplementedError
    
    def public_getServiceListing(self):
        """ Return catalogue of services available on this node. """
        raise NotImplementedError
    
    def public_getPublicKey(self):
        """ Return this node's public key """
        raise NotImplementedError
    
class PelotonManagementInterface(PelotonInterface):
    """ Methods for use by management tools, such as a console, 
the SSH Manhole or similar. All methods prefixed public_ are available 
for use in such tools."""

    def public_shutdown(self):
        self.__kernel__.closedown()
        
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
        print self.__kernel__.profile
        
