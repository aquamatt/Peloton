# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
""" Setup Peloton logging via the Python logging module. """

import peloton.utils.logging as pul
import logging
import logging.handlers
import os

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

