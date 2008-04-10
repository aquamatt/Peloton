"""
Demonstrates error in handling of Failure in Twisted 8.0.1
To demonstrate:

1) Open three terminals.
2) In the first run test_patch_8_0_1.py server
3) In the second run test_patch_8_0_1.py middle
4) In the third run test_patch_8_0_1.py client

In Twisted 2.5 and patched Twisted 8.0.1 the client call
prints out the details of the Failure received.

In un-patched Twisted 8.0.1 an exception is raised in the 
'middle man' console and the client never receives a 
response.
"""
from twisted.python.failure import Failure
from twisted.spread import pb
from twisted.internet.defer import Deferred
from twisted.internet import reactor
from twisted import version

import sys

class MyError(Exception):
    pass

class Server(pb.Root):

    def start(self):
        svr = pb.PBServerFactory(self)
        self.connection = reactor.listenTCP(7654, svr)
        reactor.callWhenRunning(self._running)
        
    def _running(self):
        print("Server started (Twisted %s)" % version)

    def remote_raiseError(self):
        print("About to oops")
        raise MyError("MyError message")

    def remote_raiseFailure(self):
        print("About to oops with failure")
        raise Failure(MyError("MyError message is FAILURE"))
        
class MiddleMan(pb.Root):
    def start(self):
        svr = pb.PBServerFactory(self)
        self.connection = reactor.listenTCP(7655, svr)

        factory = pb.PBClientFactory()
        reactor.connectTCP('localhost', 7654, factory)
        d = factory.getRootObject()
        d.addCallback(self.gotRoot)
        d.addErrback(self.error)
        reactor.callWhenRunning(self._running)
        
    def _running(self):
        print("Middleman started (Twisted %s)" % version)

    def gotRoot(self, root):
        self.root = root
        
    def remote_reflect(self):
        print("Called reflect")
        rd = Deferred()
#        d = self.root.callRemote('raiseError')
        d = self.root.callRemote('raiseFailure')
        rd.addCallback(self.rdCallbackCheck)
        d.addCallback(rd.callback)
        d.addErrback(self.callerror, rd)
        return rd
        
    def rdCallbackCheck(self, v):
        print("RD Callback check... %s " % str(v))
        return v
    
    def callerror(self, err, rd):
        print("Call error %s" % err.getErrorMessage())
        rd.errback(err)
#        rd.callback('yay!')
        
    def error(self, err):
        print("Middle man failed to connect: %s " % err.getErrorMessage())
    
    
class Client(object):
    def start(self):
        factory = pb.PBClientFactory()
        reactor.connectTCP('localhost', 7655, factory)
        d = factory.getRootObject()
        d.addCallback(self.gotRoot)
        d.addErrback(self.error)
    
    def gotRoot(self, rt):
        d=rt.callRemote('reflect')
        d.addCallback(self.done)
        d.addErrback(self.error)
        
    def done(self, a=''):
        print("Done: %s" % str(a))
        reactor.stop()        

    def error(self, err):
        print("\n***********************\nTwisted %s" % version)
#        print dir(err)
        print err.parents
        print err.value
#        print type(err.value)
        err.printTraceback(sys.stdout)
        self.done()
        print("***********************\n")
        
if __name__ == '__main__':
    if sys.argv[1]=='server':
        Server().start()
    elif sys.argv[1]=='middle':
        MiddleMan().start()
    else:
        Client().start()
        
    reactor.run()
