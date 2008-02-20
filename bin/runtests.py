#!/usr/bin/env python
##############################################################################
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved.
#
# This software  is licensed under the terms of the BSD license, a copy of
# which should accompany this distribution.
#
##############################################################################


import os
import sys
from unittester import *

def main(root, ignoreList):
    runTests(root, ignoreList)

if __name__ == '__main__':
    rootDir = os.getcwd()
    ignoreList = []
    args = sys.argv[1:] 
    if args:
        rootDir = args[0]
        
    print ("Root dir: %s" % rootDir)
    print("Running tests:")
    main(rootDir, ignoreList)

