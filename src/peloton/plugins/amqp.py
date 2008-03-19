# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
""" AMQP based Event Bus plugin """
from peloton.plugins import PelotonPlugin
from peloton.events import AbstractEventBusPlugin
from peloton.events import AbstractEventHandler
from peloton.exceptions import MessagingError
from twisted.internet import reactor
from twisted.internet import task
from twisted.internet.defer import DeferredQueue

import amqplib.client_0_8 as amqp
import threading
import sys
import time

class DebugEventHandler(AbstractEventHandler):
    def eventReceived(self, msg):
        from cStringIO import StringIO
        s = StringIO()
        for key, val in msg.properties.items():
            s.write('%s: %s\n' % (key, str(val)))
        for key, val in msg.delivery_info.items():
            s.write('> %s: %s\n' % (key, str(val)))

        s.write('\n')
        s.writelines(msg.body)
        s.write('\n')
        print(s.getvalue())

class AMQPEventBus(PelotonPlugin,AbstractEventBusPlugin):
    """Uses amqplib to hook into the AMQP event bus, most probably
provided by RabbitMQ but potentially any provider. 

The amqplib is not Twisted based and provides a blocking handler 
for receiving messages off the bus. We thus run the listener
in a thread and put call the message handler in the main thread. For
this to work we also require two connections: one for read and one
for write. As the topic exchange does not as far as I know allow
for negative patterns (specifying fields NOT to occur) we have to 
filter on guid once the message has arrived... I'm sure we can
sort this out in future iterations.
"""
    def initialise(self):
        self.vhost = self.kernel.config['grid.messagingVHost']
        self.host = self.kernel.config['grid.messagingHost']
        self.realm = self.kernel.config['grid.messagingRealm']
        self.domain = self.kernel.initOptions.domain
        self.node_guid = self.kernel.profile['guid']
        
        # key is ctag; value is handler object
        self.handlersByCtag = {}
        # key is <exchange>.<routing_key>; value is ctag
        self.ctagByQueue = {} 
        # key is handler, value is (exchange, routing_key, ctag)
        self.registeredHandlers = {}
        
        self.mqueue = DeferredQueue()        
        self.mqueue.get().addCallback(self._processQueue)    

    def start(self):
        self.connectionIn = amqp.Connection(self.host, 
                                userid=self.config['username'], 
                                password=self.config['password'], 
                                ssl=False, 
                                virtual_host=self.vhost)        

        self.connectionOut = amqp.Connection(self.host, 
                                userid=self.config['username'], 
                                password=self.config['password'], 
                                ssl=False, 
                                virtual_host=self.vhost)        

        exchanges = [('domain_control','topic'),
                     ('logging', 'topic'),
                     ('events', 'topic')]

        self.channelIn = self.connectionIn.channel()
        self.channelIn.access_request(self.realm, active=True, read=True)
        for x,t in exchanges:
            self.channelIn.exchange_declare(x, t, auto_delete=True)

        self.channelOut = self.connectionOut.channel()
        self.channelOut.access_request(self.realm, active=True, write=True)

        self.register("test.matthew.#", DebugEventHandler(), 'events')

        mt = threading.Thread(target=self._startListener)
        mt.setDaemon(True)
        mt.start()
        
#        reactor.callLater(5, self.test)

    def test(self):
        print("Starting test")
        reactor.callLater(5, self.test2)
        try:
            print("Register")
            self.register("test.#", DebugEventHandler(), 'events')
            print("Done")
            sys.stdout.flush()
            task.LoopingCall(self.tick).start(1)
        except Exception, ex:
            print str(ex)
            sys.stdout.flush()
            

    def test2(self):
        print("Test 2")
        sys.stdout.flush()
        self.register("manky.skanky.#", DebugEventHandler(), 'events')

    def tick(self):
        print("Tick")
        msg="Tick tock"
        ch = self.channelOut
        msg = amqp.Message(msg, content_type='text/plain', application_headers={'nodeguid':self.node_guid})
        ch.basic_publish(msg, 'events', routing_key='pelotonica.test.time')

    def register(self, key, handler, exchange='events'):
        """ Register to receive events from the specified exchange (default 'events')
with all messages to be handled by a peloton.events.AbstractEventHandler instance."""

        if not isinstance(handler, AbstractEventHandler):
            raise MessagingError("Subscription to %s.%s attempted with invalid handler: %s" % (exchange, key, str(handler)))
        key = "%s.%s" % (self.domain, key)
        queue = "%s.%s" % (exchange,key)
            
        if not self.ctagByQueue.has_key(queue):
            qname, _, _ = self.channelIn.queue_declare()
            self.channelIn.queue_bind(qname, exchange, routing_key=key)
            ctag = self.channelIn.basic_consume(qname, callback=self._callback)
            self.ctagByQueue[queue] = (ctag, qname)
        else:
            ctag, qname = self.ctagByQueue[queue]
        
        self.registeredHandlers[handler] = (exchange, key, ctag, qname)

        try:
            self.handlersByCtag[ctag].append(handler)
        except:
            self.handlersByCtag[ctag] = [handler]
        
        
    def deregister(self, handler):
        """ Remove this handler from all listened for queues """
        _, _, ctag, qname = self.registeredHandlers[handler]
        self.handlersByCtag[ctag].remove(handler)
        del(self.registeredHandlers[handler])
        if not self.handlersByCtag[ctag]:
            self.channelIn.queue_delete(qname)
            del(self.handlersByCtag[ctag])
            
    def _startListener(self):
        try:
            while True:
                self.channelIn.wait()
        except Exception, ex:
            self.logger.error("Exception raised in event listener thread: %s " % str(ex))

    def _callback(self, msg):
        if msg.properties['application_headers'].has_key('nodeguid') and \
            msg.properties['application_headers']['nodeguid'] == self.node_guid:
            msg.channel.basic_ack(msg.delivery_tag)
            return
        reactor.callFromThread(self.mqueue.put, msg)
        msg.channel.basic_ack(msg.delivery_tag)

    def _processQueue(self, msg):
        """ Find all handlers for this message based on exchange and queue and
pass the message to them. """
        self.mqueue.get().addCallback(self._processQueue)
        ctag = msg.delivery_info['consumer_tag']

        for handler in self.handlersByCtag[ctag]:
            handler.eventReceived(msg)

    def stop(self):
        self.channelOut.close()
        self.connectionOut.close()
        self.logger.info("@todo: Work out how to stop event bus IN-bound cleanly")
    
    
    