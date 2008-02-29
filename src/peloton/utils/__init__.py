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