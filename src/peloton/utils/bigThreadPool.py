# $Id: coreio.py 104 2008-04-02 17:22:55Z mp $
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
"""
This is a mod to make all the Twisted threads daemon threads 
so that they do not block termination of the main process.

Even when threads are daemonised, when the reactor calls threadpool.stop()it 
attempts to join() every thread and close it. If threads are blocked for
some reason this call will also block.

So we overide stop() to set the workers count to zero. This by-passes some
twisted code and the daemon threads simply die with the parent.

This module must be imported before any other code imports the thread pool. 
"""
import twisted.python.threadpool
from twisted.python import threadable
threadable.init()
import Queue
import threading
from twisted import version as twistedVersion
from twisted.python import runtime
MIN_THREADS=5
MAX_THREADS=150

class DaemonThreadPool_2(twisted.python.threadpool.ThreadPool):
    def __init__(self, minthreads=5, maxthreads=20, name=None):
        """Create a new threadpool.

        @param minthreads: minimum number of threads in the pool

        @param maxthreads: maximum number of threads in the pool
        """
        assert minthreads >= 0, 'minimum is negative'
        assert minthreads <= maxthreads, 'minimum is greater than maximum'
        self.q = Queue.Queue(0)
        self.min = max(MIN_THREADS, minthreads)
        self.max = max(MAX_THREADS, maxthreads)
        self.name = name
        if runtime.platform.getType() != "java":
            self.waiters = []
            self.threads = []
            self.working = []
        else:
            self.waiters = twisted.python.threadpool.ThreadSafeList()
            self.threads = twisted.python.threadpool.ThreadSafeList()
            self.working = twisted.python.threadpool.ThreadSafeList()
        
    def startAWorker(self):
        self.workers = self.workers + 1
        name = "PoolThread-%s-%s" % (self.name or id(self), self.workers)
        try:
            firstJob = self.q.get(0)
        except Queue.Empty:
            firstJob = None
        newThread = threading.Thread(target=self._worker, name=name, args=(firstJob,))
        newThread.setDaemon(True)
        self.threads.append(newThread)
        newThread.start()

    def stop(self):
        self.workers = 0
        
class DaemonThreadPool_8(twisted.python.threadpool.ThreadPool):
    def __init__(self, minthreads=5, maxthreads=20, name=None):
        """Create a new threadpool.

        @param minthreads: minimum number of threads in the pool

        @param maxthreads: maximum number of threads in the pool
        """
        assert minthreads >= 0, 'minimum is negative'
        assert minthreads <= maxthreads, 'minimum is greater than maximum'
        self.q = Queue.Queue(0)
        self.min = max(MIN_THREADS, minthreads)
        self.max = max(MAX_THREADS, maxthreads)
        self.name = name
        if runtime.platform.getType() != "java":
            self.waiters = []
            self.threads = []
            self.working = []
        else:
            self.waiters = twisted.python.threadpool.ThreadSafeList()
            self.threads = twisted.python.threadpool.ThreadSafeList()
            self.working = twisted.python.threadpool.ThreadSafeList()

        
    def startAWorker(self):
        self.workers += 1
        name = "PoolThread-%s-%s" % (self.name or id(self), self.workers)
        newThread = self.threadFactory(target=self._worker, name=name)
        newThread.setDaemon(True)
        self.threads.append(newThread)
        newThread.start()

    def stop(self):
        self.workers = 0

if twistedVersion.major==2:
    twisted.python.threadpool.ThreadPool = DaemonThreadPool_2
else:
    twisted.python.threadpool.ThreadPool = DaemonThreadPool_8