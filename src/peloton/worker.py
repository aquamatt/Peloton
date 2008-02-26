# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details

from twisted.internet import reactor
from peloton.base import HandlerBase

class PelotonWorker(HandlerBase):
    """ A Peloton Worker manages services, executes methods and returns
results to its controling PSC. """

    def __init__(self, pscHost, pscPort, options, args):
        """ The parent PSC is found at pscHost:pscPort - the host
will in general be the host on which this worker resides but we
allow for other scenarios by passing the host through at this point.

options and args are the options and args passed into the application
from the command line.
"""
        HandlerBase.__init__(self, options, args)
        self.pscHost = pscHost
        self.pscPort = pscPort
    
    def start():
        """ Start this worker; returns an exit code when worker closes down. """
        return 0
    
    def closedown(self):
        reactor.stop() 