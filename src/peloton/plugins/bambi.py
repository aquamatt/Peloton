# $Id: bambi.py 86 2008-03-21 12:43:24Z mp $
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details

""" This plugin module is ONLY for testing - developers
can insert any old rubbish here to test new kernel wotsits.
"""
from peloton.plugins import PelotonPlugin
from peloton.events import AbstractEventHandler
from twisted.internet import reactor

class BambiPlugin(PelotonPlugin, AbstractEventHandler):
    def initialise(self):
        pass
    
    def start(self):
        reactor.callWhenRunning(self.kernel.dispatcher.registerInternal, 
                                "testing.testing", self)
        reactor.callWhenRunning(self.kernel.dispatcher.registerInternal, 
                                "something.else", self)
        reactor.callWhenRunning(reactor.callLater, 1, 
                                self.kernel.dispatcher.fireInternalEvent, 
                                "testing.testing", 
                                wally=27)

        reactor.callWhenRunning(reactor.callLater, 2, 
                                self.kernel.dispatcher.fireInternalEvent, 
                                "something.else", 
                                wally=222)
    
    def stop(self):
        pass
    
    def eventReceived(self, msg, x, k):
        if msg['wally'] == 27:
            self.logger.debug("Bambi got %d (%s)" % (msg['wally'], k))
            reactor.callLater(1, self.kernel.dispatcher.fireInternalEvent,
                              "testing.testing",
                              wally = 28)

        elif msg['wally'] == 28:
            self.logger.debug("Bambi got %d (%s)" % (msg['wally'], k))
            self.kernel.dispatcher.deregisterInternal(self)
            reactor.callLater(1, self.kernel.dispatcher.fireInternalEvent,
                              "testing.testing",
                              wally = 29)
            
        elif msg['wally'] == 222:
            self.logger.debug("Bambi got %d (%s)" % (msg['wally'], k))

        elif msg['wally'] == 29:
            self.logger.debug("Got 29 but shouldn't have!")
        
        else:
            self.logger.debug("Oh - what's this? %s " % str(msg))
    
            