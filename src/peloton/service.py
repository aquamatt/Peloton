# Copyright 2007 Matthew Pontefract
# See LICENSE for details
from svcdeco import testDecorator

class PelotonService(object):
    @testDecorator
    def testMethod(self, x):
        return x*x
