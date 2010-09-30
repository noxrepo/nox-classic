'''
Monitoring view for drawn topology

@author Kyriakos Zarifis
'''
from PyQt4 import QtGui, QtCore
from view import View
import random
import simplejson as json

'''
from nox.ripcordapps.dispatch_server.ripcord_pb2 import Vertex, Edge, Path, \
Tunnel, Tunnels, TunnelsRequest, Topology, DisplayTunnel, NewTunnelRequest, \
SwitchQuery, Generic, SwitchQueryReply, TopologyRequest, TopologyReply
'''

class Monitoring_View(View):

    def __init__(self, topoWidget):
        View.__init__(self, topoWidget)
        
        self.name = "Monitoring"
        
        # Monitoring view buttons
        mrSvcBtn = QtGui.QPushButton('&MapReduce Cluster')
        storageSvcBtn = QtGui.QPushButton('&Storage Cluster')
        resetSvcBtn = QtGui.QPushButton('&Reset')
        infoBtn = QtGui.QPushButton('What is Monitoring?')
        
        '''
        self.connect(mrSvcBtn, QtCore.SIGNAL('clicked()'),
                    self.show_map_reduce_cluster)
        self.connect(storageSvcBtn, QtCore.SIGNAL('clicked()'),
                    self.show_storage_cluster)
        self.connect(resetSvcBtn, QtCore.SIGNAL('clicked()'),
                     self.reset_services)
        '''
        self.connect(infoBtn, QtCore.SIGNAL('clicked()'),
                     self.show_monitoring_info)
       
        self.buttons.append(mrSvcBtn)
        self.buttons.append(storageSvcBtn)
        self.buttons.append(resetSvcBtn)
        self.buttons.append(infoBtn)

        for b in self.buttons:
            b.setCheckable(True)
        #self.buttons[0].setChecked(True)
        
        self.stats = {}  # maps tuples (dpid, port) to utilization
        self.service_subset = set([])
        self.service_name = ""

        # Connect methods to signals
        #self.get_port_stats_sig.connect( self.get_port_stats )
        # Connect to signal from communication to handle switch query replies
        #self.topologyInterface.switch_query_reply_received_signal.connect( \
        #    self.show_stats_reply )

        #self.topologyInterface.topology_received_signal.connect( \
        #    self.show_topology_reply )
        
        self.topologyInterface.monitoring_received_signal.connect( \
            self.got_monitoring_msg )
            
        # Subscribe for linkutils
        msg = {}
        msg ["type"] = "monitoring"
        msg ["command"] = "subscribe"
        msg ["msg_type"] = "linkutils"
        self.topologyInterface.send( msg )    
            
    def get_stats(self, dpid, command):
        queryMsg = {}
        queryMsg["type"] = "monitoring"
        queryMsg["dpid"] = dpid
        queryMsg["command"] = command
        self.topologyInterface.send( queryMsg )
        
    def got_monitoring_msg(self, msg):
        jsonmsg = json.loads(str(msg))
        if jsonmsg["msg_type"] == "linkutils":
            #print jsonmsg
            self.update_stats(jsonmsg["utils"])
        else:
            self.show_stats_reply(jsonmsg)

    def get_port_stats( self, dpid ):
        self.logDisplay.setText( "Query port stats from dpid: 0x%x" % (dpid) )
        self.get_stats(dpid, "portstats")

    def get_table_stats( self, dpid ):
        self.get_stats(dpid, "tablestats")

    def get_aggregate_stats( self, dpid ):
        self.get_stats(dpid, "aggstats")

    def get_latest_snapshot( self, dpid ):
        self.get_stats(dpid, "latestsnapshot")

    def get_flow_stats( self, dpid ):
        self.get_stats(dpid, "flowstats")

    def get_queue_stats( self, dpid ):
        self.get_stats(dpid, "queuestats")

    def show_stats_reply( self, replyMsg ):
        if replyMsg["msg_type"] == "portstats":
            reply = json.loads( replyMsg["data"] )
            line = ""
            line += str(len(reply[0])) + " ports\n"
            for item in reply[0]:
                line += "--------------------\n" + \
                        "Port number : " + str(item['port_no']) + "\n" + \
                        "tx bytes    : " + str(item['tx_bytes']) + "\n" + \
                        "rx bytes    : " + str(item['rx_bytes']) + "\n" + \
                        "tx packets  : " + str(item['tx_packets']) + "\n" + \
                        "rx packets  : " + str(item['rx_packets']) + "\n" + \
                        "tx dropped  : " + str(item['tx_dropped']) + "\n" + \
                        "rx dropped  : " + str(item['rx_dropped']) + "\n" + \
                        "tx errors   : " + str(item['tx_errors']) + "\n" + \
                        "rx errors   : " + str(item['rx_errors']) + "\n" + \
                        "collisions  : " + str(item['collisions']) + "\n" + \
                        "rx over err : " + str(item['rx_over_err']) + "\n" + \
                        "rx frame err: " + str(item['rx_frame_err'])+ "\n" + \
                        "rx crc err  : " + str(item['rx_crc_err']) + "\n" + \
                        "--------------------\n"
            self.logDisplay.setText("Query results came back (dpid=0x%x):\n%s"\
                                         % (replyMsg["dpid"],line))
        elif replyMsg["msg_type"] == "tablestats":
            reply = json.loads( replyMsg["data"] )
            line = ""
            line += str(len(reply[0])) + " tables\n"
            for item in reply[0]:
                line += "--------------------\n" + \
                "Table name    : " + str(item['name']) + "\n" + \
                "Table id      : " + str(item['table_id']) + "\n" + \
                "Max entries   : " + str(item['max_entries']) + "\n" + \
                "Active count  : " + str(item['active_count']) + "\n" + \
                "Lookup count  : " + str(item['lookup_count']) + "\n" + \
                "Matched count : " + str(item['matched_count']) + "\n" + \
                "--------------------\n"
            self.logDisplay.setText("Query results came back (dpid=0x%x):\n%s"\
                                        % (replyMsg["dpid"],line))
        elif replyMsg["msg_type"] == "aggstats":
            reply = json.loads( replyMsg["data"] )
            line = ""
            line += "--------------------\n" + \
            "Packet count : " + str(reply[0]['packet_count']) + "\n" + \
            "Byte count   : " + str(reply[0]['byte_count']) + "\n" + \
            "Flow count   : " + str(reply[0]['flow_count']) + "\n" + \
            "--------------------\n"
            self.logDisplay.setText("Query results came back (dpid=0x%x):\n%s"\
                                         % (replyMsg["dpid"],line))
        elif replyMsg["msg_type"] == "flowstats":
            reply = json.loads( replyMsg["data"] )
            line = ""
            line += str(len(reply[0])) + " flows\n"
            for item in reply[0]:
                line += "--------------------\n" + \
                "Packet count : " + str(item['packet_count']) + "\n" + \
                "Hard timeout : " + str(item['hard_timeout']) + "\n" + \
                "Byte count   : " + str(item['byte_count']) + "\n" + \
                "Idle timeout : " + str(item['idle_timeout']) + "\n" + \
                "Duration nsec: " + str(item['duration_nsec']) + "\n" + \
                "Duration sec : " + str(item['duration_sec']) + "\n" + \
                "Priority     : " + str(item['priority']) + "\n" + \
                "Cookie       : " + str(item['cookie']) + "\n" + \
                "Table id     : " + str(item['table_id']) + "\n" + \
                "Match        : " + "\n"
                for key in item['match']:
                    line += "\t" + key + ":" + str(item['match'][key]) + "\n"
                line += "--------------------\n"
            self.logDisplay.setText("Query results came back (dpid=0x%x):\n%s"\
                                         % (replyMsg["dpid"],line))
        elif replyMsg["msg_type"] == "queuestats":
            reply = json.loads( replyMsg["data"] )
            line = ""
            line += str(len(reply[0])) + " queues\n"
            for item in reply[0]:
                line += "--------------------\n" + \
                "Port number : " + str(item['port_no']) + "\n" + \
                "Queue id    : " + str(item['queue_id']) + "\n" + \
                "tx bytes    : " + str(item['tx_bytes']) + "\n" + \
                "tx packets  : " + str(item['tx_packets']) + "\n" + \
                "tx errors   : " + str(item['tx_errors']) + "\n" + \
                "--------------------\n"
            self.logDisplay.setText("Query results came back (dpid=0x%x):\n%s"\
                                         % (replyMsg["dpid"],line))
        elif replyMsg["msg_type"] == "latestsnapshot":
            reply = json.loads( replyMsg["data"] )
            line = ""
            line += "--------------------\n" + \
            "Collection epoch : " + str(reply['collection_epoch']) + "\n" + \
            "Epoch delta      : " + str(reply['epoch_delta']) + "\n" + \
            "Time since delta : " + str(reply['time_since_delta']) + "\n" + \
            "Timestamp        : " + str(reply['timestamp']) + "\n" + \
            "Number of flows  : " + str(reply['number_of_flows']) + "\n" + \
            "Bytes in flows   : " + str(reply['bytes_in_flows']) + "\n" + \
            "Packets in flows : " + str(reply['packets_in_flows']) + "\n" + \
            "Total tx bytes   : " + str(reply['total_tx_bytes']) + "\n" + \
            "Total rx bytes   : " + str(reply['total_rx_bytes']) + "\n" + \
            "Total tx packets : " + str(reply['total_tx_packets']) + "\n" + \
            "Total rx packets : " + str(reply['total_rx_packets']) + "\n" + \
            "Total tx packets dropped : " \
                       + str(reply['total_tx_packets_dropped']) + "\n" + \
            "Total rx packets dropped : " \
                       + str(reply['total_rx_packets_dropped']) + "\n" + \
            "Total tx errors  : " + str(reply['total_tx_errors']) + "\n" + \
            "Total rx errors  : " + str(reply['total_rx_errors']) + "\n" + \
            "Delta tx bytes   : " + str(reply['delta_tx_bytes']) + "\n" + \
            "Delta rx bytes   : " + str(reply['delta_rx_bytes']) + "\n" + \
            "Delta tx packets : " + str(reply['delta_tx_packets']) + "\n" + \
            "Delta rx packets : " + str(reply['delta_rx_packets']) + "\n" + \
            "Delta tx packets dropped : " \
                       + str(reply['delta_tx_packets_dropped']) + "\n" + \
            "Delta rx packets dropped : " \
                       + str(reply['delta_rx_packets_dropped']) + "\n" + \
            "Delta tx errors  : " + str(reply['delta_tx_errors']) + "\n" + \
            "Delta rx errors  : " + str(reply['delta_rx_errors']) + "\n"
            
            # Add in port info
            if len(reply['ports']) > 0:
                line += "\nPort info: \n"
                for port_num in reply['ports']:
                    port_info = reply['ports'][port_num]
                    line += "Port number : " + str(port_num) + "\n" + \
                    "Port name : " + \
                         port_info['port_cap']['port_name'] + "\n" + \
                    "Enabled   : " + \
                         str(port_info['port_cap']['port_enabled']) + "\n" + \
                    "Max speed (gbps)  : " + \
                        str(port_info['port_cap']['max_speed']/1e9) + "\n" \
                    "Full duplex       : " + \
                        str(port_info['port_cap']['full_duplex']) + "\n" + \
                    "Total tx bytes    : " + \
                        str(port_info['total_tx_bytes']) + "\n" + \
                    "Total rx bytes    : " + \
                        str(port_info['total_rx_bytes']) + "\n" + \
                    "Total tx packets  : " + \
                        str(port_info['total_tx_packets']) + "\n" + \
                    "Total rx packets  : " + \
                        str(port_info['total_rx_packets']) + "\n" + \
                    "Total tx packets dropped : " + \
                        str(port_info['total_tx_packets_dropped']) + "\n" + \
                    "Total rx packets dropped : " + \
                        str(port_info['total_rx_packets_dropped']) + "\n" + \
                    "Total tx errors : " + \
                        str(port_info['total_tx_errors']) + "\n" + \
                    "Total rx errors : " + \
                        str(port_info['total_rx_errors']) + "\n" + \
                    "Delta tx bytes   : " + \
                        str(port_info['delta_tx_bytes']) + "\n" + \
                    "Delta rx bytes   : " + \
                        str(port_info['delta_rx_bytes']) + "\n" + \
                     "Delta tx packets : " + \
                        str(port_info['delta_tx_packets']) + "\n" + \
                     "Delta rx packets : " + \
                        str(port_info['delta_rx_packets']) + "\n" + \
                     "Delta tx packets dropped : " + \
                        str(port_info['delta_tx_packets_dropped']) + "\n" + \
                     "Delta rx packets dropped : " + \
                        str(port_info['delta_rx_packets_dropped']) + "\n" + \
                     "Delta tx errors : " + \
                        str(port_info['delta_tx_errors']) + "\n" + \
                     "Delta rx errors : " + \
                        str(port_info['delta_rx_errors']) + "\n\n"
            line += "--------------------\n"
            
            self.logDisplay.setText("Query results came back (dpid=0x%x):\n%s"\
                                         % (replyMsg["dpid"],line))
        else:
            self.logDisplay.setText( "Query results came back: %s" % \
                                     ( str(replyMsg) ) )
        
    def update_stats(self, utils):
        ''' updates link stats from dispatch_server message '''
        self.stats = {}
        for util in utils:
        #    print( "dpid: %d, port: %d, tx: %f, rx: %f" % \
        #               (util.dpid, util.port, util.gbps_transmitted, 
        #                util.gbps_received) )
            self.stats[(util["dpid"], util["port"])] = \
                            (util["gbps_transmitted"] + util["gbps_received"]) / 2
        #print self.stats[(1, 3)]
        
    def link_color(self, link):
        # Co-opted from the elastictree view
        # reflected by shades of colors based on utilizations
        # assumes 1 GB links
        srcID = link.source.dpid
        srcPort = link.sport
        dstID = link.dest.dpid
        dstPort = link.dport

        if not (srcID, srcPort) in self.stats and \
                not (dstID, dstPort) in self.stats:
            return QtCore.Qt.white

        if not (srcID, srcPort) in self.stats:
            util = self.stats[(dstID, dstPort)]
        elif not (dstID, dstPort) in self.stats:
            util = self.stats[(srcID, srcPort)]
        else:
            util1 = self.stats[(srcID, srcPort)]
            util2 = self.stats[(dstID, dstPort)]
            util = (util1 + util2) / 2

        '''
        print link.source.id
        print link.dest.id
        if link.source.id == "1":
            print util
        '''

        #print util
        if util >= 0.8:
            return QtCore.Qt.red
        if util >= 0.3:
            return QtCore.Qt.yellow
        if util >= 0.0:
            return QtCore.Qt.green
        return QtCore.Qt.white

    def link_pattern(self, link):
        pattern = QtCore.Qt.SolidLine
        return pattern
        
    def node_color(self, node):
        #print "node color in monitoring view" 
        '''
        if node.dpid in self.service_subset:
            if self.service_name == "serviceB":
                return QtGui.QColor(QtCore.Qt.yellow)
            else:
                return QtGui.QColor(QtCore.Qt.blue)
        else:
        '''
        return QtGui.QColor(QtCore.Qt.green)
        
    def show_map_reduce_cluster(self):
        for b in self.buttons:
            b.setChecked(False)
        self.buttons[0].setChecked(True)
        self.subview = "MapReduce Cluster" 
        self.filter_map_reduce()
            
    def show_storage_cluster(self):
        for b in self.buttons:
            b.setChecked(False)
        self.buttons[1].setChecked(True)
        self.subview = "Storage Cluster" 
        self.filter_storage()

    def reset_services( self ):
        for b in self.buttons:
            b.setChecked(False)
        self.buttons[2].setChecked(True)
        self.service_name = ""
        self.service_subset.clear()
        # Force a repaint
        self.topoWidget.topologyView.updateAll()

    def filter_map_reduce(self):
        self.get_filtered_topology( "serviceA" )

    def filter_storage(self):
        self.get_filtered_topology( "serviceB" )

    def get_filtered_topology( self, subset_name ):
        # Construct and send topo request message                           
        topoRequestMsg = TopologyRequest()
        topoRequestMsg.subset_name = subset_name
        self.topologyInterface.send( topoRequestMsg )

    def show_topology_reply( self, topoMsg ):
        if topoMsg.subset_name == "serviceA" or \
                topoMsg.subset_name == "serviceB":
            print( "got topo for service" )
            # Only do something for these two specific services
            self.service_name = topoMsg.subset_name
            self.service_subset.clear()
            # Fill in service nodes
            for item in topoMsg.nodes:
                #print( "adding service item %d" % (item.dpid) )
                self.service_subset.add( item.dpid )
        else:
            print( "got full topo" )
            self.service_subset.clear()

        # Force a re-paint
        self.topoWidget.topologyView.updateAll()

    def show_monitoring_info(self):
        for b in self.buttons:
            b.setChecked(False)
        self.buttons[3].setChecked(True)
        self.subview = "What is Monitoring"
        info_popup = InfoPopup(self)
        info_popup.exec_()
        
class InfoPopup(QtGui.QDialog):
    ''' popup showing basic background for Monitoring '''

    def __init__(self, parent=None):
        ''' Sets up graphics for popup '''
        self.parent = parent
        QtGui.QWidget.__init__(self)
        self.setWindowTitle("Monitoring Basic Info")
        self.resize(500, 150)
        self.combo = QtGui.QGroupBox(self)

        ok = QtGui.QPushButton("Ok")
        self.connect(ok, QtCore.SIGNAL('clicked()'), self.ok)
        self.hbox = QtGui.QHBoxLayout()
        self.hbox.addStretch(1)
        self.hbox.addWidget(ok)

        self.vbox = QtGui.QVBoxLayout()
        grid = QtGui.QGridLayout()
        msg1 = "Monitoring visualizes switch and link health/status information" 
        msg2 = "(e.g., switch flow tables, link utilizations, packet drops/errors, etc.)."
        msg3 = "Monitoring also allows network administrators to view and manage"
        msg4 = "services (applications) deployed in the network."
        l = QtGui.QLabel(msg1)
        m = QtGui.QLabel(msg2)
        n = QtGui.QLabel(msg3)
        o = QtGui.QLabel(msg4)
        grid.addWidget(l, 1, 1)
        grid.addWidget(m, 2, 1)
        grid.addWidget(n, 3, 1)
        grid.addWidget(o, 4, 1)

        self.combo.setLayout(self.vbox)
        self.vbox.addLayout(grid)
        self.vbox.addLayout(self.hbox)
        self.vbox.addStretch(1)

    def ok(self):
        self.accept()
