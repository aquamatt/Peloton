# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
""" Start a PSC on POSIX compliant platforms """
 
import logging
import logging.handlers
import os
import sys
import cPickle as Pickle
from types import StringType, ListType

from peloton.kernel import PelotonKernel
from peloton.worker import PelotonWorker
from peloton.utils import chop

def initLogging(loglevel='ERROR', logdir='', logfile='', rootLoggerName='PSC', closeHandlers=False, toConsole=False):
    """ Configure the logger for this PSC. By default no logging to
file unless explicitly requested by setting logdir. If only logfile is set, no disk
logging will occur. You must explicitly set logdir to '.' to enable disk logging to
the current working directory. 

Logging to stdout/err enabled if --nodetach is specified; otherwise logging to the 
event bus only. 

If closeHandlers==True all current handlers FOR THE ROOT LOGGER ONLY will be closed. 
This is useful after a fork to reset the logger to a virgin state prior to re-configuring.
It assumes that no other loggers are initialised other than the root; thus if this feature
is to be used forking must occur before new loggers are initialised. 

By default the root logger is named 'PSC' but this may be overidden by assigning to
rootLoggerName.

The default log level is 'ERROR'; again you are advised to set explicitly the loglevel
argument.

By default the console logger is not hooked up; set toConsole=True to enable.
"""    

    logger = logging.getLogger()
    
    if closeHandlers:
        # Remove all log handlers from logger before re-setting
        while logger.handlers:
            logger.removeHandler(logger.handlers[-1])
        
    defaultLogFormatter = logging.Formatter("[%(levelname)s] %(asctime)-4s %(name)s : %(message)s")
    
    logger.name=rootLoggerName
    logger.setLevel(loglevel)

    if logdir:
        # removes empty elements so allows for logdir being empty
        filePath = os.sep.join([i for i in [logdir, logfile] if i])
        fileHandler = logging.handlers.TimedRotatingFileHandler(filePath, 'MIDNIGHT',1,7)
        fileHandler.setFormatter(defaultLogFormatter)
        logger.addHandler(fileHandler)

    if toConsole:
        logStreamHandler = logging.StreamHandler()
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

    # redirect stdin/out/err to /dev/null (or equivalent) 
    fd = os.open(REDIRECT_TO, os.O_RDWR)    
    
    # Duplicate fd to standard input, standard output and standard error.
    os.dup2(fd, 0)            # standard input (0)
    os.dup2(fd, 1)            # standard output (1)
    os.dup2(fd, 2)            # standard error (2)

def runGenerator(pipeFD, options, args):
    """ Main loop of the worker generator process.
Listens to the pipe from the PSC and spawns worker processes
when requested. This is a two step process:

    1.  Open the pipe for reading and read one line which is formatted as
        "INIT:host:port".Split out the host and the port
    
    2.  Enter loop reading pickled lists off the pipe. Each list contains two
        items, the name of a service to start and optional arguments. Fork and
        start a PelotonWorker in the child. Parent loops round and reads next
        command off the pipe.
    """
    logger = initLogging(getattr(logging, options.loglevel),
                        options.logdir, 
                        'generator.log',
                        'PSC-GEN', 
                        True, 
                        options.nodetach)
    
    logger.info("Generator started; pid = %d" % os.getpid())
    pin = os.fdopen(pipeFD, 'rt')

    host, port = (None, None)    
    
    # Now enter the loop which spawns worker processes
    while True:
        l = chop(pin.readline())
        if l=='STOP':
            logger.info("Generator closing down")
            pin.close()
            return 0
        elif l.startswith('INIT:'):
            host, port = l[5:].split(':')
            port = int(port)
            logger.info("Generator initialised with master at %s:%d" % (host, port))
        else:
            if host==None and port==None:
                logger.error("Generator asked to fork a worker but master PSC has not initialised")
                continue
            name, args = Pickle.loads(pin.readline())
            
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
        
    def initGenerator(self, bindHost):
        """ bindHost is a string of the form host:port. """
        self.writePipe.write('INIT:%s\n' % bindHost)
        
    def startService(self, serviceName, token, args):
        self.writePipe.write('%s\n', Pickle.dumps([serviceName, token, args]))
        
    def stop(self):
        self.writePipe.write('STOP\n')
        self.writePipe.close()

def start(options, args, pc):
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

    logger = initLogging(getattr(logging, options.loglevel),
                        options.logdir, 
                        'psc.log',
                        'PSC', 
                        True, 
                        options.nodetach)
    
    pr, pw = os.pipe()

    # Fork off a worker generator
    try:
        pid = os.fork()
    except OSError, e:
        raise Exception, "%s [%d]" % (e.strerror, e.errno)

    if pid == 0: # am the worker generator
        ex = runGenerator(pr, options, args)
    else:
        genInt = GeneratorInterface(pw)
        logger.info("Kernel starting; pid = %d" % os.getpid())
        try:
            ex = PelotonKernel(genInt, options, args, pc).start()
        except:
            genInt.stop()
            raise
    
    return ex