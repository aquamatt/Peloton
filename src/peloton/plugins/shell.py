# $Id: shell.py 77 2008-03-18 16:32:47Z mp $
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
from twisted.internet.error import CannotListenError

from peloton.plugins import PelotonPlugin
from peloton.coreio import PelotonManagementInterface
from peloton.plugins.support.sshmanhole import PasswordManhole

class PelotonShell(PelotonPlugin):
    """ Provides an interpreter inside the event loop to which
one can connect by SSH using a pre-specified username/password.

Objects in the namespace of the interpreter provide access to the
mesh and allow administrators to interrogate the mesh and to start and
stop services as well as make other hot-changes.
"""

    def initialise(self):
        # create an interface, pull out all 'public_*' methods
        # into our namespace, striping the prefix
        psc = PelotonManagementInterface(self.kernel)
        publicMethods =  [i for i in dir(psc) if i.startswith('public_')]
        namespace={}
        for m in publicMethods:
            namespace[m[7:]] = getattr(psc, m)

        self.pmh = PasswordManhole(int(self.config.port),
                                   self.config.username,
                                   self.config.password,
                                   namespace)        
        
    def start(self):
        try:
            self.pmh.startService()
            self.logger.info("SSH shell plugin initialised")
        except CannotListenError:
            raise Exception("SSH Shell cannot listen on port %d" % self.config.port)
        
    def _stopped(self, *args, **kargs):
        self.logger.info("SSH shell plugin stopped")
        
    def stop(self):
        self.logger.info("SSH shell plugin stopping")
        d = self.pmh.stopService()
        d.addCallback(self._stopped)
