# $Id: __init__.py 114 2008-04-07 22:23:16Z mp $
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
import os
import socket
import sys

def chop(s, extras=[]):
    """Remove \\r, \\n and all characters in the extras list from 
the end of string s and return """
    _ch = ['\r','\n']
    _ch.extend(extras)
    
    while s[-1] in _ch:
        s = s[:-1]
        
    return s

def getClassFromString(clazz, reload=False):
    """ Performn an import given an absolute class reference as a string; returns
the class object. If 'reload' is set True sys.modules will be cleaned prior
to import  thus hopefuly effecting a reload."""
    packageTree = clazz.split('.')
    cls = packageTree[-1]
    packageTree = packageTree[:-1]
    
    if reload:
        currentKey = ''
        loadedModules = sys.modules.keys()
        for pkg in packageTree:
            currentKey = ".".join([i for i in [currentKey, pkg] if i])
            if currentKey in loadedModules:
                del(sys.modules[currentKey])
                print("Purging %s " % currentKey)
    
    try:
        mdle = __import__(".".join(packageTree),{},{},".".join(packageTree[:-1]))
        handler = getattr(mdle, cls)
        if callable(handler):
            return handler
        else:
            raise Exception("Class %s is not valid" % clazz)
    except Exception,ex:
        raise Exception("Could not find class %s (error: %s)" %(clazz, str(ex)))

def getExternalIPAddress():
    """ Bit of a cheap way of working out what the IP address
of the external interface on this machine is; if we've got 
configuration saying to connect to 0.0.0.0 that's fine, but we
will still need to know what address to tell other nodes to 
contact this node on. As a result, something like this is handy."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('1.2.3.4', 56))
        ip = s.getsockname()[0]    
        s.close()
    except:
        ip = socket.gethostbyname(socket.gethostname())
    return ip

def deCompound(l):
    """ Takes l which is likely from configuration parsing and will be 
a list of strings, some of which may be comma delimited. Expands the 
comma delimited lists and returns a single, separated list. Thus, 
a list transforms as follows::
    
    ["a", "b", "c,d,e", "f"] --> ["a","b","c","d","e","f"]
"""
    out = []
    for i in l:
        out.extend(i.split(','))
    return out