# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details

""" This plugin module is ONLY for testing and first-stop 
try-before-you-buy. As an MQ provider it does little to ensure
stability, capacity, persistence... in fact it does almost nothing x
that AMQP does, it is simply a call-alike module that allows shallow 
testing.
"""
from peloton.plugins import PelotonPlugin
from peloton.events import AbstractEventBusPlugin
from peloton.events import AbstractEventHandler
from peloton.exceptions import ConfigurationError
from peloton.exceptions import PluginError
from twisted.internet import reactor
from twisted.internet.error import CannotListenError
from twisted.spread import pb
import cPickle as pickle

class PseudoMQ(PelotonPlugin, AbstractEventBusPlugin):
    """ This plugin provides a fake AMQP provider with almost
no facilities of a real provider! Essentially any exchange can be
made and they're all topic exchanges. Everything is held in RAM; there's
no guarantee of anything. It's for testing.

Read again: It's for testing.

One node must be started as a server (config isServer=True) and 
all others must be clients (isServer=False).

The system is run entirely over PB and cannot be used to simulate
messaging between domains. This can only run a single domain.

If it is a server it creates the PseudoMQServer pb.Root object and
publishes on the port specified in config.

If it is a client it creates a PseudoMQClient referenceable, connects
to the server and gets the root object. 

Code can register, de-register and fire events on the plugin
as required by the AbstractEventBusPlugin. There's no guarantee that
this is particularly neat - after a while you may find memory structures
getting large even though you've been de-registering handlers.

When registering, if a client, local exchanges/queues are formed with
the local handler as a recipient. In addition registration is made
on the server with the PseudoMQClient provided as a handler. When an
event is fired on the server it is sent to all its local listeners
and all the remote handlers. The remote clients then pass that to 
the plugin eventReceived which fires it on to all its local handlers.

If a client, a fire event fires the event on the server directly then
the above process takes place.

The PseudoExchange and PseudoQueue classes model exchanges and queues
and just simplify the event firing procedure. PseudoExchange
has to determine which queues to pass the event to based on the 
event key and the queue keys. It has to match based on AMQP pattern
matching rules; this is done with the matchKey method.
"""
    def initialise(self):
        self.isServer = self.config.as_bool('isServer')
        self.host, port = self.config['host'].split(':')
        try:
            self.port = int(port)
        except ValueError:
            raise ConfigurationError("Cannot connect pseudomq to port: %s" % port)
        
        self.exchanges={}
        
    def start(self):
        if self.isServer:
            self.connection = None
            self._startServer()
        else:
            self.connected = False
            self.server=None
            self._startClient()
            self.registrationQueue = []
            self.eventFiringQueue = []
            
    def stop(self):
        if self.isServer and self.connection:
            self.connection.stopListening()
        elif self.server:
            # must find out how to disconnet a client
            pass
    
    def register(self, key, handler, exchange='events'):
#        self.logger.debug("Registration called on %s.%s" % (exchange, key))
        try:
            self.exchanges[exchange].addQueue(key, handler)
        except KeyError:
            self.exchanges[exchange] = PseudoExchange(exchange)
            self.exchanges[exchange].addQueue(key, handler)
            
        if not self.isServer:
            if self.connected:
                self.server.callRemote('register', key, self.clientObj, exchange)
            else:
                self.registrationQueue.append((key, exchange))
                
    def deregister(self, handler):
        for exchange in self.exchanges.values():
            exchange.deregister(handler)
        
    def fireEvent(self, key, exchange='events', **kwargs):
        """ If I'm the server I fire to all my handlers, many
of which will be remote. If I'm a client I call fireEvent on the
server. """
#        self.logger.debug("Fire event on %s.%s" % (exchange, key))
        if 'sender_guid' not in kwargs.keys():
            kwargs.update({'sender_guid' : self.kernel.guid})
        if self.isServer:
            try:
                exchange = self.exchanges[exchange]
                exchange.fireEvent(key, kwargs)
            except KeyError:
                # no registration for this exchange. hey ho.
                pass
        else:
            if self.connected:
                try:
                    self.server.callRemote('fireEvent', key, exchange, pickle.dumps(kwargs))
                except pb.DeadReferenceError:
                    self.connected=False
                    self.logger.error("Message server has gone!")
                    self.eventFiringQueue.append((key, exchange, kwargs))
            else:
                self.eventFiringQueue.append((key, exchange, kwargs))

    def eventReceived(self, msg, exchange, key, ctag=''):
        """ Forward event received from server to locally registered
nodes. """
        msg = pickle.loads(msg)
        try:
            exchange = self.exchanges[exchange]
            exchange.fireEvent(key, msg)
        except KeyError:
            # no registration for this exchange. hey ho.
            pass


    def _startServer(self):
        """ Connect a server PB interface to whatever port
is specified in the config. """
        rootObj = PseudoMQServer(self)
        svr = pb.PBServerFactory(rootObj)
        try:
            self.connection = reactor.listenTCP(self.port, 
                                                svr, 
                                                interface=self.host)
        except CannotListenError:
            raise PluginError("PseudoMQ cannot bind to %s:%s" % (self.host, self.port))
        except Exception:
            self.logger.exception("Error initialising PseudoMQ")

    def _startClient(self):
        """ Get a connection to a PseudoMQ server node. """
        self.clientObj = PseudoMQClient(self)
        factory = pb.PBClientFactory()
        try:
            reactor.connectTCP(self.host, self.port, factory)
            d = factory.getRootObject()
            d.addCallback(self._clientConnect)
            d.addErrback(self._clientConnectError)
        except Exception, ex:
            raise PluginError("Could not connect to PseudoMQ server: %s" % str(ex))
        
    def _clientConnect(self, svr):
        """ Called when root object from PseudoMQ server obtained. """
        self.server = svr
        self._safeQueuePurge()
    
    def _safeQueuePurge(self, *args):
        """ Registrations made prior to the server being
connected are flushed out one at a time (to preserve order). Then,
events remaining to be fired are flushed out one at a time. Then 
we consider ourselves connected. """
        if self.registrationQueue:
            key,exchange = self.registrationQueue.pop()
            d = self.server.callRemote('register', key, 
                                   self.clientObj, exchange)
            d.addCallback(self._safeQueuePurge)
        elif self.eventFiringQueue:
            key, exchange, msg = self.eventFiringQueue.pop()
            d = self.server.callRemote('fireEvent', key, 
                                   exchange, pickle.dumps(msg))        
            d.addCallback(self._safeQueuePurge)
        else:
            self.connected = True
            
    def _clientConnectError(self, err):
        """ Error connecting the client to the server """
        raise PluginError("Could not connect to PseudoMQ server: %s" % str(err))
    
class PseudoMQServer(pb.Root):
    def __init__(self, pseudomq):
        self.pseudomq = pseudomq
        
    def remote_register(self, key, handler, exchange='events'):
        self.pseudomq.register(key, handler, exchange)
    
    def remote_deregister(self, handler):
        self.pseudomq.deregister(handler)
    
    def remote_fireEvent(self, key, exchange='events', msg=''):
        kwargs = pickle.loads(msg)
        self.pseudomq.fireEvent(key, exchange, **kwargs)
    
class PseudoMQClient(pb.Referenceable):
    def __init__(self, pseudomq):
        self.pseudomq = pseudomq
        
    def remote_eventReceived(self, msg, exchange='', key='', ctag=''):
        self.pseudomq.eventReceived(msg, exchange, key, ctag)
        
class PseudoExchange(object):
    """ Model an exchange in a super simplistic way. Allow registration
of listeners to queues and firing of events. """
    def __init__(self, name):
        self.name = name
        self.queues = {}
        
    def addQueue(self, key, handler):
        try:
            self.queues[key].addHandler(handler)
        except KeyError:
            self.queues[key] = PseudoQueue(key)
            self.queues[key].addHandler(handler)
    
    def deregister(self, handler):
        """ De-register handler from all queues to which it
is registered. """
        for queue in self.queues.values():
            queue.removeHandler(handler)
            
    def fireEvent(self, key, msg):
        """ Fire event to all queues whose routing key matches the 
message key according to AMQP pattern matching rules. """
        keys = self.queues.keys()
        matchKeys = [k for k in keys if self.matchKey(k, key)]
        for k in matchKeys:
            self.queues[k].fireEvent(key, self.name, msg)

    def matchKey(self, pattern, key):
        """ Pattern is a topic routing key pattern as defined by
the AMQP specification. Return True if key matches the pattern, 
False otherwise. A pattern is a string of '.' delimited tokens. 
Permitted wildcards are:
        
        - # : matches zero or more tokens
        - * : matches a single token
"""
        patternTokens = pattern.split('.')
        keyTokens = key.split('.')
        return self._matchKey(patternTokens, keyTokens)
    
    def _matchKey(self, pt, kt):
        """ Recursive matching method. """
        if pt==[] and kt==[]:
            return True
        elif pt==[]:
            # there's no more pattern but there remain keytokens 
            # un-matched.
            return False
        
        if pt[0] == '#':
            # peek at next pattern value and scroll forward in
            # key tokens until found
            if len(pt) > 1:
                peek = pt[1]
            else:
                # we're at the last element in pattern and it's a
                # hash so whatever is remaining in the key tokens,
                # it's OK - we have a match
                return True
            
            # find the first match of the next token in key space,
            # then match on the rest of the key tokens. If no match,
            # seek another match on the peeked token (this allows for 
            # a.#.b.c to match a.x.x.b.x.x.b.c
            startPos = 0
            while True:
                try:
                    targetPos = kt[startPos:].index(peek)
                    match = self._matchKey(pt[1:], kt[startPos+targetPos:])
                    if match:
                        return True
                    elif startPos+targetPos+1 == len(kt):
                        # no more places to try match
                        return False
                    else:
                        startPos += targetPos+1
                except ValueError:
                    # the key tokens do not contain the next token
                    # in the pattern
                    return False
            
        elif pt[0] == '*':
            if not kt:
                return False
            else:
                return self._matchKey(pt[1:], kt[1:])

        elif (pt and kt) and (pt[0] == kt[0]):
            return self._matchKey(pt[1:], kt[1:])
        
        else:
            return False
    
class PseudoQueue(object):
    def __init__(self, key):
        self.key = key
        self.handlers = []
        
    def addHandler(self, handler):
        self.handlers.append(handler)
        
    def removeHandler(self, handler):
        try:
            self.handlers.remove(handler)
        except ValueError:
            # value not in list. Hey ho
            pass
    
    def fireEvent(self, key, exchange, message):
        msgPickle = pickle.dumps(message)
        deadHandlers = []
        for h in self.handlers:
            if isinstance(h, AbstractEventHandler):
                h.eventReceived(message, exchange, key, '')
            else:
                try:
                    h.callRemote('eventReceived', msgPickle, exchange, key, '')
                except pb.DeadReferenceError:
                    deadHandlers.append(h)
                    
        for h in deadHandlers:
            self.handlers.remove(h)
        
        