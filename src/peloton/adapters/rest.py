# $Id: rest.py 125 2008-04-11 20:35:48Z mp $
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
        if '__info' in request.args.keys():
            resp = self.render_info(request)
            self.deferredResponse(resp, request)
            return
        else:
            service, method = request.postpath[:2]
            split = method.split('.')
            if len(split)==1:
                target = 'html'
            else:
                method, target = split
                
            args = request.postpath[2:]
            kwargs={}
            for k,v in request.args.items():
                if len(v) == 1:
                    kwargs[k] = v[0]
                else:
                    kwargs[k] = v

            try:
                profile = self.kernel.serviceLibrary.getLastProfile(service)
                mimeType = profile['methods'][method]['properties']['mimetype.%s'%target]
            except:
                try:
                    mimeType = {'html':'text/html',
                          'xml':'text/xml',
                          'json':'text/plain',
                          'raw':'text/plain'}[target]
                except KeyError:
                    mimeType = 'text/plain'

                    
            sessionId="TOBESORTED"
            d = self.requestInterface.public_call(sessionId, target, service, method, args, kwargs )
            d.addCallback(self.deferredResponse, mimeType, request)
            d.addErrback(self.deferredError, target, request)

        return server.NOT_DONE_YET
        
    def deferredResponse(self, resp, mimeType, request):
        # str ensures not unicode which is not liked by 
        # twisted.web
        resp = str(resp)
        request.setHeader('Content-Type', mimeType)
        request.setHeader('Content-Length', len(resp))
        request.write(resp)
        request.finish()
        
    def deferredError(self, err, format, request):
        err = "ERROR: (%s) %s" % (err.parents[-1], err.getErrorMessage())
        request.setHeader('Content-Type', 'text/plain')
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
