# $Id: base.py 108 2008-04-04 15:39:30Z mp $
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
""" Base classes for, e.g., Kernels and Workers 

@todo: Check to see if we need to reset sys.ext and set
       handlers every time - it is most likely that these
       mods are preserved in the fork so shouldn't need to 
       be done in any extension of HandlerBase.
"""
import sys
import peloton.utils.logging as logging
from peloton.utils.config import PelotonSettings
import signal
from twisted.internet import reactor

class HandlerBase(object):
    def __init__(self, settings = {}):
        self.settings = settings
        if settings.has_key('profile'):
            self.profile = profile = settings.profile
        else:
            self.profile = PelotonSettings()
        self.logger = logging.getLogger()
        # hide sys.exit
        self._trapExit()
        # ensure that handlers only installed when things are OK
        reactor.callWhenRunning(self._setSignalHandlers)
        
    def _trapExit(self):
        """ Move sys.exit to sys.realexit and put a dummy
into sys.exit. This prevents service writers from accidentaly
closing a node down."""
        def dummyExit():
            raise Exception("sys.exit disabled to prevent accidental node shutdown.")
        
        sys.realexit = sys.exit
        sys.exit = dummyExit
        
    def _signalClosedown(self, num, frame):
        """ Handle SIGINT/TERM """
        # delay helps ensure things closedown neatly... think
        # the shutdown tramples on event handler code. Not sure.
        # Anyhow... it helps.
        if not self.__CLOSING_DOWN__:
            self.__CLOSING_DOWN__ = True
            reactor.callLater(0.1, self.closedown)
    
    def _signalReload(self, num, frame):
        """ Reaction to a SIGHUP: need to re-start so as to re-load configuration
files etc."""
        raise NotImplementedError("SIGHUP handler not yet written.")
    
    def _setSignalHandlers(self):
        """Set signal traps for INT and TERM to the _signalClosedown method
that tidies up behind itself."""
        self.__CLOSING_DOWN__ = False
        signal.signal(signal.SIGINT, self._signalClosedown)
        signal.signal(signal.SIGTERM, self._signalClosedown)
        signal.signal(signal.SIGHUP, self._signalReload)    
                