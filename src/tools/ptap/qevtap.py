#!/usr/bin/env python
# $Id: pseudomq.py 93 2008-03-25 22:08:27Z mp $
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details

"""QT Event Viewer for Peloton"""
import qt4reactor
qt4reactor.install()

from evgui import Ui_MainWindow
import tapcore
from peloton.utils.structs import FilteredOptionParser

from PyQt4 import QtCore
from PyQt4 import QtGui
import math
import sys
import time

VERSION="0.1.0"
EVENT_VIEWER, LOG_VIEWER = (0,1)

class State(object):
    pass
state = State()

class MainWindow(QtGui.QMainWindow, Ui_MainWindow):
    def __init__(self, tapConn):
        QtGui.QMainWindow.__init__(self)
        # keyed on GUID this stores data about each host 
        self.tapConn = tapConn
        self.profiles= {}
        self.setupUi(self)
        self.connect(self.actionExit, QtCore.SIGNAL('triggered()'), self.exit)        
        self.connect(self.actionEvent_Viewer, QtCore.SIGNAL('triggered()'), self.setEventViewer)
        self.connect(self.actionLog_Viewer, QtCore.SIGNAL('triggered()'), self.setLogViewer)        
        
        self.sb = self.statusBar()
        self.sbLabel = QtGui.QLabel()
        self.sb.addPermanentWidget(self.sbLabel)
        self.connect(self.exchangeComboBox, QtCore.SIGNAL('currentIndexChanged()'), self.resetHandler)
        self.connect(self.messageKeyField, QtCore.SIGNAL('editingFinished()'), self.resetHandler)

        self.handler = None
        self.timeDisconnected = 0
        
        tapConn.addListener("loggedin", self.tapConnected)
        tapConn.addListener("profileReceived", self.setProfile)
        tapConn.addListener("masterProfileReceived", self.setMasterProfile)
        tapConn.addListener("exchangesReceived", self.setExchanges)
        tapConn.addListener("disconnected", self.disconnected)
        
    def tapConnected(self):
        if self.timeDisconnected > 0:
            self.logTextEdit.append("<span style='color:white; background-color:green; text-align:center;'>Server re-connected</span> after %ds"% self.timeDisconnected)
        self.timeDisconnected = 0
        
    def resetHandler(self, *args):
        state.options.key = str(self.messageKeyField.text())
        state.options.exchange = str(self.exchangeComboBox.currentText())
        if self.handler:
            self.tapConn.removeEventHandler(self.handler)
        self.handler = self.tapConn.addEventHandler(state.options.key, \
                            state.options.exchange, self.loggerEventFired)

    def setEventViewer(self):
        if state.mode == LOG_VIEWER:
            self.logTextEdit.clear()
            state.mode = EVENT_VIEWER
            self.setMode()
    
    def setLogViewer(self):
        if state.mode == EVENT_VIEWER:
            self.logTextEdit.clear()
            state.mode = LOG_VIEWER
            self.setMode()

    def setMode(self):
        """ Called when mode is selected from menu. """
        if state.mode == EVENT_VIEWER:
            self.actionEvent_Viewer.setChecked(True)
            self.actionLog_Viewer.setChecked(False)
            self.messageKeyField.setEnabled(True)
            self.exchangeComboBox.setEnabled(True)
            
        elif state.mode == LOG_VIEWER:
            self.actionEvent_Viewer.setChecked(False)
            self.actionLog_Viewer.setChecked(True)
            self.messageKeyField.setText('psc.logging')
            self.exchangeComboBox.setCurrentIndex(self.exchangeComboBox.findText('logging'))
            self.messageKeyField.setEnabled(False)
            self.exchangeComboBox.setEnabled(False)
            self.resetHandler()
        
    def callError(self, err):
        self.outputField.setText('Error calling Peloton PSC')
        print(str(err))

    def loggerEventFired(self, msg, exchange, key, ctag):
        if not self.profiles.has_key(msg['sender_guid']):
            self.tapConn.getPSCProfile(msg['sender_guid'])
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
            if self.profiles.has_key(msg['sender_guid']):
                p = self.profiles[msg['sender_guid']]
                host = p['hostname']
                dix = host.find('.')
                if dix > 0:
                    host = host[:dix]
                msg['__source'] = "%s:%s" % (host, p['port'])
            else:
                msg['__source'] = '???'
            created = float(msg['created'])
            t = time.localtime(created)
            millis = int(math.modf(created)[0]*1000.0)
            msg['time'] = "%s.%03d" % (time.strftime('%H:%M:%S', t), millis)
            self.logTextEdit.append("""<span style='color:#%(__color)s'>%(time)s %(__source)s  : %(levelname)s [%(name)s] %(message)s</span><br/>""" % msg)
        except Exception, ex:
            print "Error: " + str(ex)

    def setExchanges(self, exchanges):
        for x in exchanges:
            self.exchangeComboBox.addItem(x)
        self.exchangeComboBox.setCurrentIndex(self.exchangeComboBox.findText(state.options.exchange))
        self.messageKeyField.setText(state.options.key)
        self.setMode()
        self.resetHandler()

    def setMasterProfile(self, profile):
        self.setProfile(profile, True)

    def setProfile(self, profile, isMaster=False):
        self.profiles[profile['guid']] = profile
        if isMaster:
            state.mainWindow.sbLabel.setText('Connected to %s:%s' % \
                                         (profile['hostname'], profile['port']))

    def disconnected(self):
        state.mainWindow.sbLabel.setText('DISCONNECTED (%ds)' % self.timeDisconnected)
        if self.timeDisconnected == 0:
            self.logTextEdit.append("<span style='color:white; background-color:red; text-align:center;'>Server disconnected</span> attempting reconnection</span>")
        self.timeDisconnected += 1

    def exit(self):
        self.tapConn.stop()
        sys.exit(0)
    
if __name__ == '__main__':
    usage = "usage: %prog [options]" 
    parser = FilteredOptionParser(usage=usage, version="QEVTAP version %s" % VERSION)

    parser.add_option("--host","-H",
                     help="Host for PSC to contact [default %default]",
                     default="localhost")

    parser.add_option("--port", "-p",
                      help="Port on which to connect [default %default]",
                      default = "9100")

    options, args = parser.parse_args()
    state.options = options
    state.options.key='psc.logging'
    state.options.exchange='logging'
    state.tapConn = tapcore.TAPConnector(options.host, int(options.port), 'qevtap', 'qevtap')
    state.mode = LOG_VIEWER
    state.mainWindow = MainWindow(state.tapConn)
    state.mainWindow.setVisible(True)
    state.tapConn.start()
    print("QEVTAP finished")
    sys.exit(0)
