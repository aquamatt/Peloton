# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details

""" PSC: Peloton Service Container

The service container is the primary unit in the Peloton mesh. 
PSC units link together to form a mesh; each PSC manages a number
of services.

How those services are managed is dependent on the container; some
may be developed to work in different ways. The default behaviour
for this core PSC will be to spawn a worker process to run a service,
each worker then running a certain number of threads. This allows
us to tune the process vs thread ratio to the strengths of 
different platforms.

A PSC will communicate with other PSCs via Twisted RPC, via RPC 
over message bus or by other protocols to be defined in future.
The acceptable protocols are listed in the PSC signature.

This script is pretty shallow: it simply calls into the appropriate 
platform-specific code for starting a PSC and associated processes
or threads after first processing out command line arguments.
"""

import os
import sys
from optparse import OptionParser, OptionGroup
import peloton

# Determine the appropriate code to use to start a PSC
# on this platform.
# os.name is  'posix', 'nt', 'os2', 'mac', 'ce' or 'riscos'
if os.name in ['posix', 'mac']:
    import peloton.psc_posix as pscplatform
else:
    print("Sorry: your platform (%s) is not yet supported by Peloton" % os.name)
    sys.exit(1)

# Let's read the command line    
usage = "usage: %prog [options]" # add 'arg1 arg2' etc as required
parser = OptionParser(usage=usage, version="Peloton version %s" % peloton.RELEASE_VERSION)
parser.set_defaults(nodetach=False)
parser.add_option("--nodetach",
                  action="store_true",
                  dest="nodetach",
                  help="Prevent PSC detaching from terminal [default: %default]")

parser.add_option("-c", "--configpath",
                  help="""Directory containing the master server configuration files
 [default: %default]""",
                  default=pscplatform.DEFAULT_CONFIG_PATH)

parser.add_option("-v", "--servicepath",
                  help="""Directory containing peloton services. You may specify several
such directories with multiple instances of this option [default: %default]""",
                  action="append",
                  default=pscplatform.DEFAULT_SERVICE_PATH)

parser.add_option("-m", "--mode",
                  help="Run mode, one of prod, test or dev [default: %default]",
                  choices=['prod', 'test', 'dev'],
                  default='dev')

# If we need sub-groups of options:
#group = OptionGroup(parser, 'Dangerous Options',
#                    "Caution: use these options at your own risk. It is believed that some of them bite.")
#group.add_option('-g', action='store_true', help='Group option.')
#parser.add_option_group(group)

(options, args) = parser.parse_args()
# Handling errors and pumping back through the system
#if len(args) != 1:
#    parser.error("incorrect number of arguments")
print options
print args

ec = pscplatform.start(options, args)
sys.exit(ec)
 
