# $Id: kernel.py 108 2008-04-04 15:39:30Z mp $
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
    
  - The forking was leaving the worker processes in a 'strange' state
    that seemed to be causing problems with Twisted that were never
    resolved.
"""

