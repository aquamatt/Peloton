# Copyright 2007 Matthew Pontefract
# See LICENSE for details
""" Decorators for service methods.
"""

def testDecorator(f):
    def _f(self, *args, **kargs):
        print "Called with args: %s, kargs:%s" % (str(args), str(kargs))
        return f(*args, **kargs)
    return _f

