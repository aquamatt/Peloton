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
from peloton.utils.structs import FilteredOptionParser
import tapcore
import sys
import time
import math

VERSION = "0.1.0"

disconnectedTime = 0
tapConn = None
options = None
profiles = {}

def eventReceived(msg, exchange, key, ctag):
    if not profiles.has_key(msg['sender_guid']):
        tapConn.getPSCProfile(msg['sender_guid'])
        
    if key=='psc.logging' and exchange=='logging':
        # automatically detect log entries and format accordingly
        try:
            if profiles.has_key(msg['sender_guid']):
                p = profiles[msg['sender_guid']]
                host = p['hostname']
                dix = host.find('.')
                if dix > 0:
                    host = host[:dix]
                msg['__source'] = "%s:%s" % (host, p['port'])
            else:
                msg['__source'] = '???'
            created = float(msg['created'])
            t = time.localtime(created)
            millis = int(math.modf(created)[0]*1000.0)
            msg['time'] = "%s.%03d" % (time.strftime('%H:%M:%S', t), millis)
            print("""%(time)s %(__source)s : %(levelname)s [%(name)s] %(message)s""" % msg)
        except Exception, ex:
            print "Error: " + str(ex)
        
    else:
        print("\n:: %s | %s" % (exchange, key))
        for k,v in msg.items():
            print("%s \t: %s" % (str(k), str(v)))

def tapConnected():
    global disconnectedTime
    if disconnectedTime > 0:
        print("Re-connected after %ds" % disconnectedTime)
        disconnectedTime = 0
    else:
        print("Connected!")
    
def setProfile(profile):
    global profiles
    profiles[profile['guid']] = profile

def setMasterProfile(profile):
    setProfile(profile)
    tapConn.addEventHandler(options.key, options.exchange, eventReceived)

def disconnected():
    global disconnectedTime
    if disconnectedTime == 0:
        print("DISCONNECTED -- attempting reconnect")
    disconnectedTime += 1
    
def main():
    global tapConn, options
    usage = "usage: %prog [options]" 
    parser = FilteredOptionParser(usage=usage, version="EVTAP version %s" % VERSION)

    parser.add_option("--host","-H",
                     help="Host for PSC to contact [default %default]",
                     default="localhost")
    parser.add_option("--key", "-k",
                      help="""Message key - may include the wildcards 
 # (match zero or more tokens) or * (match a single token) as defined in the
 AMQP specification [default %default]""",
                      default="psc.logging")
    parser.add_option("--port", "-p",
                      help="Port on which to connect [default %default]",
                      default = "9100")

    parser.add_option("--exchange", "-x",
                      help="Exchange [default %default]",
                      default="logging")

    options, args = parser.parse_args()
    
    tapConn = tapcore.TAPConnector(options.host, int(options.port), 'tap', 'tap')
    tapConn.addListener("loggedin", tapConnected)
    tapConn.addListener("profileReceived", setProfile)
    tapConn.addListener("masterProfileReceived", setMasterProfile)
    tapConn.addListener("disconnected", disconnected)
    tapConn.start()
    return 0

if __name__ == '__main__':
    sys.exit(main())
