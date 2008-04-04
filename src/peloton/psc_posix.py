# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
""" Start a PSC on POSIX compliant platforms """ 
import peloton.utils.logging as logging
import os
import subprocess

from peloton.kernel import PelotonKernel
from peloton.utils.config import PelotonConfig

def makeDaemon():
    """ Detach from the console, redirect stdin/out/err to/from
/dev/null."""
    # File mode creation mask of the daemon.
    UMASK = 0
    # Default maximum for the number of available file descriptors.
    MAXFD = 1024
    # The standard I/O file descriptors are redirected to /dev/null by default.
    if (hasattr(os, "devnull")):
        REDIRECT_TO = os.devnull
    else:
        REDIRECT_TO = "/dev/null"
        
    try:
        pid = os.fork()
    except OSError, e:
        raise Exception, "%s [%d]" % (e.strerror, e.errno)

    if (pid == 0):  # The first child.
        os.setsid()

        try:
            pid = os.fork() # Fork a second child.
        except OSError, e:
            raise Exception, "%s [%d]" % (e.strerror, e.errno)

        if (pid == 0):  # The second child.
            os.umask(UMASK)
        else:
            # exit() or _exit() - See http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/278731 
            os._exit(0) # Exit parent of the second child - the first child.
    else:
        os._exit(0) # Exit parent of the first child.

    # Close all open file descriptors.  This prevents the child from keeping
    # open any file descriptors inherited from the parent.  
    import resource
    maxfd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
    if (maxfd == resource.RLIM_INFINITY):
        maxfd = MAXFD
    # Iterate through and close all file descriptors.
    for fd in range(0, maxfd):
        try:
            os.close(fd)
        except OSError:    
            # ERROR, fd wasn't open to begin with (ignored)
            pass

    # redirect stdin/out/err to /dev/null (or equivalent) 
    fd = os.open(REDIRECT_TO, os.O_RDWR)    
    
    # Duplicate fd to standard input, standard output and standard error.
    os.dup2(fd, 0)            # standard input (0)
    os.dup2(fd, 1)            # standard output (1)
    os.dup2(fd, 2)            # standard error (2)

class GeneratorInterface(object):
    """ Interface through which a PelotonKernel can communicate
with the worker generator. PelotonKernel is intended not to have
dependencies on the topology of the PSC/Worker group so is passed
an object, such as this, which wraps up the implementation details
of messaging between the two components."""
    def __init__(self):
        # get path to pwp - it'll be in the same directory
        # as this file
        fspec = __file__.split('/')[:-1]
        fspec.append('pwp.py')
        self.pwp = os.sep.join(fspec)
        if not os.path.isfile(self.pwp):
            raise Exception("Cannot find worker process launcher %s!" % self.pwp)
    
    def initGenerator(self, bindHost):
        """ bindHost is a string of the form host:port. """
        self.host, self.port = bindHost.split(':')
        
    def startService(self, num,  token):
        for _ in range(num):
            subprocess.Popen(['python', self.pwp, self.host, self.port, token])
        
    def stop(self):
        pass

def start(options, args):
    """ Start a PSC. By default the first step is to double fork to detach
from the console; this can be over-ridden by specifying --nodetach on the
command line.

Next, another fork will happen. The child is the worker generator, the parent
the PSC master process. The worker generator will be used to 
spawn worker processes running service code. 

Once the worker is started it waits on an anonymous pipe to be informed of the
port number on which the PSC master starts its Twisted RPC service.

Once informed the worker enters a loop, waiting for instructions on the 
anonymous pipe to start procesess for specific services. These worker
processes communicate with the PSC master via Twisted RPC. The worker generator
is responsible solely for starting them. 

The generator is required because we need a virgin, non-initialised template
to fork from; forking from the PSC master would be bad as the program stack will
contain all the initialised PSC code which is quite different to the worker code.
"""
    if not options.nodetach:
        makeDaemon()

    pc = PelotonConfig(options)

    logging.closeHandlers()
    logging.initLogging(rootLoggerName='PSC', 
                        logLevel=getattr(logging, options.loglevel),
                        logdir=options.logdir, 
                        logfile='psc.log', 
                        logToConsole=options.nodetach)
    genInt = GeneratorInterface()
    logging.getLogger().info("Kernel starting; pid = %d" % os.getpid())
    try:
        ex = PelotonKernel(genInt, options, args, pc).start()
    except:
        genInt.stop()
        raise
    
    return ex