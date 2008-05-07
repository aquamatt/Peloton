# $Id: pwp.py 122 2008-04-11 08:22:28Z mp $
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
""" The PWP (Peloton Worker Process) is spawned by the PSC to
run a service worker. 

Originaly workers were spawned by forking but this has a couple of 
disadvantages:

  - It's not compatible with non-POSIX systems, notably a certain
    well known platform.
    
  - The forking seemed to leave the worker processes in a 'strange' 
    state that may have caused problems with Twisted that were 
    never resolved.
"""
import sys
from peloton.worker import PelotonWorker
from peloton.utils import chop

def main():
    """ Steps to start:
    1. Obtain host, port from args
    2. Obtain token from stdin
    3. Call in and get service name, logdir (if any), launchTime etc
    4. Startup
"""
    host, port = sys.argv[1:3]
    port=int(port)
    token = chop(sys.stdin.readline())
    worker = PelotonWorker(host, port, token)
    return worker.start()
    
if __name__ == '__main__':
    sys.exit(main())
