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

