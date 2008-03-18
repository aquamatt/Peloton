# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
""" AMQP based Event Bus plugin """
from peloton.plugins import PelotonPlugin
from peloton.dispatcher import AbstractEventBusPlugin
import amqplib.client_0_8 as amqp

class AMQPEventBus(PelotonPlugin,AbstractEventBusPlugin):
    """
"""
    def initialise(self):
        self.vhost = self.kernel.config['grid.messagingVHost']
        self.host = self.kernel.config['grid.messagingHost']
    
    def start(self):
        self.amqpconn = amqp.Connection(self.host, 
                                userid=self.config['username'], 
                                password=self.config['password'], 
                                ssl=False, 
                                virtual_host=self.vhost)        
        
        self.coreChannel = self.amqpconn.channel()
        self.coreChannel.access_request('/data/core', active=True, write=True)
        self.coreChannel.exchange_declare('events', 'topic', auto_delete=True)

        self.eventChannel = self.amqpconn.channel()
        self.eventChannel.access_request('/data/event', active=True, write=True)
        self.eventChannel.exchange_declare('events', 'topic', auto_delete=True)

    def stop(self):
        self.amqpconn.close()
    
#    msg = amqp.Message(msg_body, content_type='text/plain', application_headers={'foo': 7, 'bar': 'baz'})
#
#    ch.basic_publish(msg, 'mytopic', routing_key=options.topic)
#    qname, _, _ = ch.queue_declare()
#    ch.queue_bind(qname, 'mytopic', routing_key=options.topic)
#    ch.basic_consume(qname, callback=callback)
    
    