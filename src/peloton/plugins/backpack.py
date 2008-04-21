# $Id: backpack.py 83 2008-03-21 00:20:56Z mp $
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
from peloton.plugins import PelotonPlugin
from peloton.utils import getClassFromString
from peloton.events import AbstractEventHandler
from pysqlite2 import dbapi2 as sqlite
from twisted.spread import pb
from twisted.internet import reactor
import time

class BackPackPlugin(PelotonPlugin):
    """ The Peloton plugin interface to the BackPack system through which
requests are made and nodes managed.

On startup - make a Store and if not master fire a 'who is' event.
Re-issue every 5 seconds until response comes.

With response, get proxy from routing table and getInterface(<name>) 
which returns BackPackIO that provides get(), set(), del() and others.

Listen for broadcast cache-updates and invalidation

The store conforms to interface to allow for changing in the future.


KNOWN ISSUES:

 - All nodes trap invalidate and populate their own store, thus all nodes
   end up with full copy of cache. This should be changed so that only 
   certain keys are kept by all, and maybe even only the advertised 'edge' 
   nodes at that. low cache TTL helps but...
 - ...no purging of cache as yet
 - master store has infinite TTL and no purging.
 - All ops happen in event thread so potential blocking and slowing of operations... should
   go to thread but that complicates life somewhat, mainly because it's hard to make invalidation requests
   'jump the queue' and to have timed purges if the handling thread is blocking on get. Alternative is to loop with 
   timer, but that's horrible. I think there's a Queue implementation with a timeout somewhere; that could work...
- getMulti and delete not yet implemented.

- need to implement manual purge of entire parent group
- test with file-based storage
- implement slave system
"""
    def initialise(self):
        # get class for persistence and initialise
        self.backEnd = \
            getClassFromString(self.config['storageBackend'])(self.kernel, self.config)

        self.get = self.backEnd.get
        self.set = self.backEnd.set
        self.getmulti = self.backEnd.getmulti
        self.delete = self.backEnd.delete

        # create the callable
        self.iface = BackPackIO(self)
    
    def start(self):
        self.backEnd.start()
        self.kernel.registerCallable(self.config['storeName'], self.iface)
    
    def stop(self):
        self.backEnd.stop()
        self.kernel.deregisterCallable('backpack')
            
class BackPackIO(pb.Referenceable):
    """ Referenceable used by client nodes to communicate with the master. """
    def __init__(self, backpack):
        self.backpack = backpack
        
    def remote_get(self, parent, key):
        return self.backpack.get(parent, key)
    
    def remote_set(self, parent, key, value, source):
        self.backpack.set(parent, key, value, False, source=source)
    
    def remote_getmulti(self, parent, keys):
        return self.backpack.getmulti(self, parent, keys)
    
    def remote_delete(self, parent, key=None):
        self.backpack.delete(parent, key)
    
class BackPackPersistentStore(object):
    """ Base class for all persistence back-ends for the BackPack system. """
    def __init__(self, kernel, config):
        self.kernel = kernel
        self.config = config
        self.cacheTTL=config.as_int('cacheTTL')
        self.masterGUID = ''
        self.mbusChannel = 'psc.plugins.backpack.%s' % self.config['storeName']
    
    def start(self):
        raise NotImplementedError()
    
    def stop(self):
        raise NotImplementedError()

class BackPackSQLite(BackPackPersistentStore, AbstractEventHandler):
    def __init__(self, kernel, config):
        BackPackPersistentStore.__init__(self, kernel, config)
        AbstractEventHandler.__init__(self)
        # store updates prior to master coming online
        self.remoteUpdateQueue = []
        self.kernel.dispatcher.register(self.mbusChannel, self, 'domain_control')

    def start(self):
        if self.kernel.hasFlag('backpackMaster'):
            self.isMaster = True
            storeFile = self.config['storeFile']
            self.ttl = -1
        else:
            self.isMaster = False
            storeFile = ':memory:'
            self.masterRef = None
            self.CONNECTING_MASTER = False
            self._seekMaster()
            self.ttl = self.cacheTTL
            
        self.db = sqlite.connect(storeFile)
        self.kernel.logger.debug("Going to create table")
        try:
            self.db.executescript("""create table backpack (
        parent  varchar(100),
        ttl      integer,
        expiry   integer,
        key      char(20),
        value    varchar(200)
    );
    """)
        except sqlite.OperationalError, ex:
            self.kernel.logger.error(str(ex))

    def stop(self):
        self.db.close()

    def get(self, parent, key):
        self.kernel.logger.debug("Getting %s|%s" %(parent, key))
        try:
            try:
                cur = self.db.cursor()
                cur.execute("select value from backpack where parent=? and key=?", (parent, key))
                v = eval(cur.fetchone()[0])
            except Exception, err:
                if (not self.isMaster) and self.masterRef:
                    v = self.masterRef.callRemote('get', parent, key)
                    v.addCallback(lambda x: self.set(parent, key, x, True))
                else:
                    raise KeyError("Key %s|%s is not valid. (%s)" % (parent, key, str(err)))
        finally:
            cur.close()
        return v
        
    def set(self, parent, key, value, netUpdate=False, source=None):
        """ if netUpdate is True this will not propagate upstream...
used when responding to an invalidation request."""
        cur = self.db.cursor()
        if self.ttl > 0:
            expiry = long(time.time() + self.ttl)
        else:
            expiry = -1
        rvalue = repr(value)
        self.kernel.logger.debug("Setting %s|%s=%s" %(parent, key, rvalue))
        cur.execute("delete from backpack where parent=? and key=?", (parent, key))
        cur.execute("insert into backpack(parent, ttl, expiry, key, value) values (?, ?, ?, ?, ?)",
                    (parent, self.ttl, expiry, key, rvalue))
        self.db.commit()

        if (not self.isMaster) and (not netUpdate):
            if self.masterRef:
                # update the master
                self.masterRef.callRemote('set', parent, key, value, self.kernel.guid)
            else:
                self.remoteUpdateQueue.put( ('set', parent, key, value, self.kernel.guid) )
        elif self.isMaster:
            self.kernel.dispatcher.fireEvent(self.mbusChannel,
                                             'domain_control',
                                             type='INVALIDATE',
                                             parent=parent,
                                             datakey=key,
                                             value=rvalue,
                                             source=source
                                             )

        # required for use in lambda function in get, above
        return value
        
    def getmulti(self, parent, keys):
        pass
    
    def delete(self, parent, key=None):
        pass
    
    def _seekMaster(self):
        """ loop which messges for a master until one is discovered. """
        if (not self.masterRef) and not (self.CONNECTING_MASTER):
            self.kernel.dispatcher.fireEvent(self.mbusChannel,
                                             'domain_control',
                                             type='WHO_IS_MASTER'
                                             )
            reactor.callLater(5, self._seekMaster)

    def _connectMaster(self):
        self.CONNECTING_MASTER = True
        try:
            proxy = self.kernel.routingTable.pscByGUID[self.masterGUID]  
        except KeyError:
            reactor.callLater(0.2, self._connectMaster)
            return
        
        d = proxy.getInterface(self.config['storeName'])
        d.addCallback(self._masterFound)
        d.addErrback(self._masterError)
        
    def _masterFound(self, master):
        self.masterRef = master
        self.CONNECTING_MASTER = False
        self.kernel.logger.info("Connected to backpack master for %s" % self.config['storeName'])
        # flush any set calls that need making
        while  self.remoteUpdateQueue:
            self.masterRef.callRemote(*self.remoteUpdateQueue.pop(0))
        
    def _masterError(self, err):
        self.kernel.logger.error("Error connecting to master data base for %s: %s" % (self.config['storeName'], err.getErrorMessage()))
        self.CONNECTING_MASTER = False
        reactor.callLater(1, self._seekMaster)
    
    def eventReceived(self, msg, exchange='', key='', ctag=''):
        """ Waits for the following events:
    - 'who is master' messages; if master responds.
    - 'I am master' message
    - 'invalidation' message
"""
        if msg['type'] == 'WHO_IS_MASTER':
            if self.isMaster:
                self.kernel.dispatcher.fireEvent(self.mbusChannel,
                                     'domain_control',
                                     type='I_AM_MASTER'
                                     ) 
                       
        elif msg['type'] == 'I_AM_MASTER':
            masterGUID = msg['sender_guid']
            if self.isMaster or self.masterGUID == masterGUID:
                return
            self.masterGUID = masterGUID
            self._connectMaster()
        
        elif msg['type'] == 'INVALIDATE':
            if self.isMaster or msg['source']==self.kernel.guid:
                return
            self.set(msg['parent'], msg['datakey'], eval(msg['value']), True)
    