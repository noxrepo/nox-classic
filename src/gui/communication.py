'''
This module implements the communication between 
    - the topology view and the monitoring backend that feeds it
    - the log view and NOX's logger
    - the json command prompt and NOX's json messenger

@author Kyriakos Zarifis
'''
from twisted.internet import reactor
from PyQt4 import QtGui, QtCore


import SocketServer
import threading
import thread
import socket
import simplejson
import asyncore
from time import sleep

class LoggerInterface(QtCore.QThread, SocketServer.UDPServer):
    '''
    Server that listens for incoming NOX debug messages
    '''
    def __init__(self, parent):
        QtCore.QThread.__init__(self)
        self.logWidget = parent
        '''
        # First, connect to listening bouncer to register our ip:
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((self.logWidget.parent.noxip, 2221))
        except:
            print "no bouncer running"
        sock.close()
        
        self.running = True      
        '''
             
        SocketServer.UDPServer.__init__(self, ('localhost', 2222), LogHandler)
        
    def run(self):
        self.serve_forever()
        
        #server_thread = threading.Thread(target=self.serve_forever)
        #server_thread.setDaemon(True)
        #server_thread.start()
            
class LogHandler(SocketServer.BaseRequestHandler):    
    ''' 
    Handler for LoggerInterface
    '''        
    
    def handle(self):
        msg = self.request[0].strip()
        self.server.logWidget.dbWrapper.logMsgRcvdSignal.emit(msg+'\n')

class TopologyInterface(QtCore.QThread, QtGui.QWidget):

    ''' 
    Communicates with lavi through jsonmessenger in order to receive topology-view
    information. Used to communicate with jsonmessenger for other, component-
    specific event notification too. (eg new tunneltable etc)
    '''
    # Define signals that are emitted when messages are received
    # Interested custom views connect these signals to their slots
    
    # Signal used to notify te view that tunnels have been updated
    #tunnels_reply_received_signal = QtCore.pyqtSignal()
    
    # Signal used to notify te view that new TED info was received
    #ted_reply_received_signal = QtCore.pyqtSignal()
    
    # Signal used to notify te view that tunnels might have changed 
    #link_status_change_signal = QtCore.pyqtSignal()
    
    # Define a new signal that takes a SwitchQueryReply type as an argument
    #switch_query_reply_received_signal = QtCore.pyqtSignal()# SwitchQueryReply )
    
    # Signal used to notify monitoring view of new msg 
    monitoring_received_signal = QtCore.pyqtSignal(str)
    
    # Define a new signal that takes a Topology type as an argument
    topology_received_signal = QtCore.pyqtSignal(str)
   
    # Signal used to notify STP view of new msg 
    spanning_tree_received_signal = QtCore.pyqtSignal(str)
    
    # Signal used to notify routing view of new msg 
    routing_received_signal = QtCore.pyqtSignal(str)
    
    # Signal used to notify FlowTracer view of new msg 
    flowtracer_received_signal = QtCore.pyqtSignal(str)
    
    def __init__(self, topoView):
        QtCore.QThread.__init__(self)
        self.topoView = topoView    
        self.xid_counter = 1
        
        self.noxip = self.topoView.parent.parent.noxip
        self.noxport = self.topoView.parent.parent.noxport
        
        # Connect socket
        self.connected = False
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #self.sock.setblocking(0)
        try:
            self.sock.connect((self.noxip,self.noxport))
            self.connected = True
        except:
            self.retry_connection()
            
        #self.subscribe_for_topochanges()
        #self.subscribe_for_linkutils()
        
        self.listener = Listener(self)
        self.listener.start()
        #thread.start_new_thread(self.recv_data,())
        
        
    def retry_connection(self):
        print "Retrying connection to NOX...(is 'monitoring' component running?)"
        sleep(2)
        try:
            self.sock.connect((self.noxip,self.noxport))
            self.connected = True
        except:
            self.retry_connection()
    
    def send(self, msg):
        if not self.connected:
            print "Not connected to NOX"
            return
        if not "xid" in msg:
            msg["xid"] = self.xid_counter
        self.xid_counter += 1   
        #print 'Sending ...%s' % (msg) 
        self.sock.send(simplejson.dumps(msg))
        
    def shutdown(self):
        self.listener.stop()
        sock.shutdown(1)
        sock.close()
      
class Listener(QtCore.QThread):
    def __init__(self, p):
        QtCore.QThread.__init__(self)
        self.p = p
            
    def run(self):
        "Receive json messages, parse them and raise relevant signal"
        msg = ''
        outstanding_lbraces = 0
        end = False
        while 1:
            try:
                c = self.p.sock.recv(1)
                if c == '{':
                    outstanding_lbraces += 1
                elif c == '}':
                    outstanding_lbraces -= 1
                if outstanding_lbraces == 0:
                    end = True
                msg += c
            except:
                #Handle the case when server process terminates
                print "Server closed connection, thread exiting."
                #thread.interrupt_main()
                break
            if not msg:
                # Recv with no data, server closed connection
                print "Nothing to receive."
                #thread.interrupt_main()
                break
            if end:
                # Dispatch message
                jsonmsg = simplejson.loads(msg)
                if jsonmsg["type"] == "lavi":
                    self.p.topology_received_signal.emit(msg)
                elif jsonmsg["type"] == "monitoring":
                    self.p.monitoring_received_signal.emit(msg)
                elif jsonmsg["type"] == "spanning_tree":
                    self.p.spanning_tree_received_signal.emit(msg)
                elif jsonmsg["type"] == "sample_routing":
                    self.p.routing_received_signal.emit(msg)
                elif jsonmsg["type"] == "flowtracer":
                    self.p.flowtracer_received_signal.emit(msg)
                msg = ''
                outstanding_lbraces = 0
                end = False
  
class ConsoleInterface():
    '''
    Sends JSON commands to NOX
    '''        
    def __init__(self, parent):
        self.consoleWidget = parent
        ##NOX host
        self.nox_host = "localhost"
        ##Port number
        self.port_no = 2703
        
    def send_cmd(self, cmd=None, expectReply=False):        
        # if textbox empty, construct command
        if not cmd:
            print "sending dummy cmd"
            cmd = "{\"type\":\"lavi\",\"command\":\"request\",\"node_type\":\"all\"}"
        #Send command
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.nox_host,self.port_no))
        sock.send(cmd)
        if expectReply:
            print simplejson.dumps(simplejson.loads(sock.recv(4096)), indent=4)
        sock.send("{\"type\":\"disconnect\"}")
        sock.shutdown(1)
        sock.close() 
