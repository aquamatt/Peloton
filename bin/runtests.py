#!/usr/bin/env python
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

