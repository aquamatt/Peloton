# $Id: structs.py 35 2008-02-27 11:31:57Z mp $
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
""" Create a new domain key file which is composed of the following:
  - A random 50 character cookie
  - An ezPyCrypto public key
  - The corresponding ezPyCrypto private key
"""
import os
import sys
import random
import ezPyCrypto

import peloton
from peloton.utils.structs import FilteredOptionParser
from peloton.utils import chop

tokenlength = 50
keylength = 512
tokenspace = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
__VERSION__ = "0.1"

def makeKeyFile(keyfile, toConsole=False):
    cookie = "".join([tokenspace[random.randrange(0,len(tokenspace))] 
                      for i in xrange(tokenlength)])
    
    key = ezPyCrypto.key(keylength)
    contents = cookie+"\n"+key.exportKeyPrivate()
    if toConsole:
        print(contents)
    else:
        f = open(keyfile,'wt')
        f.writelines(contents)
        f.close()

def main():
    usage = "usage: %prog [options]" # add 'arg1 arg2' etc as required
    parser = FilteredOptionParser(usage=usage, version="Peloton newkey version %s" % __VERSION__)
    parser.add_option("--prefix",
                      help="Path to directory containing configuration data, links to services etc. [default: %default]",
                      default=peloton.getPlatformDefaultDir('config'))
    
    parser.add_option("-d", "--domain",
                      help="""Specify the domain name for which to create a key [default: %default]""",
                      default="Pelotonica")
    
    parser.add_option("-k", "--domainkey",
                      help="""Domain key file [default: $PREFIX/keys/<domain>.key]""",
                      default="$PREFIX/keys/$DOMAIN.key")
    
    parser.add_option("-c", "--console", 
                      help="""Send to console instead of file""",
                      action="store_true",
                      default=False)

    opts, args = parser.parse_args()
    makeKeyFile(os.path.expanduser(opts.domainkey), opts.console)
    return 0

if __name__ == '__main__':
    sys.exit(main())