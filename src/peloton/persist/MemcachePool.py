"""Developed by :
      Jehiah Czebotar
      Aryeh Katz

   Released under Apache License 2.0
   Version 1.0 - January 24, 2006

   http://jehiah.com/download/MemcachePool.py.txt
   http://jehiah.com/download/Bogus.py.txt

   ---------------------

   edit the MemcachePool.getMCHosts() to suit your needs

   import MemcachePool
   mc = MemcachePool.getMC()
   mc.set(...)
   mc.get(...)
"""
#import memcache                        
try:
    # c-Memcache: twice as fast as memcache; builtin module
    import cmemcache as memcache   
except:
    # Pymemcache - pure python
    import memcache
    
import os
import threading

class Bogus:
    def __init__(self, selfShuntObj=None):
        pass
    
    def set(self, name, value,time=0):
        return 0
    
    def add(self, name, value,time=0):
        return 0
    
    def replace(self, name, value,time=0):
        return 0
    
    def delete(self, name,time=0):
        return 0
    
    def incr(self, name,value=1):
        return 0
    
    def decr(self, name,value=1):
        return 0
    
    def get(self, name):
        return None
    
    def flush_all(self):
        pass
    
    def debuglog(self, str):
        pass
    
    def disconnect_all(self):
        pass
    
    def forget_dead_hosts(self):
        pass
    
    def get_multi(self, keys):
        return None
    
    def get_stats(self):
        return None
    
    def set_servers(self, keys):
        pass
    
class MemcachePool:
    def __init__(self,hosts=None):
        if not hosts:
            raise Exception()
        self._pooled_conns=[]
        self.enabled = True
        self._hosts=hosts
        self.lock = threading.Lock()
        
    def enable(self):
        self.enabled = True
    def disable(self):
        self.enabled = False

    def addConnection(self):
        try:
            mc = memcache.Client(self._hosts)
        except:
            print "creating bogus exception"
            mc = Bogus()
        return mc

    def getConnection(self):
        if not self.enabled:
            return Bogus()

        self.lock.acquire()
        if len(self._pooled_conns) > 0:
            mc = self._pooled_conns.pop()
        else:
            mc = self.addConnection()
        self.lock.release()    
        return mc

    def returnConnection(self,mc):
        # never return bogus memcache client to the pool
        if  not isinstance(mc,Bogus):
            self.lock.acquire()
            self._pooled_conns.append(mc)
            self.lock.release()
        
    def get(self,key):
        mc = self.getConnection()
        v = mc.get(key)
        self.returnConnection(mc)
        return v

    def set(self,key,value,time=0):
        mc = self.getConnection()
        r = mc.set(key,value,time)
        self.returnConnection(mc)
        return r

    def flush_all(self):
        mc = self.getConnection()
        r = mc.flush_all()
        self.returnConnection(mc)
        return r

    def add(self,key,value,time=0):
        mc = self.getConnection()
        r = mc.add(key,value,time)
        self.returnConnection(mc)
        return r

    def replace(self,key,value,time=0):
        mc = self.getConnection()
        r = mc.replace(key,value,time)
        self.returnConnection(mc)
        return r

    def delete(self,key,time=0):
        mc = self.getConnection()
        r = mc.delete(key,time)
        self.returnConnection(mc)
        return r

    def incr(self,name,value=1):
        mc = self.getConnection()
        r = mc.incr(name,value)
        self.returnConnection(mc)
        return r

    def decr(self,name,value=1):
        mc = self.getConnection()
        r = mc.decr(name,value)
        self.returnConnection(mc)
        return r

    def disconnect_all(self):
        self.lock.acquire()
        while len(self._pooled_conns):
            mc = self._pooled_conns.pop()
            mc.disconnect_all()
        self.lock.release()

    def get_multi(self,keys):
        mc = self.getConnection()
        v = mc.get_multi(keys)
        self.returnConnection(mc)
        return v

    def get_stats(self):
        mc = self.getConnection()
        r = mc.get_stats()
        self.returnConnection(mc)
        return r

_globalMemcachePool = None

def init(hosts):
    global _globalMemcachePool
    if _globalMemcachePool == None:
        _globalMemcachePool = MemcachePool(hosts)

def getMC():
    return _globalMemcachePool
