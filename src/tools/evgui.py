# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'evgui.ui'
#
# Created: Wed Apr 30 18:46:45 2008
#      by: PyQt4 UI code generator 4.3.3
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(QtCore.QSize(QtCore.QRect(0,0,702,375).size()).expandedTo(MainWindow.minimumSizeHint()))

        self.centralwidget = QtGui.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")

        self.vboxlayout = QtGui.QVBoxLayout(self.centralwidget)
        self.vboxlayout.setSpacing(6)
        self.vboxlayout.setMargin(9)
        self.vboxlayout.setObjectName("vboxlayout")

        self.hboxlayout = QtGui.QHBoxLayout()
        self.hboxlayout.setObjectName("hboxlayout")

        self.label = QtGui.QLabel(self.centralwidget)

        font = QtGui.QFont()
        font.setWeight(75)
        font.setBold(True)
        self.label.setFont(font)
        self.label.setObjectName("label")
        self.hboxlayout.addWidget(self.label)

        self.exchangeField = QtGui.QLineEdit(self.centralwidget)
        self.exchangeField.setObjectName("exchangeField")
        self.hboxlayout.addWidget(self.exchangeField)

        self.label_2 = QtGui.QLabel(self.centralwidget)

        font = QtGui.QFont()
        font.setWeight(75)
        font.setBold(True)
        self.label_2.setFont(font)
        self.label_2.setObjectName("label_2")
        self.hboxlayout.addWidget(self.label_2)

        self.messageKeyField = QtGui.QLineEdit(self.centralwidget)
        self.messageKeyField.setObjectName("messageKeyField")
        self.hboxlayout.addWidget(self.messageKeyField)
        self.vboxlayout.addLayout(self.hboxlayout)

        self.logTextEdit = QtGui.QTextEdit(self.centralwidget)

        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.logTextEdit.sizePolicy().hasHeightForWidth())
        self.logTextEdit.setSizePolicy(sizePolicy)
        self.logTextEdit.setReadOnly(True)
        self.logTextEdit.setObjectName("logTextEdit")
        self.vboxlayout.addWidget(self.logTextEdit)
        MainWindow.setCentralWidget(self.centralwidget)

        self.menubar = QtGui.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0,0,702,30))
        self.menubar.setObjectName("menubar")

        self.menuFIle = QtGui.QMenu(self.menubar)
        self.menuFIle.setObjectName("menuFIle")

        self.menuMode = QtGui.QMenu(self.menubar)
        self.menuMode.setObjectName("menuMode")
        MainWindow.setMenuBar(self.menubar)

        self.statusbar = QtGui.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.actionExit = QtGui.QAction(MainWindow)
        self.actionExit.setObjectName("actionExit")

        self.actionEvent_Viewer = QtGui.QAction(MainWindow)
        self.actionEvent_Viewer.setCheckable(True)
        self.actionEvent_Viewer.setChecked(True)
        self.actionEvent_Viewer.setObjectName("actionEvent_Viewer")

        self.actionLog_Viewer = QtGui.QAction(MainWindow)
        self.actionLog_Viewer.setCheckable(True)
        self.actionLog_Viewer.setObjectName("actionLog_Viewer")
        self.menuFIle.addAction(self.actionExit)
        self.menuMode.addAction(self.actionEvent_Viewer)
        self.menuMode.addAction(self.actionLog_Viewer)
        self.menubar.addAction(self.menuFIle.menuAction())
        self.menubar.addAction(self.menuMode.menuAction())

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QtGui.QApplication.translate("MainWindow", "Peloton Event Viewer", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("MainWindow", "Exchange", None, QtGui.QApplication.UnicodeUTF8))
        self.label_2.setText(QtGui.QApplication.translate("MainWindow", "Message Key", None, QtGui.QApplication.UnicodeUTF8))
        self.menuFIle.setTitle(QtGui.QApplication.translate("MainWindow", "File", None, QtGui.QApplication.UnicodeUTF8))
        self.menuMode.setTitle(QtGui.QApplication.translate("MainWindow", "Mode", None, QtGui.QApplication.UnicodeUTF8))
        self.actionExit.setText(QtGui.QApplication.translate("MainWindow", "Exit", None, QtGui.QApplication.UnicodeUTF8))
        self.actionEvent_Viewer.setText(QtGui.QApplication.translate("MainWindow", "Event Viewer", None, QtGui.QApplication.UnicodeUTF8))
        self.actionLog_Viewer.setText(QtGui.QApplication.translate("MainWindow", "Log Viewer", None, QtGui.QApplication.UnicodeUTF8))

