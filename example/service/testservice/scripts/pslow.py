#!/usr/bin/env python
from twisted.internet import reactor
from twisted.spread import pb
import sys

HOST='localhost' 

def clientConnect(svr, delay):
    d = svr.callRemote('login', 'blah')
    d.addCallback(gotIface, delay)
    d.addErrback(error)
    
def gotIface(iface, delay):
    d = iface.callRemote('call', 'TestService', 'slowCall', delay)
    d.addCallback(done)
    d.addErrback(error)        
    
def done(x):
    print(x)
    reactor.stop()

def error(err):
    print("Ooooh - error:%s " % err.value)
    reactor.stop()
    
def main(delay):
    factory = pb.PBClientFactory()
    reactor.connectTCP(HOST, 9100, factory)
    d = factory.getRootObject()
    d.addCallback(clientConnect, int(delay))
    d.addErrback(error)
    reactor.run()
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))
