# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
""" Platform dependent implementations of some processes. For now,
makeDaemon.""" 
import os

def POSIX_makeDaemon():
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

def WINDOWS_makeDaemon():
    raise NotImplementedError("Sorry: your platform (%s) is not yet supported by Peloton" % os.name)


# Set makeDaemon according to platform
if os.name in ['posix', 'mac']:
    makeDaemon = POSIX_makeDaemon
else:
    makeDaemon = WINDOWS_makeDaemon
