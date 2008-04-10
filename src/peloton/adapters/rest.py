# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details

from twisted.internet import reactor
from twisted.internet.error import CannotListenError
from twisted.web import server
from twisted.web import resource
from peloton.adapters import AbstractPelotonAdapter
from peloton.coreio import PelotonRequestInterface

from cStringIO import StringIO
import types

class PelotonRestAdapter(AbstractPelotonAdapter, resource.Resource):
    """ The REST adapter provides for accessing methods over
HTTP and receiving the results in a desired format.

Strictly speaking this isn't true rest: URIs refer to services not
resources and session tracking is used. But... well... 
"""
    isLeaf = True
    def __init__(self, kernel):
        AbstractPelotonAdapter.__init__(self, kernel, 'REST Adapter')
        resource.Resource.__init__(self)
        self.requestInterface = PelotonRequestInterface(kernel)
        self.formatters = {'xml' : XMLFormatter(),
                           'html' : HTMLFormatter(),
                           }
        
    def start(self, configuration, options):
        """ Implement to initialise the adapter based on the 
parsed configuration file (configuration) and command line 
options (options). This method must also hook this adapter
into the reactor, probably calling reactor.listenTCP or adding
itself to another protocol as a resource (this is the case for most
HTTP based adapters)."""
        try:
            self.connection = reactor.listenTCP(int(configuration['psc.restPort']),
                              server.Site(self),
                              interface=configuration['psc.bind_interface'])
        except CannotListenError:
            self.kernel.logger.info("Cannot start REST interface: port %s in use" % configuration['psc.restPort'])
            self.connection = None
        

    def render_GET(self, request):    
        return self.render_PUT(request)
    
    def render_PUT(self, request):
        if request.postpath[0]=='__info':
            resp = self.render_info(request)
            self.deferredResponse(resp, request)
            return
        else:
            service, method = request.postpath[:2]
            split = method.split('.')
            if len(split)==1:
                format = 'html'
            else:
                method, format = split
                
            args = request.postpath[2:]
            kwargs={}
            for k,v in request.args.items():
                if len(v) == 1:
                    kwargs[k] = v[0]
                else:
                    kwargs[k] = v
                    
            sessionId="TOBESORTED"
            d = self.requestInterface.public_call(sessionId, service, method, args, kwargs )
            d.addCallback(self.deferredResponse, format, request)
            d.addErrback(self.deferredError, format, request)

        return server.NOT_DONE_YET
        
    def deferredResponse(self, resp, format, request):
        try:
            ct, resp = self.formatters[format].format(resp)
        except KeyError:
            ct, resp = self.formatters['html'].format(resp)
        request.setHeader('Content-Type', ct)
        request.setHeader('Content-Length', len(resp))
        request.write(resp)
        request.finish()
        
    def deferredError(self, err, format, request):
        try:
            ct, err = self.formatters[format].format(err)
        except KeyError:
            ct, err = self.formatters['html'].format(err)
            
        request.setHeader('Content-Type', ct)
        request.setHeader('Content-Length', len(err))
        request.write(err)
        request.finish()

    def render_info(self, request):
        resp = StringIO()
        resp.write("<html><head><title>Peloton Request</title></head>")
        resp.write("<body><h2>Your request</h2>")
        resp.write("<p style='font-weight:bold'>The service, method path, *args path:</p>")
        resp.write("<ol>")
        for p in request.postpath:
            resp.write("<li>%s</li>" % p) 
        resp.write("</ol>")
        resp.write("<p style='font-weight:bold'>The **kwargs:</p>")
        resp.write("<ul>")
        for k,v in request.args.items():
            resp.write("<li>%s=%s</li>" % (k, str(v))) 
        resp.write("</ul>")
        
        resp.write("<p style='font-weight:bold'>The headers:</p>")
        resp.write("<ul>")
        for k,v in request.received_headers.items():
            resp.write("<li>%s=%s</li>" % (k, str(v))) 
        resp.write("</ul>")
        
        resp.write("</body></html>")
        return resp.getvalue()
            
    def _stopped(self, x):
        """ Handler called when reactor has stopped listening to this
protocol's port."""
        pass

    def stop(self):
        """ Close down this adapter. """
        if self.connection:
            d = self.connection.stopListening()
            d.addCallback(self._stopped)        

####### NODDY - JUST FOR POC ###############
class XMLFormatter(object):
    def format(self,v):
        """ Returns content-type, content. """
        s = StringIO()
        if type(v) == types.ListType or type(v) == types.TupleType:
            s.write("<data>\n")
            index = 0
            for value in v:
                s.write("  <item id='%d'>%s</item>\n" % (index, str(value)))
                index+=1
            s.write("</data>")

        elif type(v) == types.DictType:
            s.write("<data>\n")
            for key, value in v.items():
                s.write("  <item key='%s'>%s</item>\n" % (str(key), str(value)))
            s.write("</data>")
        
        else:
            s.write("<data>\n")
            s.write("  <value>\n    %s\n  </value>\n" % str(v))
            s.write("</data>")
            
        return "text/xml", s.getvalue()
    
class HTMLFormatter(object):
    def format(self,v):
        """ Returns content-type, content. """
        s = StringIO()
        if type(v) == types.ListType or type(v) == types.TupleType:
            s.write("<html><body><h2>Response</h2><ol>\n")
            index = 0
            for value in v:
                s.write("  <li>[%d] %s</li>\n" % (index, str(value)))
                index+=1
            s.write("</ol></body></html>")
            
        elif type(v) == types.DictType:
            s.write("<html><body><h2>Response</h2><ol>\n")
            for key, value in v.items():
                s.write("  <li>%s = %s</li>\n" % (str(key), str(value)))
            s.write("</ol></body></html>")

        else:
            s.write("<html><body><h2>Response</h2>\n")
            s.write("%s\n" % str(v))
            s.write("</body></html>")

        return "text/html", s.getvalue()
    