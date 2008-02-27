# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
""" Start a PSC on POSIX compliant platforms """
 
import logging
import os
import sys
import cPickle as Pickle
from types import StringType, ListType

from peloton.kernel import PelotonKernel
from peloton.worker import PelotonWorker
from peloton.utils import chop

# every psc implementation has to specify the default place to 
# look for configuration data. Provides the default for $PREFIX in 
# command line options
DEFAULT_CONFIG_ROOT='/etc/peloton/'

class NullStream(object):
    """ File like object bit-bucket providing null output for logging
if it is to be entirely disabled. """
    def write(self, *args, **kargs):
        pass
    
    def writeline(self, *args, **kargs):
        pass
    
    def writelines(self, *args, **kargs):
        pass
    
    def flush(self):
        pass

def initLogging(options):
    """ Configure the logger for this PSC. By default no logging to
file unless explicitly requested on the command line. Logging to stdout/err
if --nodetach is specified; otherwise logging to the event bus. """    

    # determine the appropriate
    if options.loglevel:
        options.loglevel = options.loglevel.upper()
    else:
        options.loglevel = {'dev':'DEBUG',
                           'test':'INFO',
                           'uat_a':'ERROR',
                           'uat_b':'ERROR',
                           'prod':'ERROR'}[options.mode]
    
    defaultLogFormatter = logging.Formatter("[%(levelname)s] %(asctime)-4s %(name)s : %(message)s")
    
    
    logger = logging.getLogger('')
    logger.name='PSC'
    logger.handlers=[] # following a fork, clear old handlers out for reset
    logger.setLevel(getattr(logging, options.loglevel))

    if options.logfile:
        fileHandler = logging.handlers.TimedRotatingFileHandler(options.logfile, 'MIDNIGHT',1,7)
        fileHandler.setFormatter(defaultLogFormatter)
        logger.addHandler(fileHandler)

    if options.nodetach:
        logStreamHandler = logging.StreamHandler()
        logStreamHandler.setFormatter(defaultLogFormatter)
        logger.addHandler(logStreamHandler)            

    if not logging._handlers:
        logStreamHandler = logging.StreamHandler(NullStream())
        logStreamHandler.setFormatter(defaultLogFormatter)
        logger.addHandler(logStreamHandler)            

    return logger

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

    # Redirect the standard I/O file descriptors to the specified file.  Since
    # the daemon has no controlling terminal, most daemons redirect stdin,
    # stdout, and stderr to /dev/null.  This is done to prevent side-effects
    # from reads and writes to the standard I/O file descriptors.

    # This call to open is guaranteed to return the lowest file descriptor,
    # which will be 0 (stdin), since it was closed above.
    os.open(REDIRECT_TO, os.O_RDWR)    # standard input (0)
    
    # Duplicate standard input to standard output and standard error.
    os.dup2(0, 1)            # standard output (1)
    os.dup2(0, 2)            # standard error (2)

def runGenerator(pipeFD, options, args):
    """ Main loop of the worker generator process.
Listens to the pipe from the PSC and spawns worker processes
when requested. This is a two step process:

 1) Open the pipe for reading and read one line which is in the format:
 
    host:port
    
    Split these apart then proceed to step 2
    
 2) Enter loop reading pickled lists off the pipe. Each list contains two
    items, the name of a service to start and optional arguments. Fork and
    start a PelotonWorker in the child. Parent loops round and reads next
    command off the pipe.
    """
    
    pin = os.fdopen(pipeFD, 'rt')
    
    # First wait for initialisation string which is simply host:port of
    # the PSC Twisted RPC interface
    l = chop(pin.readline())
    host, port = l.split(':')
    
    # Now enter the loop which spawns worker processes
    while True:
        l = Pickle.loads(pin.readline())
        if type(l) == StringType and chop(l)=='STOP':
            os.close(pipeFD)
            return 0
        
        elif type(l) == ListType:
            name, args = l
            
            # fork a worker
            try:
                pid = os.fork()
            except OSError, e:
                raise Exception, "%s [%d]" % (e.strerror, e.errno)
            
            if pid == 0: # worker process
#                os.close(pipeFD)
                return PelotonWorker(host, port, options, args).start() 
        
class GeneratorInterface(object):
    """ Interface through which a PelotonKernel can communicate
with the worker generator. PelotonKernel is intended not to have
dependencies on the topology of the PSC/Worker group so is passed
an object, such as this, which wraps up the implementation details
of messaging between the two components."""
    def __init__(self, writePipe):
        self.writePipe = os.fdopen(writePipe, 'wt', 0)
        
    def startService(self, serviceName, args):
        self.writePipe.write('%s\n', Pickle.dumps([serviceName, args]))

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
    if options.nodetach:
        logging.getLogger().debug("PSC is not daemonising (nodetach == True)")
    else:
        makeDaemon()
        # re-initialise the logging as those file handles will have been closed
        initLogging(options)

    pr, pw = os.pipe()

    # Fork off a worker generator
    try:
        pid = os.fork()
    except OSError, e:
        raise Exception, "%s [%d]" % (e.strerror, e.errno)

    if pid == 0: # am the worker generator
        ex = runGenerator(pr, options, args)
    else:
        ex = PelotonKernel(GeneratorInterface(pw), options, args).start()
    
    return ex