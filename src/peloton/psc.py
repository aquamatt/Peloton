# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details

""" PSC: Peloton Service Controller

The service controller is the primary unit in the Peloton mesh. 
PSC units link together to form a mesh; each PSC manages a number
of services.

How those services are managed is dependent on the controller; some
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
import logging
import os
import sys
from optparse import OptionGroup
from peloton.utils.structs import FilteredOptionParser
import peloton

def main():
    # Let's read the command line
    pscplatform = peloton.getPlatformPSC()
        
    usage = "usage: %prog [options]" # add 'arg1 arg2' etc as required
    parser = FilteredOptionParser(usage=usage, version="Peloton version %s" % peloton.RELEASE_VERSION)
#    parser.set_defaults(nodetach=False)
    parser.add_option("--nodetach",
                      action="store_true",
                      default=False,
                      help="Prevent PSC detaching from terminal [default: %default]")
    
    parser.add_option("-c", "--configdir",
                      help="Path to directory containing configuration data. You may provide several config directories. [default: %default]",
                      action="append",
                      dest="configdirs",
                      default=[peloton.getPlatformDefaultDir('config')])
    
    parser.add_option("-g", "--grid",
                      help="""Short name for the grid to join [default: %default]""",
                      default="peligrid")
    
    parser.add_option("-d", "--domain",
                      help="""Short name for the domain to join [default: %default]""",
                      default="pelotonica")
    
    parser.add_option("-b", "--bind", 
                      help="""specify the host:port to which this instance should bind. Overides
values set in configuration.""",
                      dest='bindhost')
    
    parser.add_option("-p", "--profile",
                      help="""Path to a PSC profile""",
                      dest="profile")
    
    parser.add_option("--anyport",
                      action="store_true",
                      default=False,
                      help="""When set, this permits the PSC to seek a free port if the 
configured port is not available.""")
    
    parser.add_option("-s", "--servicepath",
                      help="""Directory containing peloton services. You may specify several
such directories with multiple instances of this option [default: %default]""",
                      action="append",
                      default=["$PREFIX/services"])
        
    parser.add_option("--loglevel",
                      help="""Set the logging level to one of critical, fatal, error(uat, prod), warning, info(test), debug(dev).
(defaults for each run mode indicated in brackets).""",
                      choices=['critical', 'fatal', 'error', 'warning', 'info', 'debug'])
    
    parser.add_option("--logdir", 
                      help="""Directory to which log files should be written. By setting this argument
the logging-to-file system will be enabled.""")
    
    # If we need sub-groups of options:
    #group = OptionGroup(parser, 'Dangerous Options',
    #                    "Caution: use these options at your own risk. It is believed that some of them bite.")
    #group.add_option('-g', action='store_true', help='Group option.')
    #parser.add_option_group(group)
    
    options, args = parser.parse_args()
    # Handling errors and pumping back through the system
    #if len(args) != 1:
    #    parser.error("incorrect number of arguments")

    # determine the appropriate log-level for the root logger based
    # on supplied arguments.
    if options.loglevel:
        options.loglevel = options.loglevel.upper()
    else:
        options.loglevel = "DEBUG"

    try:
        exitCode = pscplatform.start(options, args)
    except:
        logging.getLogger().exception('Untrapped error in PSC:')
        exitCode = 99
        
    return exitCode

if __name__ == '__main__':
    sys.exit(main())

