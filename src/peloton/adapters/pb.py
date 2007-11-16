# Copyright 2007 Matthew Pontefract
# See LICENSE for details
from twisted.spread import pb
from twisted.internet import defer

class PelotonPBAdapter(pb.Root):
    """ The primary client adapter for Peloton is the Python Twisted PB
RPC mechanism. This provides the most complete and sophisticated
interface to the Peloton grid."""
    
    def remote_call(self, clientObj, service, method, *args, **kwargs):
        raise NotImplementedError
    
    def remote_login(self, clientObj):
        """ Login to Peloton. The clientObj contains the credentials to be
used."""
        raise NotImplementedError
    
    def remote_post(self, clientObj, service, method, *args, **kwargs):
        raise NotImplementedError
    
    def remote_postLater(self, sessionId, delay_seconds, service, method, *args, **kwargs):
        raise NotImplementedError

    def remote_postAt(self, sessionId, dateTime, service, method, *args, **kwargs):
        raise NotImplementedError
    
    def remote_fireEvent(self, sessionId, eventChannel, eventName, payload):
        raise NotImplementedError
    
    def remote_subscribeToEvent(self, sessionId, eventChannel, eventName):
        raise NotImplementedError