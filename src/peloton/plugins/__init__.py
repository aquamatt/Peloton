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

The Plugin Architecture
=======================

The key feature of a Peloton PSC is that it is extremely light weight;
cheap to start and cheap to stop a mesh is made robust in part by
the very simplicity of its components.

In order to help keep the weight down and also to simplify the development
and customisation process, many kernel features not essential to the
functioning of any PSC are implemented as kernel plugins.

So, for example, if a particular scheduler is required, or an 
interface to a bespoke messaging bus on a client site, it may be implemented
as a kernel plugin and loaded according to configuration at runtime.

Plugins may easily be enabled/disabled in configuration and so may also be
switched on or off according to the current gridmode.

Be aware that the writing of a kernel plugin is more delicate than writing
a service. Services run in the sandbox of a separate process and requests
are handled in a separate thread so a bug might lock the thread but it will
not lock the system.

A PSC kernel plugin is operating at the heart of the system: locking the event
loop will completely disable the PSC and prevent requests reaching services that 
it manages, and results from returning. 

A PSC kernel plugin is NOT a substitute for a service. It is NOT something that
the 'casual' service writer (the quant in the bank; the accountant who also
writes a bit of VB script etc) should deal with.

Plugin developers should understand Twisted, network programing and the meaning 
of threading in Python. If a developer understands all that, the plugin system
opens up a number of exciting possibilities for extending the Peloton platform.

Security
========

Plugins have access to all your core PSC functionality: they are un-restricted 
in their ability to operate in the PSC and as such should NEVER be introduced
lightly or be permitted to introduce un-guarded functionality to the user
layer.

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