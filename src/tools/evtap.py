#!/usr/bin/python
# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
""" Quick and dirty tool for tapping into the event bus and dumping events
posted to a given exchange and key. Key may be specified as a pattern in AMQP
format.
"""
from twisted.internet import reactor
from twisted.spread import pb
from peloton.utils.structs import FilteredOptionParser
import sys

VERSION = "0.1.0"

class EventHandler(pb.Referenceable):
    def remote_eventReceived(self, msg, exchange, key, ctag):
        print("\n:: %s | %s" % (exchange, key))
        for k,v in msg.items():
            print("%s \t: %s" % (str(k), str(v)))
            
handler = EventHandler()

def clientConnect(svr, options):
    d = svr.callRemote('login', 'blah')
    d.addCallback(gotIface, options)
    d.addErrback(error, None, options)
    
def registered(_):
    print("Registered and listening. ")
    
def gotIface(iface, options):
    d = iface.callRemote('register', options.key, handler, options.exchange)
    d.addCallback(registered)
    d.addErrback(error, iface, options)        
    
def error(err, iface, options):
    print("Error:%s " % err.value)
    err.printTraceback(sys.stdout)
    if iface:
        iface.callRemote('deregister', handler).addBoth(stop)
    else:
        stop(0)

def stop(_):
    reactor.stop()
    
def main():
    usage = "usage: %prog [options]" 
    parser = FilteredOptionParser(usage=usage, version="EVTAP version %s" % VERSION)

    parser.add_option("--host","-H",
                     help="Host for PSC to contact [default %default]",
                     default="localhost")
    parser.add_option("--key", "-k",
                      help="""Message key - may include the wildcards 
 # (match zero or more tokens) or * (match a single token) as defined in the
 AMQP specification [default %default]""",
                      default="#")

    parser.add_option("--exchange", "-x",
                      help="Exchange [default %default]",
                      default="events")

    options, args = parser.parse_args()
    
    
    factory = pb.PBClientFactory()
    reactor.connectTCP(options.host, 9100, factory)
    d = factory.getRootObject()
    d.addCallback(clientConnect, options)
    d.addErrback(error, None, options)
    reactor.run()
    return 0

if __name__ == '__main__':
    sys.exit(main())
