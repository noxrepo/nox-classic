'''
FlowTracer GUI view 

@author Kyriakos Zarifis (kyr.zarifis@gmail.com)
'''

from PyQt4 import QtGui, QtCore
from view import View
import simplejson as json

class Flow_Tracer_View(View):
    def __init__(self, topoWidget):
        View.__init__(self, topoWidget, "FlowTracer")    

        # Buttons
        infoBtn = QtGui.QPushButton('What is FlowTracer?')
        self.connect(infoBtn, QtCore.SIGNAL('clicked()'), self.showInfo)
        traceBtn = QtGui.QPushButton('Trace!')
        self.connect(traceBtn, QtCore.SIGNAL('clicked()'), self.trace_flow)
        self.buttons.append(infoBtn)
        self.buttons.append(traceBtn)
        
        # Signals
        self.topologyInterface.flowtracer_received_signal.connect( \
            self.got_json_msg )
        
        # Subscribe to messages from backend 
        msg = {}
        msg ["type"] = "flowtracer"
        msg ["command"] = "subscribe"
        msg ["msg_type"] = "highlight"
        self.topologyInterface.send( msg ) 
        
        self.highlighted_path = []
        
    def node_color(self, node):
        pass

    def link_color(self, link):
        s = link.source.id
        d = link.dest.id
        l = str((min(s,d))) +'-'+str(max((s,d)))
        
        if l in self.highlighted_path:
                return QtCore.Qt.red
        return QtCore.Qt.gray

    def link_pattern(self, link):
        pass
        
    def trace_flow(self):
        # Reset previously highlighted links  
        self.highlighted_path = []  
        
        # Get flow match info from selected flow entry
        text = str(self.infoDisplay.selectedRowToString())
        start = text.find("Match : ")
        if start < 0:
            self.flowEntryNotSelectedPopup()
            return
        start = start + 9
        stop = text.find("Counters : ")
        match = text[start:stop-3]
        
        matcharray = match.split("  ")
        
        match = {}
        
        for item in matcharray:
            field, value = item.split(":")
            value = value[1:]
            # convert values from strings to correct types
            if (field == 'in_port') or \
                    (field == 'tp_src') or \
                    (field == 'tp_dst') or \
                    (field == 'nw_proto') or \
                    (field == 'nw_dst_n_wild') or \
                    (field == 'dl_vlan') or \
                    (field == 'dl_vlan_pcp') or \
                    (field == 'nw_tos'):
                value = int(value)
            elif (field == 'dl_src') or \
                    (field == 'dl_dst') or \
                    (field == 'dl_type'):
                value = int(value,16)
            elif (field == 'nw_src') or \
                    (field == 'nw_dst'):
                value = self.dottedQuadToNum(value)
            match[field] = value
        
        text = str(self.infoDisplay.indexAt(QtCore.QPoint(0,0)).data().toString())
        dpid = int(text[text.find("=")+1:text.find(")")],16)
        
        self.send_flowtrace_request(dpid, match)
        
    def dottedQuadToNum(self, ip):
        "convert decimal dotted quad string to long integer"
        hexn = ''.join(["%02X" % long(i) for i in ip.split('.')])
        #print "converted", ip, "to", long(hexn, 16)
        return long(hexn, 16)
    
    """Communication with the NOX"""   
    
    def send_flowtrace_request(self, dpid, match):
        msg = {}
        msg["type"] = "flowtracer"
        msg["command"] = "trace"
        msg["match"] = match
        msg["dpid"] = dpid
        self.topologyInterface.send(msg)
    
    def got_json_msg(self, msg):
        ''' Handle json messages received from NOX flowtracer component '''
        jsonmsg = json.loads(str(msg))
        
        if jsonmsg["type"] != "flowtracer":
            return
        
        if jsonmsg["msg_type"] == "highlight":
            p = jsonmsg['path']
            
        # Put links that we'll highlight here
        links = []
        
        # Add first link
        print "path", p
        minend=min(self.topologyView.nodes[p[1]].neighbors[p[0]], p[1])
        maxend=max(self.topologyView.nodes[p[1]].neighbors[p[0]], p[1])
        firstlink = minend+'-'+maxend
        links.append(firstlink)
        
        # Add last link
        minend=min(self.topologyView.nodes[p[len(p)-2]].neighbors[p[len(p)-1]],\
            p[len(p)-2])
        maxend=max(self.topologyView.nodes[p[len(p)-2]].neighbors[p[len(p)-1]],\
            p[len(p)-2])
        lastlink = minend+'-'+maxend
        links.append(lastlink)
        
        # Add intermediate links
        p = p[1:len(p)-1]
        for i in range(0,len(p)-1):
            links.append( (min((p[i],p[i+1]))+'-'+max((p[i],p[i+1]))) )
        
        self.highlighted_path = links
        
        self.topologyView.updateLinks()
        
    def showInfo(self):
        ''' Routing view information popup'''
        self.buttons[0].setChecked(True)

        msgBox = QtGui.QMessageBox()
        msgBox.setWindowTitle("FlowTracer View")
        msgBox.setText("FlowTracer view allows you to select a flow "+\
            "entry from the panel on the left and trace the path that a "+\
            "packet matching this rule would follow.")
        msgBox.exec_()
    
    def flowEntryNotSelectedPopup(self):
        msgBox = QtGui.QMessageBox()
        msgBox.setWindowTitle("FlowTracer")
        msgBox.setText("Please select a flow entry on the info panel")
        msgBox.exec_()
