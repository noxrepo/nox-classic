'''
Base class for drawn topology views

Custom topology vies extend this by optionally adding secondary buttons and
coloring behavior. Any logic is included in the custom view files.
(for example, TE_View has the notion of tunnels etc)

@author Kyriakos Zarifis
'''
from PyQt4 import QtGui, QtCore

class View(QtGui.QWidget):
    def __init__(self, topoWidget):
        QtGui.QWidget.__init__(self)
        self.topoWidget = topoWidget
        self.topologyInterface = self.topoWidget.topologyView.topologyInterface
        self.logDisplay = self.topoWidget.parent.logWidget.logDisplay
        self.buttons = []       # view-specific buttons, added by derived views
        self.name = ""          # must be initialized be derived views
        
    def show(self):
        # Give draw access
        self.topoWidget.topologyView.drawAccess = self.name
        
        # Clear secondary bar
        for btn in self.topoWidget.changeViewWidget.secondaryBtns:
            self.topoWidget.changeViewWidget.grid.removeWidget(btn) 
            btn.hide()
        # Add secondary bar, if any defined in derived class
        for i in range(0,len(self.buttons)): 
            self.topoWidget.changeViewWidget.grid.addWidget(self.buttons[i], 1, i)
            self.buttons[i].show()
            
        self.topoWidget.changeViewWidget.secondaryBtns = self.buttons
        
        #self.topoView.updateAll()
