# $Id: python_logger.py 123 2008-04-11 10:17:34Z mp $
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
""" Setup Peloton logging via the Python logging module. """

import peloton.utils.logging as pul
import logging
import logging.handlers
import os
import cPickle as pickle

class NullHandler(logging.Handler):
    """ A logging handler that simply looses everying down the bit bucket..."""
    def __init__(self):
        logging.Handler.__init__(self)
        
    def emit(self, record):
            pass

_LOG_HANDLERS_ = []
_DEFAULT_LEVEL_ = pul.ERROR

def initialise(rootLoggerName='PSC', logLevel=None, logdir='', logfile='', logToConsole=True):
    global _DEFAULT_LEVEL_
    if logLevel:
        _DEFAULT_LEVEL_ = logLevel
    else:
        logLevel = _DEFAULT_LEVEL_
        
    formatter = logging.Formatter(pul._DEFAULT_FORMAT__)
    
    if logdir:
        # removes empty elements so allows for logdir being empty
        filePath = os.sep.join([i for i in [logdir, logfile] if i])
        fileHandler = logging.handlers.TimedRotatingFileHandler(filePath, 'MIDNIGHT',1,7)
        fileHandler.setFormatter(formatter)
        _LOG_HANDLERS_.append(fileHandler)
    
    if logToConsole:
        logStreamHandler = logging.StreamHandler()
        logStreamHandler.setFormatter(formatter)
        _LOG_HANDLERS_.append(logStreamHandler)            
        
    if not _LOG_HANDLERS_:
        # add a nullhandler for good measure
        _LOG_HANDLERS_.append(NullHandler())
        
    logger = logging.getLogger()
    logger.name = rootLoggerName
    logger.setLevel(logLevel)
    for h in _LOG_HANDLERS_:
        logger.addHandler(h)
        
def closeHandlers():
    logger = logging.getLogger()
    while _LOG_HANDLERS_:
        logger.removeHandler(_LOG_HANDLERS_.pop())
    
def getLogger(name=''):
    l = logging.getLogger(name)
    l.setLevel(_DEFAULT_LEVEL_)
    return l

class BusLogHandler(logging.Handler):
    """ A logging handler that puts log messages onto the message bus.
    """
    def __init__(self, kernel):
        logging.Handler.__init__(self)
        self.kernel = kernel
        logging.getLogger().addHandler(self)

    def makeEvent(self, record):
        event={}
        keys = ['created', 'filename', 'funcName', 'levelname', 
                'lineno', 'module', 'name', 'pathname',  
                'process', 'threadName']
        for key in keys:
            event[key] = getattr(record, key)
            
        # sometimes record has key msg, others message... not
        # sure why two versions of record exist. Same class 
        # from same location (checked)
        
        if hasattr(record, 'message'):
            event['message'] = record.message
        else:
            event['message'] = record.msg
            
        return event
    
    def send(self, event):
        self.kernel.dispatcher.fireEvent(key="psc.logging", exchange='logging', **event)

    def emit(self, record):
        try:
            event = self.makeEvent(record)
            self.send(event)
        except Exception, ex:
            print(ex)

