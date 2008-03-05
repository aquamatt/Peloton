# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details

def chop(s, extras=[]):
    """Remove \\r, \\n and all characters in the extras list from 
the end of string s and return """
    _ch = ['\r','\n']
    _ch.extend(extras)
    
    while s[-1] in _ch:
        s = s[:-1]
        
    return s

def getClassFromString(clazz):
    """ Performn an import given an absolute class reference as a string; returns
the class object."""
    packageTree = clazz.split('.')
    cls = packageTree[-1]
    packageTree = packageTree[:-1]
    try:
        mdle = __import__(".".join(packageTree),{},{},".".join(packageTree[:-1]))
        handler = getattr(mdle, cls)
        if callable(handler):
            return handler
        else:
            raise Exception("Class %s is not valid" % clazz)
    except Exception,ex:
        raise Exception("Could not find class %s (error: %s)" %(clazz, str(ex)))
