# $Id$
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

class HandlerBase(object):
    def __init__(self, options, args):
        self.initOptions = options
        self.initArgs = args

        # hide sys.exit
        self._trapExit()
        self._setSignalHandlers
        
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
        self.closedown()
    
    def _signalReload(self, num, frame):
        """ Reaction to a SIGHUP: need to re-start so as to re-load configuration
files etc."""
        raise NotImplementedError("SIGHUP handler not yet written.")
    
    def _setSignalHandlers(self):
        """Set signal traps for INT and TERM to the _signalClosedown method
that tidies up behind itself."""
        signal.signal(signal.SIGINT, self._signalClosedown)
        signal.signal(signal.SIGTERM, self._signalClosedown)
        signal.signal(signal.SIGHUP, self._signalReload)    
                