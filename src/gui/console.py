'''
Console Widget, used for sending json messages to NOX

@author Kyriakos Zarifis
'''

from PyQt4 import QtGui, QtCore
from communication import ConsoleInterface

class ConsoleWidget(QtGui.QWidget):
    def __init__(self, parent=None):
        self.parent = parent
        QtGui.QWidget.__init__(self, parent)
        
        # Handle to logDisplay
        self.logDisplay = self.parent.logWidget.logDisplay
        
        # Handle to sqldg
        self.curs = self.parent.logWidget.curs
        
        # Configure Widget
        self.label = QtGui.QLabel('Send JSON command to NOX')     
        self.consoleEdit = QtGui.QLineEdit()
        self.consoleEdit.setText("{\"type\":\"lavi\",\"command\":\"request\",\"node_type\":\"all\"}")
        
        '''
        p = QtGui.QPalette()
        p.setColor(QtGui.QPalette.Active, QtGui.QPalette.Base, QtCore.Qt.black)
        p.setColor(QtGui.QPalette.Inactive, QtGui.QPalette.Base, QtCore.Qt.black)
        self.consoleEdit.setPalette(p)
        #self.consoleEdit.setTextColor(QtCore.Qt.darkGreen)
        '''   
        sendCmdBtn = QtGui.QPushButton("&Send")        
        self.connect(sendCmdBtn, QtCore.SIGNAL('clicked()'), self.send_cmd)

        grid = QtGui.QGridLayout()
        grid.setSpacing(10)

        grid.addWidget(self.label, 1, 0)
        grid.addWidget(self.consoleEdit, 2, 0)
        grid.addWidget(sendCmdBtn, 2, 1)
        
        self.setLayout(grid)
        
        self.consoleInterface = ConsoleInterface(self)
        
    def send_cmd(self):
        self.curs.execute("select distinct component from messages")
        print self.curs
        if "jsonmessenger" not in self.curs:
            self.logDisplay.setText("jsonmessenger is not running")
        else:
            cmd = str(self.consoleEdit.text())
            self.consoleInterface.send_cmd(cmd)
        
            
    def keyPressEvent(self, event):
        key = event.key()

        if key == QtCore.Qt.Key_Enter:
            self.send_cmd()
                
