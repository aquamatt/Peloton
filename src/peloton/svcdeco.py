# $Id: svcdeco.py 59 2008-03-12 10:33:50Z mp $
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details

""" Decorators for service methods.
"""
import peloton.utils.logging as logging
def localAudit(f):
    def _f(*args, **kargs):
        logging.getLogger().debug("%s called with args: %s, kargs:%s" % (f.func_name, str(args[1:]), str(kargs)))
        return f(*args, **kargs)
    return _f

def setKey(key, value):
    def wrapper(f):
        if not hasattr(f, '_PELOTON_METHOD_PROPS'):
            f._PELOTON_METHOD_PROPS = {}
        f._PELOTON_METHOD_PROPS[key] = value
        return f
    return wrapper

def transform(transformKey, *transformList):
    return setKey("transform.%s"%transformKey, list(transformList))
        
def mimeType(target, mimeType):
    return setKey("mimetype.%s" % target, mimeType)