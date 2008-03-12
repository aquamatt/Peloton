# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
from twisted.internet.error import CannotListenError

from peloton.plugins import PelotonPlugin
from peloton.coreio import PelotonManagementInterface
from peloton.plugins.sshmanhole import PasswordManhole
from twisted.internet.error import CannotListenError

class PelotonManholePlugin(PelotonPlugin):
    """ Provides an interpreter inside the event loop to which
one can connect by SSH using a pre-specified username/password.

Objects in the namespace of the interpreter provide access to the
mesh and allow administrators to interrogate the mesh and to start and
stop services as well as make other hot-changes.
"""

    def initialise(self):
        namespace={'psc':PelotonManagementInterface(self.kernel)}
        
        self.pmh = PasswordManhole(int(self.config['port']),
                                   self.config['username'],
                                   self.config['password'],
                                   namespace)        
        
    def start(self):
        try:
            self.pmh.startService()
            self.started = True
            self.logger.info("Manhole plugin initialised")
        except CannotListenError:
            raise Exception("Manhole cannot listen on port %d" % self.config['port'])
        
    def _stopped(self, *args, **kargs):
        self.started = False
        self.logger.info("Manhole plugin stopped")
        
    def stop(self):
        self.logger.info("Manhole plugin stopping")
        d = self.pmh.stopService()
        d.addCallback(self._stopped)
