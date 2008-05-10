#!/usr/bin/env python
# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
#!/usr/bin/env python2.4
"""newservice.py
Script for generating new directory and file layout for a service.
Includes stub code for key files that should allow a service to be
created in just a couple of minutes."""

import sys
import os
import peloton
from genshi.template import TemplateLoader
from genshi.template.text import TextTemplate
from genshi.template import MarkupTemplate
from peloton.utils.structs import FilteredOptionParser

import newservice 

TEXT = TextTemplate
XML = MarkupTemplate

class ServiceBuilder(object):
    def __init__(self):
        searchPath = [os.path.split(newservice.__file__)[0] + "/resource"]
        self.templateLoader = TemplateLoader(searchPath)
    
    def makeService(self, prefix, serviceName):
        """ Create folders and files for a new service. """
        serviceFolder = serviceName.lower()
        folderStructure = {serviceFolder: {
                                'config': {},
                                'docs' : {},
                                'tests' : {},
                                'scripts': {},
                                'resource': {
                                        'templates' : {
                                                serviceName: {}
                                                       }
                                            }
                                          }
                          }
        
        # list of lists, each list is composed of:
        # 1. folder name in which to create file
        # 2. name of file
        # 3. template to use
        files=[ [serviceFolder, "%s.py" % serviceFolder, 'service.genshi', TEXT],
                ["%s/config" % serviceFolder, "profile.pcfg", 'profileconf.genshi', TEXT],
                ["%s/docs" % serviceFolder, "%s.xml"%serviceFolder, 'docs.genshi', XML],
                ["%s/tests" % serviceFolder, "test%s"%serviceName, 'tests.genshi', TEXT],
                [serviceFolder, "__init__.py", "init.genshi", TEXT],
              ]
        
        try:
            self._makeDirs(prefix, folderStructure)
            self._makeFiles(serviceName, prefix, files)
        except OSError:
            print("Could not create directories and files - not writeable or dir exists.")
    
    def _makeDirs(self, prefix, folders):
        """ Recursively build a directory structure from a dictionary. """
        for folder,subfolders in folders.items():
            fpath = prefix+'/'+folder
            os.mkdir(fpath)
            if subfolders:
                self._makeDirs(fpath, subfolders)

    def _makeFiles(self, serviceName, prefix, files):
        
        keyData = {'name':serviceName,
                   'module': serviceName.lower(),
                   'package': serviceName.lower(),
                   }
        
        for folder, file, template, tmplCls in files:
            tmpl = self.templateLoader.load(template, cls=tmplCls)
            of = open(prefix+'/'+folder+'/'+file, 'wt')
            of.writelines(tmpl.generate(**keyData).render(strip_whitespace=False))
            of.close()

def main(args):
    usage = "usage: %prog [options]" 
    parser = FilteredOptionParser(usage=usage, version="NEWSERVICE; Peloton version %s" % peloton.RELEASE_VERSION)

    parser.add_option("--prefix",
                     help="Directory in which to create this service [default: %default]",
                     default=os.getcwd())
    parser.add_option("--service", "-s",
                      help="Service name (camel case)")

    options, args = parser.parse_args()
    if not options.service:
        parser.error("You must provide a name for this service!")
    
    ServiceBuilder().makeService(options.prefix, options.service)
    
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
