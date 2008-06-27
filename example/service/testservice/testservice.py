# $Id$
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
from peloton.service import PelotonService
from peloton.svcdeco import *
import time
import os

class TestService(PelotonService):
    def start(self):
        self.logger.info("Pelton test service is started. ")
        self.register('testservice.test', self.eventTrap, inThread=False)
        
    def eventTrap(self, msg, exchange, key, ctag):
        self.logger.info("PID %d got message: %s" % (os.getpid(), msg['count']))
        
    def public_startCount(self):
        """ Long-running call; sends 10 counts on the event bus. """
        count = 5
        while count:
            self.fireEvent('testservice.test', 'events', count=count)
            time.sleep(0.5)
            count -= 1
        return ("DONE")
        
    def public_index(self):
        return "Hi! You've got the TestService!"
    
    def public_sumint(self, x, y):
        """ Return the sum of integers x and y. """
        x=int(x)
        y=int(y)
        self.logger.info("Handling sum of %d and %d" % (x,y))
        return x+y
        
    def public_returnList(self, *args):
        return args
    
    @localAudit
    def public_returnDict(self, **kwargs):
        return kwargs
    
    @transform("xml", 
               'stripKeys("interests")', 
               "upperKeys()", 
               "@template")
    def public_returnMixed(self):
        return {'name': 
                 {'first':'Jon',
                  'last' :'Doe'},
                'interests' : ['sailing', 'running', 'jam'],
                'work' : [{'company':'Big Balls', 'position':'bearings maker'},
                          {'company':'Better Balls', 'position':'Junior inflator'}],
                'poolId' : self.settings.poolId,
                }
        
    def public_slowCall(self, x):
        """ Sleep for x seconds. """
        x=int(x)
        time.sleep(x)
        return "Done a slow call"
    
# The following transforms are implicitly applied; if 
# template(...) receives non-dictionary data it applies
# valueToDict automatically.
#    @transform("xml", "valueToDict", "@template")
#    @transform("html", "valueToDict", "@template")
#
# You can change mime type for a particular target output
#    @mimeType('html','text/xhtml')
#
# And you can even add new target types for a method. So now,
# as well as html, xml etc, you can also get the fakeml representation
# of this method response.
#   not that here the valueToDict is applied automaticaly in @template
    @transform("fakeml", "@template")
    @mimeType('fakeml', 'text/xml')
    def public_echo(self, x):
#        raise NotImplementedError("OOOh - not ready")
        return x