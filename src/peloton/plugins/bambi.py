# $Id: bambi.py 86 2008-03-21 12:43:24Z mp $
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details

""" This plugin module is ONLY for testing - developers
can insert any old rubbish here to test new kernel wotsits.
"""
from peloton.plugins import PelotonPlugin
from twisted.internet import reactor
from twisted.internet.defer import maybeDeferred

class BambiPlugin(PelotonPlugin):
    def initialise(self):
        pass
    
    def start(self):
        if self.kernel.hasFlag('bambisender'):
            reactor.callLater(3, self.send)
        else:
            reactor.callLater(3, self.receive)
            
    
    def stop(self):
        pass
    
    def send(self):
        store = self.kernel.plugins['sessionStore']
        store.set('jolly.good', 'test', 2008)
#        store.set('jolly.good', 'test', 'hello world')
#        store.set('jolly.good','test',[10,20,30])
        store.set('jolly.good', 'hello', 'hello M')
        
    def receive(self):
        store = self.kernel.plugins['sessionStore']
        maybeDeferred(store.get, 'jolly.good', 'test').addCallback(self.printResult)
        maybeDeferred(store.get,'jolly.good', 'hello').addCallback(self.printResult)
        reactor.callLater(3, self.receive)

    def printResult(self, v):
        self.logger.debug("BAMBI smelt %s, type %s" % ( str(v), str(type(v))) )
        
