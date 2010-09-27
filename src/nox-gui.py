#!/usr/bin/python
'''
NOX GUI
This file creates the main application window, sets up the layout and invokes
the GUI's widgets.
The left panel (log) is used for displaying context-specific information.
The right panel (topology) is an interactive display of the topology
The bottom right pane (console) is a frontend for communication with
jsonmessenger. 

@author Kyriakos Zarifis
'''

import struct
import sys

from PyQt4 import QtGui, QtCore

import gui.log as log
import gui.topology as topology
import gui.console as console
import gui.Popup as Popup
       
class MainWindow(QtGui.QMainWindow):
    
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

        # Configure layout
        self.setWindowTitle('NOX Graphical User Interface')
        self.resize(1280, 800)
        self.statusBar().showMessage('Ready')        
        self.center()
        
        # Messenger socket:
        if len(sys.argv) > 1:
            self.noxip = sys.argv[1]
        else:
            self.noxip = "127.0.0.1"
        self.noxport = 2703 #messenger port

        self.logWidget = log.LogWidget(self)
        self.left = self.logWidget
                
        self.topoWidget = topology.TopoWidget(self) 
        self.consoleWidget = console.ConsoleWidget(self)  
        
        self.rightvbox = QtGui.QVBoxLayout()
        self.rightvbox.addWidget(self.topoWidget)
        self.rightvbox.addWidget(self.consoleWidget)
        self.right = QtGui.QWidget()
        self.right.setLayout(self.rightvbox)
        
        self.splitter = QtGui.QSplitter(QtCore.Qt.Horizontal)
        self.splitter.addWidget(self.left)
        self.splitter.addWidget(self.right)
        
        self.setCentralWidget(self.splitter)

        # Actions
        start = QtGui.QAction(QtGui.QIcon('gui/icons/logo.png'), 'Start', self)
        start.setShortcut('Ctrl+S')
        start.setStatusTip('Start NOX')
        self.connect(start, QtCore.SIGNAL('triggered()'), self.start_nox)        
        
        switch_to_log = QtGui.QAction(QtGui.QIcon('gui/icons/log.png'),'Log View',self)
        switch_to_log.setShortcut('Ctrl+1')
        switch_to_log.setStatusTip('Switch to system log view')
        self.connect(switch_to_log, QtCore.SIGNAL('triggered()'), self.show_log)
        
        switch_to_topo = QtGui.QAction(QtGui.QIcon('gui/icons/topo.png'),'Topology View',self)
        switch_to_topo.setShortcut('Ctrl+2')
        switch_to_topo.setStatusTip('Switch to topology view')
        self.connect(switch_to_topo, QtCore.SIGNAL('triggered()'), self.show_topo)                
                
        switch_to_split = QtGui.QAction(QtGui.QIcon('gui/icons/split.png'),'Split View',self)
        switch_to_split.setShortcut('Ctrl+3')
        switch_to_split.setStatusTip('Switch to split view')
        self.connect(switch_to_split, QtCore.SIGNAL('triggered()'), self.show_split)
        
        toggle_console = QtGui.QAction(QtGui.QIcon('gui/icons/split.png'),'Show/Hide Console',self)
        toggle_console.setShortcut('Ctrl+4')
        toggle_console.setStatusTip('Show/Hide Console')
        self.connect(toggle_console, QtCore.SIGNAL('triggered()'), self.toggle_show_console)
        
        exit = QtGui.QAction(QtGui.QIcon('gui/icons/exit.png'), 'Exit', self)
        exit.setShortcut('Ctrl+Q')
        exit.setStatusTip('Exit application')
        self.connect(exit, QtCore.SIGNAL('triggered()'), QtCore.SLOT('close()'))
        #self.connect(exit, QtCore.SIGNAL('triggered()'), self.graceful_close)
        
        self.statusBar()

        # Configure Menubar
        menubar = self.menuBar()
        file_menu = menubar.addMenu('&File')
        file_menu.addAction(start)
        file_menu.addAction(exit)
        view_menu = menubar.addMenu('&View')
        view_menu.addAction(switch_to_log)
        view_menu.addAction(switch_to_topo)
        view_menu.addAction(switch_to_split)
        view_menu.addAction(toggle_console)
        components_menu = menubar.addMenu('&Components')
        components_menu.addAction('Installed Components')
        components_menu.addAction('Active Components')
        components_menu.addAction('Install Component...')
        help_menu = menubar.addMenu('&Help')
        #file.addAction(About)

        # Configure Toolbar
        toolbar = self.addToolBar('Exit')
        toolbar.addAction(start)
        toolbar.addAction(switch_to_log)
        toolbar.addAction(switch_to_topo)
        toolbar.addAction(switch_to_split)
        toolbar.addAction(exit)
        
    def center(self):
        screen = QtGui.QDesktopWidget().screenGeometry()
        size =  self.geometry()
        self.move((screen.width()-size.width())/2, (screen.height()-size.height())/2)
       
    def closeEvent(self, event):
        '''
        reply = QtGui.QMessageBox.question(self, 'Exit NOX',
            "Are you sure to quit?", QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
        if reply == QtGui.QMessageBox.Yes:
            self.topoWidget.topologyView.topologyInterface.stop()
            event.accept()
        else:
            event.ignore()
        '''
        self.logWidget.logInterface.running = False
        event.accept()
        
    def start_nox(self):
        popup = Popup.StartComboBox(self)
        popup.exec_()
    
    def show_log(self):
        self.right.hide()
        self.left.show()
        
    def show_topo(self):
        self.right.show()
        self.left.hide()
        
    def show_split(self):
        self.right.show()
        self.left.show()
        
    def toggle_show_console(self):
        if self.consoleWidget.isHidden():
            self.consoleWidget.show()
        else:
            self.consoleWidget.hide()
                    
app = QtGui.QApplication(sys.argv)
app.setWindowIcon(QtGui.QIcon('gui/icons/logo.ico'))
noxgui = MainWindow()
noxgui.show()
sys.exit(app.exec_())


