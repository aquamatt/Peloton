# $Id: rest.py 125 2008-04-11 20:35:48Z mp $
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details

from twisted.internet import reactor
from twisted.internet.error import CannotListenError
from twisted.web import server
from twisted.web import resource
from twisted.web.static import FileTransfer
from peloton.adapters import AbstractPelotonAdapter
from peloton.adapters.xmlrpc import PelotonXMLRPCHandler
from peloton.coreio import PelotonRequestInterface
from peloton.utils.config import locateService
from peloton.exceptions import ServiceError

import os

binaryFileMimeTypes = {'.png':'image/PNG','.jpg':'image/JPEG',
       '.jpeg':'image/JPEG','.gif':'image/GIF','.bmp':'image/BMP',
       '.pdf':'application/PDF',
       '.zip':'application/x-zip-compressed',
       '.tgz':'application/x-gzip'}

plainFileMimeTypes = {'.css':'text/css',
      '.html' : 'text/html; charset=UTF-8',
      '.js':'text/javascript'}

class PelotonHTTPAdapter(AbstractPelotonAdapter, resource.Resource):
    """ The HTTP adapter provides for accessing methods over
HTTP and receiving the results in a desired format. The main interface
is rest-like but it also provides XMLRPC.

Strictly speaking this isn't true rest: URIs refer to services not
resources and session tracking is used. But... well... 
"""
    isLeaf = True
    def __init__(self, kernel):
        AbstractPelotonAdapter.__init__(self, kernel, 'HTTP Adapter')
        resource.Resource.__init__(self)
        self.logger = kernel.logger
        self.requestInterface = PelotonRequestInterface(kernel)
        self.xmlrpcHandler = PelotonXMLRPCHandler(kernel)

        # setup info template loader
        from peloton.utils.transforms import template
        source=os.path.split(__file__)[0].split(os.sep)
        source.extend(['templates','request_info.html.genshi'])
        self.infoTemplate = template({}, "/".join(source))
        
    def start(self):
        """ Implement to initialise the adapter. This method must also 
hook this adapter
into the reactor, probably calling reactor.listenTCP or adding
itself to another protocol as a resource (this is the case for most
HTTP based adapters)."""
        try:
            self.connection = reactor.listenTCP(self.kernel.settings.httpPort,
                              server.Site(self),
                              interface=self.kernel.profile.bind_interface)
        except CannotListenError:
            self.kernel.logger.info("Cannot start HTTP interface: port %s in use" % \
                                    self.kernel.settings.httpPort)
            self.connection = None
        

    def render_GET(self, request):    
        return self.render_POST(request)
    
    def render_POST(self, request):
        if request.postpath and request.postpath[0] == "RPC2":
            return self.xmlrpcHandler._resource.render(request)
        
        elif request.postpath and request.postpath[0] == "static":
            profile, _ = \
                self.kernel.serviceLibrary.getProfile(request.postpath[1])
            resourceRoot = profile['resourceRoot']
            self.deliverStaticContent(resourceRoot, request.postpath[2:], request)

        elif request.postpath and request.postpath[0] == "fireEvent":
            self.fireEvent(request.postpath[1:], request) 
            
        elif request.postpath and request.postpath[0] == "inspect":
            resp = self.infoTemplate({'rq':request}, {})
            self.deferredResponse(resp, 'html', None, 'text/html',request)
        
        elif request.postpath and request.postpath[0] == "favicon.ico":
            self.returnFavicon(request)

        else:
            if request.postpath[-1] == '':
                request.postpath = request.postpath[:-1]
            try:
                service, method = request.postpath[:2]
            except ValueError:
                if len(request.postpath) == 1:
                    service = request.postpath[0]
                    method = 'index'
                else:
                    raise ServiceError("Method or service not found for %s " % str(request.postpath))
                
            split = method.split('.')
            if len(split)==1:
                target = 'html'
            else:
                method, target = split

            args = request.postpath[2:]
            kwargs={}
            # JSON requests which set the callback argument will get a JSONP formatted response
            callbackName = None
            for k,v in request.args.items():
                self.kernel.logger.debug("Key %s value %s" % (k,v))
                if target == 'json' and k == 'callback':
                    callbackName = v[0]
                elif len(v) == 1:
                    kwargs[k] = v[0]
                else:
                    kwargs[k] = v

            self.kernel.logger.info("Callback name %s" % callbackName)

            try:
                profile, _ = self.kernel.serviceLibrary.getProfile(service)
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
            d.addCallback(self.deferredResponse, target, callbackName, mimeType, request)
            d.addErrback(self.deferredError, target, request)

        return server.NOT_DONE_YET

    def fireEvent(self, args, request):
        """ Fire an event on the message bus. Payload is the request arguments dictionary
with an additional key, __peloton_args__ with the request arguments list. 

args[0] is the channel on which to fire the event.
args[1] is the exchange

"""
        payload = request.args
        payload['__peloton_args'] = args[2:]
        self.kernel.dispatcher.fireEvent(args[0], args[1], **payload)
        request.write("OK")
        request.finish()
        
 
    def returnFavicon(self, request):
        request.setHeader('Content-Type','image/x-icon')
        thisDir = os.path.split(__file__)[0]
        iconPath = "%s/favicon.ico" % thisDir
        fsize = os.stat(iconPath)[6]
        request.setHeader('Content-Length',fsize)
        res = open(iconPath, 'rb')
        FileTransfer(res, fsize, request)        
        
    def deferredResponse(self, resp, target, callbackName, mimeType, request):
        # str ensures not unicode which is not liked by 
        # twisted.web
        resp = str(resp)
        if target == 'json' and callbackName:
            resp = "%s(%s)" % (callbackName, resp)
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
                
    def deliverStaticContent(self, resourceRoot, requestPath, request):
        """Read and deliver the static data content directly. """
        resourcePath = os.path.realpath('%s/%s' % (resourceRoot, '/'.join(requestPath)))
        resourcePath = resourcePath.replace('//','/')
#        resourceRoot = resourceRoot.replace('//','/')

        # os.path.realpath expands softlinks. If we did not do this for
        # resource root it may not match resourcePath.
        realResourceRoot = os.path.realpath(resourceRoot)
        if not resourcePath.startswith(realResourceRoot):
            request.setResponseCode(404)
            self.kernel.logger.debug("Relative path (%s|%s|%s) in request points outside of resource root" % (requestPath,resourcePath, resourceRoot))
            request.write("Relative path points outside resource root")
            request.finish()
            return
        
        if not os.path.isfile(resourcePath):
            request.setResponseCode(404)
            self.kernel.logger.debug("Request for non-existent static content")
            request.write("Static content unavailable.")
            request.finish()
            return
        
        suffix = resourcePath[resourcePath.rfind('.'):]

        if suffix in binaryFileMimeTypes.keys():
            openMode = 'rb'
            request.setHeader('Content-Type', binaryFileMimeTypes[suffix])
        elif suffix in plainFileMimeTypes.keys():
            openMode = 'rt'
            request.setHeader('Content-Type', plainFileMimeTypes[suffix])
        else:
            openMode = 'rt'
            request.setHeader('Content-Type', 'text/html')
        try:
            res = open(resourcePath, openMode)
            fsize = os.stat(resourcePath)[6]
            FileTransfer(res, fsize, request)
        except Exception, ex:
            request.setResponseCode(404)
            request.write("Could not read resource %s: %s" % (resourcePath, str(ex)))
            self.kernel.logger.debug("Could not read static resource %s: %s" % (resourcePath, str(ex)))
            request.finish()

    def _stopped(self, x):
        """ Handler called when reactor has stopped listening to this
protocol's port."""
        pass

    def stop(self):
        """ Close down this adapter. """
        if self.connection:
            d = self.connection.stopListening()
            d.addCallback(self._stopped)        
