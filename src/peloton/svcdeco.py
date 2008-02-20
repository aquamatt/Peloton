##############################################################################
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved.
#
# This software  is licensed under the terms of the BSD license, a copy of
# which should accompany this distribution.
#
##############################################################################

""" Decorators for service methods.
"""

def testDecorator(f):
    def _f(*args, **kargs):
        print "Called with args: %s, kargs:%s" % (str(args), str(kargs))
        return f(*args, **kargs)
    return _f

