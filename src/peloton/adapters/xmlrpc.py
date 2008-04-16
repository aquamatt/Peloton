# $Id: xmlrpc.py 59 2008-03-12 10:33:50Z mp $
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
import datetime
import xmlrpclib
from twisted.application import service
from twisted.web import xmlrpc
from peloton.coreio import PelotonRequestInterface

def dump_xmlrpc_date(self, value, write):
    # according to spec at http://www.xmlrpc.com/spec XML-RPC date
    # is ISO 8601 format e.g. 19980717T14:08:55
    date = datetime.datetime.strftime(value, "%Y%m%dT%H:%M:%S")
    write("<value><dateTime.iso8601>%s</dateTime.iso8601></value>" % date)

def dump_xmlrpc_time(self, value, write):
    """ Serialize a datetime.time instance iso8601 format"""
    write("<value><dateTime.iso8601>%s</dateTime.iso8601></value>" % value.strftime("%Y%m%dT%H:%M:%S"))

def dump_xmlrpc_none(self, value, write):
    """ Handle None types by sending a string? """
    write("<value><nil/></value>")

class PelotonXMLRPCHandler(service.Service):
    """ XMLRPC protocol interface"""
    
    def __init__(self, kernel):
        self.kernel = kernel
        self.logger = kernel.logger
        self.requestInterface = PelotonRequestInterface(kernel)

        # Need to add a marshaler for datetime instances as xmlrpclib
        # will only marshall it's own style of datetime. 
        xmlrpclib.Marshaller.dispatch[type(datetime.datetime.now())] = dump_xmlrpc_date
        xmlrpclib.Marshaller.dispatch[type(datetime.date(2007,1,1))] = dump_xmlrpc_date
        xmlrpclib.Marshaller.dispatch[type(datetime.time(0,0))] = dump_xmlrpc_time
        xmlrpclib.Marshaller.dispatch[type(None)] = dump_xmlrpc_none
        
        self.setResource()
        
    def xmlrpc_request(self, sessionId, *args, **kargs):
        """ Make a service request. Takes the following arguments:
    - service (string)
    - method (string)
    - <parameters>
"""
        service = args[0]
        method = args[1]
        params = args[2:]
        return self.requestInterface.public_call(sessionId, "raw", service, method, params, {})

    def setResource(self):
        """ Create the XMLRPC resource and attach all xmlrpc_* methods
to it. """
        x = xmlrpc.XMLRPC()
        publishedMethods = [i for i in dir(self) if i.startswith('xmlrpc_')]
        for mthd in publishedMethods:
            # equiv to x.<mthd> = self.<mthd>
            setattr(x, mthd, getattr(self, mthd))
        self._resource = x
    
