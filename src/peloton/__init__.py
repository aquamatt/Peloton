# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details

"""Peloton is a distributed SOA platform targeting users with dynamic
environments and a need for robust distributed computing.

As well as providing typical SOA services via common protocols, it also
provides a sturdy web application platform and the means to implement
any number of non-standard protocols to facilitate working with legacy
software.

The Peloton homepage is at U{http://www.peloton-grid.net}

The main aims of this project are to:

    - Create a robust, distributed SOA platform
    - Provide a Python HA platform for commercial use
    - Integrate with legacy systems
    - Make trivial the development and sharing of code 
"""
import os

RELEASE_VERSION = '0.0.1'
BUILD_REVISION  = '$Revision: 52 $'.split(' ')[1]

def getPlatformDefaultDir(dir):
    """ Return the default temporary directory for this platform. Argument
is one of ['temp', 'config'] """
    posix_dirs = {'temp':'/tmp',
                  'config':'/etc/peloton'}
    if os.name in ['posix', 'mac']:
        return posix_dirs[dir] 
    else:
        raise RuntimeError("Sorry: your platform (%s) is not yet supported by Peloton" % os.name)

def getPlatformPSC():
    """ Return the appropriate PSC implementation for this platform """
    if os.name in ['posix', 'mac']:
        import peloton.psc_posix as pscplatform
        return pscplatform
    else:
        raise RuntimeError("Sorry: your platform (%s) is not yet supported by Peloton" % os.name)
    
