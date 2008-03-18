# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
""" AMQP based Event Bus plugin """
from peloton.plugins import PelotonPlugin
from peloton.dispatcher import AbstractEventBusPlugin
import amqplib.client_0_8 as amqp
import threading

class AMQPEventBus(PelotonPlugin,AbstractEventBusPlugin):
    """Uses amqplib to hook into the AMQP event bus, most probably
provided by RabbitMQ but potentially any provider. 

The amqplib is not Twisted based and provides a blocking handler 
for receiving messages off the bus. We thus run the listener
in a thread and put call the message handler in the main thread.
"""
    def initialise(self):
        self.vhost = self.kernel.config['grid.messagingVHost']
        self.host = self.kernel.config['grid.messagingHost']
        self.domain = self.kernel.initOptions.domain
    
    def start(self):
        self.amqpconn = amqp.Connection(self.host, 
                                userid=self.config['username'], 
                                password=self.config['password'], 
                                ssl=False, 
                                virtual_host=self.vhost)        

        self.coreChannel = self.amqpconn.channel()
        self.coreChannel.access_request('/data/core', active=True, write=True)
        self.coreChannel.exchange_declare('myevents', 'topic', auto_delete=True)
        qname, _, _ = self.coreChannel.queue_declare()
        self.coreChannel.queue_bind(qname, 'myevents', routing_key="%s.*"%self.domain)
        self.coreChannel.basic_consume(qname, consumer_tag="coreListener", callback=self._coreCallback)

        self.eventChannel = self.amqpconn.channel()
        self.eventChannel.access_request('/data/event', active=True, write=True)
        self.eventChannel.exchange_declare('myevents', 'topic', auto_delete=True)
        qname, _, _ = self.eventChannel.queue_declare()
        self.eventChannel.queue_bind(qname, 'myevents', routing_key="%s.*"%self.domain)
        self.eventChannel.basic_consume(qname, consumer_tag="eventListener", callback=self._eventCallback)

        mt = threading.Thread(target=self._startCoreListener)
        mt.setDaemon(True)
        mt.start()
    
        mt = threading.Thread(target=self._startEventListener)
        mt.setDaemon(True)
        mt.start()
    
    def _startCoreListener(self):
        try:
            while self.coreChannel.callbacks:
                self.coreChannel.wait()
        except Exception, ex:
            self.logger.error("Exception raised in event listener thread: %s " % str(ex))

    def _startEventListener(self):
        try:
            while self.coreChannel.callbacks:
                self.coreChannel.wait()
        except Exception, ex:
            self.logger.error("Exception raised in event listener thread: %s " % str(ex))

    def _eventCallback(self, msg):
        for key, val in msg.properties.items():
            print '%s: %s' % (key, str(val))
        for key, val in msg.delivery_info.items():
            print '> %s: %s' % (key, str(val))
    
        print ''
        print msg.body
        print '-------'
        msg.channel.basic_ack(msg.delivery_tag)

    def _coreCallback(self, msg):
        for key, val in msg.properties.items():
            print '%s: %s' % (key, str(val))
        for key, val in msg.delivery_info.items():
            print '> %s: %s' % (key, str(val))
    
        print ''
        print msg.body
        print '-------'
        msg.channel.basic_ack(msg.delivery_tag)

    def stop(self):
        self.coreChannel.basic_cancel('coreListener')
        self.eventChannel.basic_cancel('eventListener')
        self.amqpconn.close()
    
#    msg = amqp.Message(msg_body, content_type='text/plain', application_headers={'foo': 7, 'bar': 'baz'})
#
#    ch.basic_publish(msg, 'mytopic', routing_key=options.topic)
#    qname, _, _ = ch.queue_declare()
#    ch.queue_bind(qname, 'mytopic', routing_key=options.topic)
#    ch.basic_consume(qname, callback=callback)
    
    