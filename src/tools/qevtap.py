#!/usr/bin/env python

"""QT Event Viewer for Peloton"""

from twisted.python import threadable
threadable.init()

import qt4reactor
qt4reactor.install()

from evgui import Ui_MainWindow
from twisted.internet import reactor
from twisted.internet import defer
from twisted.internet.threads import deferToThread
from twisted.spread import pb
from peloton.utils.structs import FilteredOptionParser

from PyQt4 import QtCore
from PyQt4 import QtGui
import sys

VERSION="0.1.0"
EVENT_VIEWER, LOG_VIEWER = (0,1)

class State(object):
    pass
state = State()

class EventHandler(pb.Referenceable):
    def __init__(self, callback):
        self.callback = callback
        
    def remote_eventReceived(self, msg, exchange, key, ctag):
        self.callback(msg, exchange, key, ctag)

class ClosedownListener(pb.Referenceable):
    def remote_eventReceived(self,msg, exchange, key, ctag):
        if msg['action'] == 'disconnect' and \
            msg['sender_guid'] == state.pscGUID:
            state.mainWindow.sbLabel.setText("*** DISCONNECTED ***")

class MainWindow(QtGui.QMainWindow, Ui_MainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.setupUi(self)
        self.connect(self.actionExit, QtCore.SIGNAL('triggered()'), self.exit)        
        self.connect(self.actionEvent_Viewer, QtCore.SIGNAL('triggered()'), self.setMode)
        self.connect(self.actionLog_Viewer, QtCore.SIGNAL('triggered()'), self.setMode)        
        
        self.exchangeField.setText(state.options.exchange)
        self.messageKeyField.setText(state.options.key)
        self.sb = self.statusBar()
        self.sbLabel = QtGui.QLabel()
        self.sb.addPermanentWidget(self.sbLabel)
        self.connect(self.exchangeField, QtCore.SIGNAL('editingFinished()'), self.resetHandler)
        self.connect(self.messageKeyField, QtCore.SIGNAL('editingFinished()'), self.resetHandler)

    def resetHandler(self):
        state.options.key = str(self.messageKeyField.text())
        state.options.exchange = str(self.exchangeField.text())
        try:
            state.iface.callRemote('deregister', state.handler)
            d = state.iface.callRemote('register',state.options.key,state.handler,state.options.exchange)
            d.addErrback(self.registrationFailure)
        except pb.DeadReferenceError:
            print("Server closed connection unexpectedly!")
            self.stop()
            sys.exit()

    def registrationFailure(self, err):
        text = self.exchangeField.text()
        self.exchangeField.setText("***%s***" % text)

    def setMode(self):
        """ Called when mode is selected from menu. """
        if state.mode == LOG_VIEWER:
            state.mode = EVENT_VIEWER
            self.messageKeyField.setEnabled(True)
            self.exchangeField.setEnabled(True)
            self.actionEvent_Viewer.setChecked(True)
            self.actionLog_Viewer.setChecked(False)
            self.logTextEdit.clear()
            
        elif state.mode == EVENT_VIEWER:
            state.mode = LOG_VIEWER
            self.messageKeyField.setText('psc.logging')
            self.exchangeField.setText('logging')
            self.messageKeyField.setEnabled(False)
            self.exchangeField.setEnabled(False)
            self.actionEvent_Viewer.setChecked(False)
            self.actionLog_Viewer.setChecked(True)
            self.logTextEdit.clear()
            self.resetHandler()
        
    def callError(self, err):
        self.outputField.setText('Error calling Peloton PSC')
        print(str(err))
        
    def loggerEventFired(self, msg, exchange, key, ctag):
        if state.mode == LOG_VIEWER:
            self._displayLogEvent(msg, exchange, key, ctag)
        else:
            self._displayArbitraryEvent(msg, exchange, key, ctag)

    def _displayArbitraryEvent(self, msg, exchange, key, ctag):
        msgkeyColor = 'aa0000'
        exchColor = '00aaff'
        color = '0000aa'
        keyColor = '00aa00'
        self.logTextEdit.append('')
        self.logTextEdit.append("<span style='color:#%s'>Exchange: </span><span style='color:#%s'>%s</span><br/>" % (keyColor, exchColor, exchange))
        self.logTextEdit.append("<span style='color:#%s'>Key: </span><span style='color:#%s'>%s</span><br/>" % (keyColor, msgkeyColor, key))
        for k,v in msg.items():
            self.logTextEdit.append("<span style='color:#%s'>%s</span><span style='color:#%s'> : %s</span><br/>" % (keyColor, str(k), color, str(v)))
        
    def _displayLogEvent(self, msg, exchange, key, ctag):
        colours = {'DEBUG' : '00aaff',
                        'INFO' : '0000aa',
                        'WARN' : '00ff00',
                        'ERROR' : 'ff0000',
                    }
        try:
            msg['__color'] = colours[msg['levelname']]
        except:
            msg['__color'] = '000000'
        try:
            self.logTextEdit.append("""<span style='color:#%(__color)s'>%(levelname)s @ %(asctime)s : %(message)s</span><br/>""" % msg)
        except Exception, ex:
            print "Error: " + str(ex)

    def connectEvents(self):
        state.handler = EventHandler(self.loggerEventFired)
        self.resetHandler()

    def exit(self):
        try:
            state.iface.callRemote('deregister', state.closedownHandler)
            state.iface.callRemote('deregister', state.handler).addBoth(self.stop)
        except pb.DeadReferenceError:
            print("Server closed connection unexpectedly!")
            self.stop()
            sys.exit()
    
    def stop(self, *args):
        reactor.stop()

def initGUI():
    state.mainWindow = MainWindow()

def connected(svr):
    """ Connected OK, so now login """
    state.svr = svr
    d = svr.callRemote('login', 'qevtap')
    d.addCallback(loggedIn)
    d.addErrback(connectionError)
    
def loggedIn(iface):
    """ Logged in OK - so now show the GUI window. """
    state.iface = iface
    state.mainWindow.connectEvents()
    state.mainWindow.setVisible(True)
    d = state.iface.callRemote('getGUID')
    d.addCallback(setGUID)
    d.addErrback(connectionError)

def setGUID(guid):
    state.pscGUID = guid
    state.mainWindow.sbLabel.setText('Connected to %s' % guid)
    state.closedownHandler = ClosedownListener()
    state.iface.callRemote('register', 'psc.presence', state.closedownHandler, 'domain_control')

def connectionError(err):
    print("Error connecting to server %s:%d" % (state.options.host, 9100))
    reactor.stop()

def connect():
    """ Prepare to initiate the connection then start the reactor """
    factory = pb.PBClientFactory()
    reactor.connectTCP(state.options.host, 9100, factory)
    d = factory.getRootObject()
    d.addCallback(connected)
    d.addErrback(connectionError)
    reactor.run()
    
if __name__ == '__main__':
    usage = "usage: %prog [options]" 
    parser = FilteredOptionParser(usage=usage, version="QEVTAP version %s" % VERSION)

    parser.add_option("--host","-H",
                     help="Host for PSC to contact [default %default]",
                     default="localhost")
    parser.add_option("--key", "-k",
                      help="""Message key - may include the wildcards 
 # (match zero or more tokens) or * (match a single token) as defined in the
 AMQP specification [default %default]""",
                      default="#")

    parser.add_option("--exchange", "-x",
                      help="Exchange [default %default]",
                      default="events")

    options, args = parser.parse_args()
    state.options = options
    state.mode = EVENT_VIEWER
    
    initGUI()
    connect()
    print("Demo finished")