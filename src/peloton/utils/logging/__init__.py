# $Id: __init__.py 122 2008-04-11 08:22:28Z mp $
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
""" Provides logging facilities to peloton. Allows 
centralised setup of logging and the option to switch
logging back-ends. 

"""
DEBUG, INFO, WARN, WARNING, ERROR, CRITICAL, FATAL = (10,20,30,30,40,50,50)
__LOGGER__ = None
_DEFAULT_FORMAT__ = "[%(levelname)s]\t %(asctime)-4s %(name)s\t : %(message)s"

def initLogging(backend='PYTHON', defaultFormat=None, 
                rootLoggerName='PSC', logLevel=ERROR,
                logdir='', logfile='', logToConsole=True):
    """ Initialise the Peloton logger with the specified backend,
either PYTHON (default) or TWISTED. 

You may optionaly set the default log entry format here."""
    global __LOGGER__, _DEFAULT_FORMAT__
    if backend == 'PYTHON':
        import peloton.utils.logging.python_logger as _logger
    elif backend == 'TWISTED':
        import peloton.utils.logging.twisted_logger as _logger
    else:
        raise Exception("Logger backend '%s' not known!" % backend)

    if defaultFormat != None:
        _DEFAULT_FORMAT__ = defaultFormat
    
    __LOGGER__ = _logger
    __LOGGER__.initialise(rootLoggerName, logLevel, logdir, logfile, logToConsole)
    getLogger().info("SET DEFAULT LOG LEVEL FROM OPTIONS:  self.initOptions.loglevel")

def closeHandlers():
    """ Close all log handlers cleanly. """
    if __LOGGER__:
        __LOGGER__.closeHandlers()

def getLogger(name=''):
    """ Return the root logger or the named logger
if specified. """
    if __LOGGER__ == None:
        initLogging()
        __LOGGER__.getLogger().info("Logger initialised with defaults!")
    return __LOGGER__.getLogger(name)

def setBusLogger(kernel):
    __LOGGER__.BusLogHandler(kernel)

#class BasePelotonLogger(object):
#    """ Base class for all Peloton logger systems """
#    _LOG_LEVEL__ = ERROR
#    
#    def debug(self, msg):
#        raise NotImplementedError()
#    
#    def info(self, msg):
#        raise NotImplementedError()
#    
#    def warn(self, msg):
#        raise NotImplementedError()
#
#    def warning(self, msg):
#        self.warn(msg)
#        
#    def error(self, msg):
#        raise NotImplementedError()
#    
#    def critical(self, msg):
#        raise NotImplementedError()
#    
#    def fatal(self, msg):
#        raise NotImplementedError()
#    
#    def exception(self, msg):
#        raise NotImplementedError()
#
#    def setLevel(level=ERROR):
#        """ Set the log level to level (constants defined in 
#logging are:
#    
#    - DEBUG
#    - INFO
#    - WARN
#    - WARNING
#    - ERROR
#    - CRITICAL
#    - FATAL
#        
#When the level is set all messages at that level or higher (later in the
#list) are output; all others are ignored. For example, if loglevel==WARN
#then WARN[ING], ERROR, CRITICAL and FATAL messages will be output whilst
#INFO and DEBUG messages will silently be dropped.
#"""
#        pass
