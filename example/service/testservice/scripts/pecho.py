#!/usr/bin/env python
from twisted.internet import reactor
from twisted.spread import pb
import sys

HOST='localhost' 

def clientConnect(svr, echoText):
    d = svr.callRemote('login', 'blah')
    d.addCallback(gotIface, echoText)
    d.addErrback(error)
    
def gotIface(iface, echoText):
    d = iface.callRemote('call', 'TestService', 'echo', echoText)
    d.addCallback(done)
    d.addErrback(error)        
    
def done(x):
    print("Echo: %s" % x)
    reactor.stop()

def error(err):
    print("Ooooh - error:%s " % err.value)
    reactor.stop()
    
def main(echoText):
    factory = pb.PBClientFactory()
    reactor.connectTCP(HOST, 9100, factory)
    d = factory.getRootObject()
    d.addCallback(clientConnect, echoText)
    d.addErrback(error)
    reactor.run()
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))
