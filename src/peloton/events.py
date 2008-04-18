# $Id: events.py 91 2008-03-24 00:57:50Z mp $
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
""" Core interface to the event bus. This module also contains
a base class for all event bus plugins. 

The interface may differ and the provider also, but Peloton contrains
the message bus to one that supports the AMQP protocol as defined 
at http://amqp.org/. 

The message format is simple: a pickled dictionary is sent over the bus
with one mandatory key (sender_guid) and an arbitrary number
of arbitrary keys. These are de-pickled before being passed to registered
event handlers.

This module defines three ready-made event handlers of use:

  - The QueueEventHandler extends the Python Queue class. Events
    are received and placed on the queue so that other code can
    simply get() them off as required.
    
  - The MethodEventHandler reflects the call through to another method
    with which it was initialised.
    
  - For debugging, the DebugEventHandler simply dumps the message to the 
    logger with which it was initialised.
"""
from peloton.exceptions import MessagingError

class AbstractEventHandler(object):
    """ Base class for all event handlers. """
    def eventReceived(self, msg, exchange='', key='', ctag=''):
        """ Handle message 'msg'. """
        raise NotImplementedError
    

class EventDispatcher(object):
    """ The event dispatcher is a static component of the Peloton kernel
which performs two roles:

    1. It provides an INTERNEL event routing mechanism for coupling
       components within a kernel. Such events are wholly separate
       from the external messaging bus.
       
    2. It provides an interface to the EXTERNAL event bus provided
       by the plugin which registers itself under the name 'eventbus'.
       
Thus one interface manages all messaging and internal messages are 
completely isolated from the external bus.
"""

    def __init__(self, kernel):
        self.kernel = kernel
        self.eventKeys = {}
        self.handlers={}
        
        # if any calls are made to register prior to 
        # the external bus being connected, we collect the
        # registrations and pump them through once ready.
        self.preInitRegistrations=[]
        self.preInitEvents=[]
        
    def joinExternalBus(self):
        """ Called once the plugins have been loaded. """
        externalBus = self.kernel.plugins['eventbus']
        setattr(self, 'register', externalBus.register)
        setattr(self, 'deregister', externalBus.deregister)
        setattr(self, 'fireEvent', externalBus.fireEvent)
        
        # push through any pre-init registrations
        while self.preInitRegistrations:
            args, kwargs = self.preInitRegistrations.pop(0)
            self.register(*args, **kwargs)
            self.kernel.logger.debug("Pre-init registration for %s " % args[0])

        # push through any pre-init events
        if self.preInitEvents:
            self.kernel.logger.debug("Pre-init events being fired (%d) " % len(self.preInitEvents))
            
        while self.preInitEvents:
            args, kwargs = self.preInitEvents.pop(0)
            self.fireEvent(*args, **kwargs)
        
    def registerInternal(self, key, handler):
        """ Register handler for internal events keyed on 'key'. 
Handler must be an instance of AbstractEventHandler"""
        if not isinstance(handler, AbstractEventHandler):
            raise MessagingError("Internal subscription to %s attempted with invalid handler: %s" % (key, str(handler)))
        try:
            handlers = self.eventKeys[key]
            if handler not in handlers:
                handlers.append(handler)
        except KeyError:
            self.eventKeys[key] = [handler]

        try:
            keys = self.handlers[handler]
            if key not in keys:
                keys.append(key)
        except KeyError:
            self.handlers[handler] = [key]
        
            
    def deregisterInternal(self, handler):
        """ De-register this handler for internal events. """
        eventKeys = self.handlers[handler]
        
        for key in eventKeys:
            self.eventKeys[key].remove(handler)
            # if this was the one and only listener,
            # remove the entry in the keys list
            if not self.eventKeys[key]:
                del(self.eventKeys[key])
                
        del(self.handlers[handler])
    
    def fireInternalEvent(self, key, **kargs):
        """ Fire internal event which is a dictionary composed
of the kwargs of this method. """
        try:
            handlers = self.eventKeys[key]
            for handler in handlers:
                handler.eventReceived(kargs, None, key)
        except KeyError:
            # no-one interested in this event
            pass

    def register(self, *args, **kwargs):
        """ Temporary method that collects calls to register prior to 
the external event bus 'register' being hooked in. """
        self.preInitRegistrations.append((args, kwargs))

    def fireEvent(self, *args, **kwargs):
        """ Temporary method that collects events to be fired as soon
as the external event bus is initialised. """
        self.preInitEvents.append((args, kwargs))

class AbstractEventBusPlugin(object):
    """ Define all methods that the plugins must provide
to be a valid profider for the dispatcher. 
"""
    def register(self, key, handler, exchange):
        """ Register 'handler' for events broadcast on 'exchange'
with routing key/topic 'key'. Handler is an instance of 
peloton.events.AbstractEventHandler.

An implementation of the Event Bus MUST permit a single handler
to be registered for multiple events with multiple calls to register."""
        raise NotImplementedError
    
    def deregister(self, handler):
        """ De-register the specified handler from the event to which it
was bound. """
        raise NotImplementedError

    def fireEvent(self, key, exchange='events', **kargs):
        """ Fire an event on the specified exchange with the 
specified routing key. All other keyword arguments are made
into the event message. """
        raise NotImplementedError

class DebugEventHandler(AbstractEventHandler):
    """ Dump message to the logger with which the handler is initialised. """
    def __init__(self, logger):
        self.logger = logger
        
    def eventReceived(self, msg, exchange='', key='', ctag=''):
        self.logger.info("%s: %s.%s | %s" % (ctag, exchange, key, str(msg)))


class MethodEventHandler(AbstractEventHandler):
    """Initialise with a callable that accepts the
four arguments msg, exchange, key and ctag. This handler
will simply pass the call through. """
    def __init__(self, f):
        self.f = f
        
    def eventReceived(self, msg, exchange='', key='', ctag=''):
        self.f(msg, exchange, key, ctag)
        
from Queue import Queue        
class QueueEventHandler(AbstractEventHandler, Queue):
    """Queue implementation that is a Peloton event handler;
events will be placed on the Queue for subsequent consumption.
All the benefits of queue, all the benefits of an event handler!
Use to handle events asynchronously or as a place from which 
multiple threads can pick events off in turn.
"""
    def __init__(self, *args, **kwargs):
        Queue.__init__(self, *args, **kwargs)
        
    def eventReceived(self, msg, exchange='', key='', ctag=''):
        self.put((msg, exchange, key, ctag))