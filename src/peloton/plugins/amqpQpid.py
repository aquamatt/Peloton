# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
""" AMQP based Event Bus plugin based on the QPID library.  """

from peloton.plugins import PelotonPlugin
from peloton.events import AbstractEventBusPlugin
from peloton.events import AbstractEventHandler
from peloton.exceptions import MessagingError
from peloton.exceptions import ConfigurationError
from twisted.internet import reactor
from twisted.internet import task
from twisted.internet.defer import DeferredQueue

import qpid
from qpid.queue import Closed
from qpid.client import Client
from qpid.content import Content

import cPickle as pickle
import threading
import sys
import os
import time

class DebugEventHandler(AbstractEventHandler):
    def __init__(self, logger):
        self.logger = logger
        
    def eventReceived(self, msg, exchange='', key='', ctag=''):
        self.logger.info("%s: %s.%s | %s" % (ctag, exchange, key, str(msg)))

class AMQPEventBus(PelotonPlugin,AbstractEventBusPlugin):
    """Uses Python-QPID to hook into the AMQP event bus, most probably
provided by RabbitMQ but potentially any provider. 

The QPID is not Twisted based and provides a blocking handler 
for receiving messages off the bus. 
"""
    def initialise(self):
        self.vhost = self.kernel.config['grid.messagingVHost']
        self.host = self.kernel.config['grid.messagingHost']
        hp = self.host.split(':')
        if len(hp) == 1:
            self.port = 5672
        else:
            self.host = hp[0]
            try:
                self.port = int(hp[1])
            except ValueError:
                raise ConfigurationError("Invalid port number for AMQP host: %s " % hp[1])
   
        # NB: THIS HANDLER DOES NOT SUPPORT REALM
        self.realm = self.kernel.config['grid.messagingRealm']
        
        self.domain = self.kernel.initOptions.domain
        self.node_guid = self.kernel.profile['guid']
        
        # key is ctag; value is handler object
        self.handlersByCtag = {}
        # key is <exchange>.<routing_key>; value is ctag
        self.ctagByQueue = {} 
        # key is handler, value is (exchange, routing_key, ctag)
        self.registeredHandlers = {}
        
    def start(self):
        specDir = os.sep.join(qpid.__file__.split('/')[:-2])+"/amqp_specs"
        self.connection = Client(self.host, self.port, 
                        spec=qpid.spec.load('file://%s/amqp0-8.xml' % specDir), 
                        vhost=self.vhost)

        self.connection.start({ 'LOGIN': self.config['username'], 
                      'PASSWORD': self.config['password']}) 


        exchanges = [('domain_control','topic'),
                     ('logging', 'topic'),
                     ('events', 'topic')]

        self.mqueue = DeferredQueue()        
        self.mqueue.get().addCallback(self._processQueue)    
        
        self.channel = self.connection.channel(1)
        self.channel.channel_open()
        for x,t in exchanges:
            self.channel.exchange_declare(exchange=x, type=t, auto_delete=True)

        reactor.callLater(2, self.test)

    def stop(self):
        for _, _, q in self.ctagByQueue.values():
            q.close()

    def test(self):
        self.logger.debug("Starting test")
        self.register("test.matthew.#", DebugEventHandler(self.logger), 'events')
        reactor.callLater(6, self.test2)
        try:
            self.register("test.#", DebugEventHandler(self.logger), 'events')
            task.LoopingCall(self.tick).start(2)
        except Exception, ex:
            self.logger.exceptioN("Error in test")
            sys.stdout.flush()

    def test2(self):
        sys.stdout.flush()
        dh = DebugEventHandler(self.logger)
        self.register("manky.skanky.#", dh, 'events')
        reactor.callLater(4, self.deregister, dh)
        
    def tick(self):
        self.fireEvent('test.matthew.time', 'events', text='tick tock')
        self.fireEvent('manky.skanky.hello', 'events', text='Hello World')

    def register(self, key, handler, exchange='events'):
        """ Register to receive events from the specified exchange (default 'events')
with all messages to be handled by a peloton.events.AbstractEventHandler instance."""

        if not isinstance(handler, AbstractEventHandler):
            raise MessagingError("Subscription to %s.%s attempted with invalid handler: %s" % (exchange, key, str(handler)))
        key = "%s.%s" % (self.domain, key)
        queue = "%s.%s" % (exchange,key)
            
        if not self.ctagByQueue.has_key(queue):
            qname, _, _ = self.channel.queue_declare(exclusive=True).fields
            self.channel.queue_bind(queue=qname, exchange=exchange, routing_key=key)
            ctag = self.channel.basic_consume(queue=qname, no_ack=True).consumer_tag
            q = self.connection.queue(ctag)
            self.ctagByQueue[queue] = (ctag, qname, q)
            self._startListener(ctag, q)
        else:
            ctag, qname, _ = self.ctagByQueue[queue]
        
        self.registeredHandlers[handler] = (exchange, key, ctag, qname)

        try:
            self.handlersByCtag[ctag].append(handler)
        except:
            self.handlersByCtag[ctag] = [handler]
        
        
    def deregister(self, handler):
        """ Remove this handler from all listened for queues """
        exchange, key, ctag, qname = self.registeredHandlers[handler]
        queue = "%s.%s" % (exchange,key)
        self.handlersByCtag[ctag].remove(handler)
        del(self.registeredHandlers[handler])
        if not self.handlersByCtag[ctag]:
            self.channel.queue_delete(queue=qname)
            del(self.handlersByCtag[ctag])
            _, _, q = self.ctagByQueue[queue]
            q.close()

    def fireEvent(self, key, exchange='events', **kwargs):
        """ Fire an event with routing key 'key' on the specified
exchange using kwargs to build the event message. """
        kwargs.update({'sender_guid' : self.node_guid})
        msg = Content(pickle.dumps(kwargs))
        self.channel.basic_publish(content=msg, exchange=exchange, 
                         routing_key='%s.%s' % (self.domain, key))

    def _startListener(self, ctag, q):
        """ Start a thread that listens for messages on a given 
channel. On receipt of a message it is pushed onto self.mqueue for
processing in the main Twisted event loop. """
        def _qListener(mq):
            while True:
                try:
                    v = q.get()
                except Closed:
                    # listener has been stopped
                    break
                except Exception:
                    self.logger("Qlistener forced close on %s" % ctag)
                    break
                
                reactor.callFromThread(mq.put, v)
        mt = threading.Thread(target=_qListener, args=(self.mqueue,))
        mt.setDaemon(True)
        mt.start()

    def _processQueue(self, msg):
        """ Find all handlers for this message based on the consumer tag and
pass the message to them. """
        self.mqueue.get().addCallback(self._processQueue)
        ctag, _, _, exchange, routing_key = msg.fields
        content = pickle.loads(msg.content.body)
        if self.handlersByCtag.has_key(ctag):
            # may have been deleted already.
            for handler in self.handlersByCtag[ctag]:
                handler.eventReceived(content, exchange=exchange, key=routing_key, ctag=ctag)

    
    
