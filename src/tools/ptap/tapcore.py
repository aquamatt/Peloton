# $Id: pseudomq.py 93 2008-03-25 22:08:27Z mp $
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
""" Core code for Peloton TAP utilities (event viewers). This same
code can be hooked into GUIs or console tools via handler hooks. """

from twisted.internet import reactor
from twisted.spread import pb
from peloton.utils.config import PelotonSettings

class EventHandler(pb.Referenceable):
    def __init__(self, callback):
        self.callback = callback
        
    def remote_eventReceived(self, msg, exchange, key, ctag):
        self.callback(msg, exchange, key, ctag)

class ClosedownListener(pb.Referenceable):
    def __init__(self, tapConnector, callback):
        self.tapConnector = tapConnector
        self.callback = callback
    def remote_eventReceived(self,msg, exchange, key, ctag):
        if msg['action'] == 'disconnect' and \
            msg['sender_guid'] == self.tapConnector.pscProfile['guid']:
                self.callback()

class TAPConnector(object):
    """ State object which hooks into a PSC and relays events
back to the client. Manages re-connecting on disconnect also. 

A user of this class can hook into particular events, providing a callback
method to be fired at appropriate times. The events are:

    - loggedin
    - profileReceived
    - exchangesReceived
"""
    def __init__(self, host, port, username='tap', password='tap'):
        """ self-explanatory arguments. """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.CONNECTED = False
    
        self.callbackNames = ['loggedin', 
                              'disconnected',
                              'masterProfileReceived',
                              'profileReceived',
                              'exchangesReceived']
        
        self.listeners = {}
        for cb in self.callbackNames:
            self.listeners[cb] = []
    
    def start(self):
        self.connect()
        reactor.run()
    
    ## CALLBACK MANAGEMENT
    def addListener(self, callback, handler):
        if callback not in self.callbackNames:
            raise Exception("Invalid callback %s: must be one of %s" \
                            % (callback, str(self.callbackNames)))
        self.listeners[callback].append(handler)
        
    def removeListener(self, callback, handler):
        if handler in self.listeners[callback]:
            self.listeners[callback].remove(handler)
    
    def fireCallback(self, callback, *args):
        for cb in self.listeners[callback]:
            cb(*args)
    # END CALLBACK MANAGEMENT

    def addEventHandler(self, key, exchange, handler):
        handler = EventHandler(handler)
        self.iface.callRemote("register", key, handler, exchange)
        return handler
    
    def removeEventHandler(self, handler):
        self.iface.callRemote("deregister", handler)
    
    def getPSCProfile(self, guid=None):
        d = self.iface.callRemote('getPSCProfile', guid)
        if guid==None:
            upstream=True
        else:
            upstream=False
        d.addCallback(self.__profileReceived, upstream)
        d.addErrback(self.__callError, False)
    
    def connect(self):
        """ Initialise the connection sequence. Reactor must be
started already, or started afterwards. """
        factory = pb.PBClientFactory()
        reactor.connectTCP(self.host, self.port, factory)
        d = factory.getRootObject()
        d.addCallback(self.__connected)
        d.addErrback(self.__connectionError)

    def stop(self):  
        reactor.stop()
    
    def __connected(self, ro):
        self.rootObject = ro
        self.CONNECTED = True
        d = self.rootObject.callRemote('login', self.username)
        d.addCallback(self.__receivedIface)
        d.addErrback(self.__connectionError)
        
    def __receivedIface(self, iface):
        self.iface = iface
        self.fireCallback('loggedin')
        self.getPSCProfile()
        d = self.iface.callRemote('getRegisteredExchanges')
        d.addCallback(self.__exchangesReceived)
        d.addErrback(self.__callError)
        self.closedownHandler = ClosedownListener(self, self.__pscClosedown)
        self.iface.callRemote('register', 'psc.presence', \
                              self.closedownHandler, 'domain_control')
        
    def __profileReceived(self, profile, upstreamPSC=False):
        profile = eval(profile)
        if upstreamPSC:
            self.pscProfile = profile
            self.fireCallback('masterProfileReceived', profile)
        self.fireCallback("profileReceived", profile)
    
    def __exchangesReceived(self, exchanges):
        self.exchanges = exchanges
        self.fireCallback("exchangesReceived", exchanges)
    
    def __pscClosedown(self):
        self.CONNECTED = False
        self.fireCallback("disconnected")
        reactor.callLater(1, self.connect)
    
    def __connectionError(self, err):
        self.CONNECTED = False
        self.fireCallback("disconnected")
        reactor.callLater(1, self.connect)
    
    def __callError(self, err, display=True):
        if display:
            print("Error making call: %s " % str(err))
        
        
        