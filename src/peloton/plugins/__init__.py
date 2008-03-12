# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details

""" Plugins directory containing Peloton Core plugins that form
part of the distribution. 

Peloton plugins hook into the main event loop so must be thoroughly
tested prior to deployment on production systems. 

Each plugin is initialised with configuration details and has
to register itself with the reactor in an appropriate manner.

At the time of initialisation the reactor will not be running.
"""

class PelotonPlugin(object):
    """ Base class for all Peloton core plugins """
    def __init__(self, pluginConfig, logger):
        if pluginConfig.has_key('comment'):
            self.comment = pluginConfig['comment']
        self.logger = logger
        self.config = pluginConfig
        self.started = False
        
    def start(self):
        """ Do all that is required to start this plugin. start() 
may be called prior to the reactor being started. """
        raise NotImplementedError()
    
    def stop(self):
        """ Close down cleanly this protocol. """
        raise NotImplementedError()