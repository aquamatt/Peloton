# $Id$
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
from peloton.service import PelotonService

class TestService(PelotonService):
    def public_sumint(self, x, y):
        """ Return the sum of integers x and y. """
        self.logger.info("Handling sum of %d and %d" % (x,y))
#        print("Handling sum of %d and %d" % (x,y))
        return int(x) + int(y)
        