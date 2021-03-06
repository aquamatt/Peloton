# $Id: amqpQpid.py 93 2008-03-25 22:08:27Z mp $
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

class AMQPEventBus(PelotonPlugin,AbstractEventBusPlugin):
    """Uses Python-QPID to hook into the AMQP event bus, most probably
provided by RabbitMQ but potentially any provider. 

The QPID is not Twisted based and provides a blocking handler 
for receiving messages off the bus. 

This plugin needs to be superceded by one based on a Twisted AMQP 
protocol handler for greater efficiency in this environment. As it
stands one thread is used per routing_key being listened for and in
the event that subscribers do not de-register, threads will be consumed
at an un-wholesome rate.

@todo - purging of threads with no real listeners behind them?
"""
    def initialise(self):
        self.vhost = self.kernel.settings.messagingVHost
        self.host = self.kernel.settings.messagingHost
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
        self.realm = self.kernel.settings.messagingRealm
        
        self.domain = self.kernel.settings.domain
        self.node_guid = self.kernel.profile.guid
        
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

        self.connection.start({ 'LOGIN': self.config.username, 
                      'PASSWORD': self.config.password}) 


        exchanges = [('domain_control','topic'),
                     ('logging', 'topic'),
                     ('events', 'topic')]

        self.registeredExchanges = []

        self.mqueue = DeferredQueue()        
        self.mqueue.get().addCallback(self._processQueue)    
        
        self.channel = self.connection.channel(1)
        self.channel.channel_open()
        for x,t in exchanges:
            self.channel.exchange_declare(exchange=x, type=t, auto_delete=False)
            self.registeredExchanges.append(x)
            
    def stop(self):
        for _, _, q in self.ctagByQueue.values():
            try:
                q.close()
            except:
                pass

    def register(self, key, handler, exchange='events'):
        """ Register to receive events from the specified exchange (default 'events')
with all messages to be handled by a peloton.events.AbstractEventHandler instance."""
        if exchange not in self.registeredExchanges:
            raise MessagingError("Exchange %s not valid" % exchange)
        if not isinstance(handler, AbstractEventHandler):
            raise MessagingError("Subscription to %s.%s attempted with invalid handler: %s" % (exchange, key, str(handler)))
        key = "%s.%s" % (self.domain, key)
        queue = "%s.%s" % (exchange,key)
        if not self.ctagByQueue.has_key(queue):
            try:
                qname, _, _ = self.channel.queue_declare(exclusive=True).fields
                self.channel.queue_bind(queue=qname, exchange=exchange, routing_key=key)
                ctag = self.channel.basic_consume(queue=qname, no_ack=True).consumer_tag
                q = self.connection.queue(ctag)
                self.ctagByQueue[queue] = (ctag, qname, q)
                self._startListener(ctag, q)
            except Exception:
                self.logger.error("Message published to closed exchange: %s/%s " % (exchange, key))
                raise MessagingError("Message published to closed exchange: %s/%s " % (exchange, key))
        else:
            ctag, qname, _ = self.ctagByQueue[queue]

        record = (exchange, key, ctag, qname)
        try:
            queues = self.registeredHandlers[handler]
            if record not in queues:
                queues.append(record)
        except KeyError:
            self.registeredHandlers[handler]=[record]

        try:
            handlers = self.handlersByCtag[ctag]
            if handler not in handlers:
                handlers.append(handler)
        except Exception, ex:
            self.handlersByCtag[ctag] = [handler]
        
        
    def deregister(self, handler):
        """ Remove this handler from all listened for queues """
        for exchange, key, ctag, qname in self.registeredHandlers[handler]:
            queue = "%s.%s" % (exchange,key)
            self.handlersByCtag[ctag].remove(handler)
            if not self.handlersByCtag[ctag]:
#                self.channel.queue_delete(queue=qname)
                del(self.handlersByCtag[ctag])
                _, _, q = self.ctagByQueue[queue]
                q.close()
                del(self.ctagByQueue[queue])

        del(self.registeredHandlers[handler])

    def fireEvent(self, key, exchange='events', **kwargs):
        """ Fire an event with routing key 'key' on the specified
exchange using kwargs to build the event message. """
        if exchange not in self.registeredExchanges:
            raise MessagingError("Exchange %s not valid" % exchange)
        kwargs.update({'sender_guid' : self.node_guid})
        msg = Content(pickle.dumps(kwargs))
        try:
            self.channel.basic_publish(content=msg, exchange=exchange, 
                         routing_key='%s.%s' % (self.domain, key))
        except Exception:
            self.logger.error("Message published to closed exchange: %s/%s " % (exchange, key))
            raise MessagingError("Message published to closed exchange: %s/%s " % (exchange, key))
        
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
                except:
                    self.logger.error("Qlistener forced close on %s" % ctag)
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
        # remove the domain name from the key
        routing_key = '.'.join(routing_key.split('.')[1:])
        content = pickle.loads(msg.content.body)
        if self.handlersByCtag.has_key(ctag):
            # may have been deleted already.
            handlersToGo = []
            for handler in self.handlersByCtag[ctag]:
                try:
                    handler.eventReceived(content, exchange=exchange, 
                                      key=routing_key, ctag=ctag)
                except:
                    # error in handler; remove it:
                    self.logger.debug("Defunct error handler: removing.")
                    handlersToGo.append(handler)

            for h in handlersToGo:
                self.deregister(h)
    
    def getRegisteredExchanges(self):
        return self.registeredExchanges
