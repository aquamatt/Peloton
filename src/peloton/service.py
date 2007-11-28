# Copyright 2007 Matthew Pontefract
# See LICENSE for details
from svcdeco import testDecorator

class PelotonService(object):
    @testDecorator
    def testMethod(self, x):
        return x*x
    
if __name__ == '__main__':
    o = PelotonService()
    print("""
One would like to have decorators in svcdeco and then be 
able to apply them genericaly to any method of any class but this fails. 
To demonstrate, PelotonService currently has one method, testMethod, 
which returns the square of a value passed (meaningless - demonstrates 
this problem).

When decorated with the testDecorator which simply prints calling 
details to the console one would like to see the output of testDecorator 
and get the return value.

However, running this code errors as follows:

    """)
    print o.testMethod(2)