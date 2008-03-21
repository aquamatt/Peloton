# $Id$
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

class AbstractEventBusPlugin(object):
    """ Define all methods that the plugins must provide
to be a valid profider for the dispatcher. """
    def register(self, key, handler, exchange):
        """ Register 'handler' for events broadcast on 'exchange'
with routing key/topic 'key'. Handler is an instance of 
peloton.events.AbstractEventHandler."""
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

class AbstractEventHandler(object):
    """ Base class for all event handlers. """
    def eventReceived(self, msg, exchange='', routing_key='', ctag=''):
        """ Handle message 'msg'. """
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