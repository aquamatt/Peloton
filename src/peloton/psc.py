# $Id: psc.py 112 2008-04-05 21:19:14Z mp $
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

This script is pretty shallow: it simply starts the kernel using some
platform-specific code where required after first processing out command 
line arguments.
"""
# Random is used in many places in Peloton, so get it seeded
# right away.
import random
random.seed()
########################

import peloton
import peloton.utils.logging as logging
import os
import sys

from peloton.utils.structs import FilteredOptionParser
from peloton.psc_platform import makeDaemon

from peloton.kernel import PelotonKernel
from peloton.utils.config import PelotonSettings
from peloton.utils import deCompound

def start(pc):
    """ Start a PSC. By default the first step is to daemonise, either by 
a double fork (on a POSIX system) or by re-spawning the process (on Windows)
to detach from the console; this can be over-ridden by specifying --nodetach 
on the command line.

The kernel is then started. This creates worker processes as required via the
subprocess module.
"""
    if not pc.nodetach:
        makeDaemon()

    logging.initLogging(rootLoggerName='PSC', 
                        logLevel=getattr(logging, pc.loglevel),
                        logdir=pc.logdir, 
                        logfile='psc.log', 
                        logToConsole=pc.nodetach)
    logging.getLogger().info("Kernel starting; pid = %d" % os.getpid())
    
    kernel = PelotonKernel(pc)
    logging.setAdditionalLoggers(kernel)
    ex = kernel.start()
    return ex

def main():
    # Let's read the command line
    usage = "usage: %prog [options]" # add 'arg1 arg2' etc as required
    parser = FilteredOptionParser(usage=usage, version="Peloton version %s" % peloton.RELEASE_VERSION)
#    parser.set_defaults(nodetach=False)
    parser.add_option("--prefix",
                     help="Prefix directory to help with setting paths")
    
    parser.add_option("--nodetach",
                      action="store_true",
                      default=False,
                      help="Prevent PSC detaching from terminal [default: %default]")
    
    parser.add_option("-c", "--configfile",
                      help="Path to configuration file for the PSC [default: %default].",
                      dest="configfile",
                      default='psc.pcfg')
    
    parser.add_option("-b", "--bind", 
                      help="""specify the host:port to which this instance should bind. Overides
values set in configuration.""",
                      dest='bindhost')
    
    parser.add_option("--anyport",
                      action="store_true",
                      default=False,
                      help="""When set, this permits the PSC to seek a free port if the 
configured port is not available.""")
    
    parser.add_option("-s", "--servicepath",
                      help="""Directory containing peloton services. You may specify several
such directories with multiple instances of this option [default: %default]""",
                      action="append",
                      default=["$PREFIX/service"])
        
    parser.add_option("--loglevel",
                      help="""Set the logging level to one of critical, fatal, error(uat, prod), warning, info(test), debug(dev).
(defaults for each run mode indicated in brackets).""",
                      choices=['critical', 'fatal', 'error', 'warning', 'info', 'debug'])
    
    parser.add_option("--logdir", 
                      help="""Directory to which log files should be written. By setting this argument
the logging-to-file system will be enabled.""")
    parser.add_option("--disable",
                      help="""Comma delimited list of plugins to prevent starting even if configuration has them enabled""",
                      action="append")
    parser.add_option("--enable",
                      help="""Comma delimited list of plugins to start even if configuration has them disabled""",
                      action="append")
    
    parser.add_option("--flags",
                      help="""Comma delimited list of flags to add to this PSC.""",
                      action="append")
    
    
    options, args = parser.parse_args()
    # Handling errors and pumping back through the system
    #if len(args) != 1:
    #    parser.error("incorrect number of arguments")

    # add any sevice directories to sys.path if not already there
    for sd in options.servicepath:
        if sd not in sys.path:
            sys.path.append(sd)


    # enable, disable and flags are all 'append' types, but allow
    # comma delimited entries as well so we need to turn the list of
    # n potentially compound entries into a single list
    
    if options.enable:
        options.enable = deCompound(options.enable)
    else:
        options.enable=[]
        
    if options.disable:
        options.disable = deCompound(options.disable)
    else:
        options.disable=[]

    if options.flags:
        options.flags = deCompound(options.flags)
    else:
        options.flags=[]

    # determine the appropriate log-level for the root logger based
    # on supplied arguments.
    if options.loglevel:
        options.loglevel = options.loglevel.upper()
    else:
        options.loglevel = "ERROR"

    # Load configuration from file
    pc = PelotonSettings()
    try:
        pc.load(options.configfile)
    except IOError:
        sys.stderr.write("There is no profile for the PSC!\n")
        return 1
    
    if pc.profile.has_key('flags'):
        pc.profile.flags.extend(options.flags)
    else:
        pc.profile.flags = options.flags
        
    # copy in the necessary from options to config
    keys =['configfile', 'nodetach', 'bindhost', 
           'anyport', 'servicepath', 
           'loglevel', 'logdir', 
           'enable', 'disable']
    for k in keys:
        pc[k] = getattr(options, k)
        
    try:
        exitCode = start(pc)
    except:
        logging.getLogger().exception('Untrapped error in PSC: ')
        exitCode = 99
        
    return exitCode

if __name__ == '__main__':
    # returns 1 if no profile can be read
    # returns 99 for untrapped error
    sys.exit(main())

