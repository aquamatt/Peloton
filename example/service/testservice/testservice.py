# $Id$
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
from peloton.service import PelotonService
import time

class TestService(PelotonService):
    def public_sumint(self, x, y):
        """ Return the sum of integers x and y. """
        self.logger.info("Handling sum of %d and %d" % (x,y))
#        print("Handling sum of %d and %d" % (x,y))
        return int(x) + int(y)
        
    def public_slowCall(self, x):
        """ Sleep for x seconds. """
        x=int(x)
        time.sleep(x)
        return "Done a slow call"
    
    def public_echo(self, x):
#        raise NotImplementedError("OOOh - not ready")
        return x