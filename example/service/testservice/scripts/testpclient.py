from twisted.internet import reactor
from twisted.spread import pb
import sys
import time

HOST = 'localhost'
class State(object):pass
state = State()

MAXITER=1000
BATCH=1000
 
def clientConnect(svr):
    d = svr.callRemote('login', 'blah')
    d.addCallback(gotIface)
    d.addErrback(error)
    
def gotIface(iface):
    state.iface = iface
    state.start=time.time()
    state.count=0
    state.outstanding = 0
    state.rsum=0
    loop()
    
def loop(*args):
    if state.count>=MAXITER:
        reactor.callLater(0.1,done)
        return
 
    for i in xrange(BATCH):
        state.outstanding+=1
        d = state.iface.callRemote('call', 'TestService', 'sumint', 1, 2)
        d.addCallback(_answer)
        d.addErrback(error)        
    state.count+=BATCH
    d.addCallback(loop)
    
def done():
    if state.outstanding > 0:
        reactor.callLater(0.01,done)
    else:
        delta = time.time()-state.start
        rate = float(state.count)/delta
        qpm=rate*60.0
        print("%d calls done in  %3.2fs (%3.2f qps - %3.0f qpm) RSUM=%d" % (state.count, delta, rate, qpm, state.rsum))
        reactor.stop()

def _answer(v):
    state.outstanding-=1
    state.rsum+=v
    return v

def error(err):
    state.outstanding-=1
    print "%s" % (err.getErrorMessage())

def main():
    factory = pb.PBClientFactory()
    reactor.connectTCP(HOST, 9100, factory)
    d = factory.getRootObject()
    d.addCallback(clientConnect)
    d.addErrback(error)
    reactor.run()
    return 0

if __name__ == '__main__':
    sys.exit(main())
