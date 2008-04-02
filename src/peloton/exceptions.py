# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
""" All Peloton exceptions """

class PelotonError(Exception):
    """ Base for all Peloton exceptions; can be used on its own
if no other exception is suitable. """
    def __init__(self, msg='', rootException=None):
        """ Initialise with an optional message and, optionally,
a root exception object - likely the underlying exception that resulted
in this exception being raised."""
        Exception.__init__(self, msg)
        self.rootException = rootException
        
    def __str__(self):
        """ Use base str but if there is a rootException add that message
to it. """
        if self.rootException:
            return "%s : Root exception: %s" % \
                (Exception.__str__(self), str(self.rootException))
        else:
            return Exception.__str__(self)
        
class ConfigurationError(PelotonError):
    """To be raised when an error occurs reading a configuration file, 
a profile file or similar; also any other configuration-related errors."""
    pass

class PluginError(PelotonError):
    """ To be raised on the whole if a general plugin error occurs; specific
plugins may wish to provide a little more specific exceptions. """
    pass

class ServiceNotFoundError(PelotonError):
    pass

class ServiceConfigurationError(PelotonError):
    pass

class ServiceError(PelotonError):
    pass

class MessagingError(PelotonError):
    pass

class WorkerError(PelotonError):
    """ Generic error raised if something untoward occurs in a worker
process. """
    pass