from nox.lib import core, openflow
from nox.lib.core import Component, Flow_stats_in_event
import nox.lib.pyopenflow as of
import simplejson as json
#from socket import ntohs, htons
from nox.lib.netinet.netinet import c_ntohl
from nox.coreapps.pyrt.pycomponent import CONTINUE
from nox.netapps.topology.pytopology import pytopology


from nox.coreapps.messenger.pyjsonmsgevent import JSONMsg_event
import logging
               
log = logging.getLogger('flowtracer')
        
class flowtracer(Component):
    def __init__(self, ctxt):
        Component.__init__(self, ctxt)

    def install(self):
        # Register for json messages from the gui
        self.register_handler( JSONMsg_event.static_get_name(), \
                         lambda event: self.handle_jsonmsg_event(event))
        # Register for flow_stats replies                 
        self.register_handler( Flow_stats_in_event.static_get_name(), \
                         lambda event: self.handle_flow_stats_in(event))
                         
        self.topology = self.resolve(pytopology)                 
                         
        # Subscribers for json messages
        self.subscribers = {}
        
        # Currently traced flow
        self.match = None
        
        # XID of the currently pending flow stats request (one at a time)
        self.pending_query_xid = 0
        
        # List of dpids on the path of the currently traced flow
        self.current_path = []
        
    def getInterface(self):
        return str(flowtracer)

    def trace_flow(self, _match, dpid):
        ''' Trace flow entry from a given dp'''
        # Build match for flowstats request
        match = of.ofp_match()
        
        print _match
        
        match.wildcards = of.OFPFW_ALL
        
        if 'dl_vlan' in _match:
            match.dl_vlan = _match['dl_vlan']
            match.wildcards -= of.OFPFW_DL_VLAN
        if 'dl_vlan_pcp' in _match:
            match.dl_vlan_pcp = _match['dl_vlan_pcp']
            match.wildcards -= of.OFPFW_DL_VLAN_PCP
        if 'nw_tos' in _match:
            match.nw_tos = _match['nw_tos']
            match.wildcards -= of.OFPFW_NW_TOS
        if 'nw_proto' in _match:
            match.nw_proto = _match['nw_proto']
            match.wildcards -= of.OFPFW_NW_PROTO
        if 'tp_src' in _match:
            match.tp_src = _match['tp_src']
            match.wildcards -= of.OFPFW_TP_SRC
        if 'tp_dst' in _match:
            match.tp_dst = _match['tp_dst']
            match.wildcards -= of.OFPFW_TP_DST
        if 'nw_src' in _match:
            match.nw_src = _match['nw_src']
            match.wildcards -= of.OFPFW_NW_SRC_ALL
        if 'nw_dst' in _match:
            match.nw_dst = _match['nw_dst']
            match.wildcards -= of.OFPFW_NW_DST_ALL
        '''
        if 'dl_vlan' in _match:
            if this is commented out, it doesn't match although vlan=65535
            # what is the expected format/type of dl_vlan ?
            print _match['dl_vlan']
            match.dl_vlan = _match['dl_vlan']
            match.wildcards -= of.OFPFW_DL_VLAN
        if 'dl_src' in _match:
            #if this is commented out, match's format gets bad (pack() doesn't work)
            # what is the expected format/type of dl_src/dl_dst ?
            print _match['dl_src']
            match.dl_src = _match['dl_src']
            match.wildcards -= of.OFPFW_DL_SRC
        if 'dl_dst' in _match:
            print _match['dl_dst']
            match.dl_dst = _match['dl_dst']
            match.wildcards -= of.OFPFW_DL_DST
        '''
        
        self.pending_query_xid = self.send_flow_stats_request(dpid, match)
        
    def send_flow_stats_request(self, dpid, match):
        """Send a flow stats request to a switch (dpid).
        @param dpid - datapath/switch to contact                               
        @param match - ofp_match structure               
        """
        
        """
        # The API here is *UGLY*.
        Should be able to do smth like 'send_flowstats_request(dpid, match)'
        """
        # Create the stats request header
        request = of.ofp_stats_request()
        
        #TODO: replace with real XID code
        if not hasattr(self, 'xid'):
            xid = 9238
        else:
            xid = getattr(self, 'xid')
        if xid >= 0xFFffFFfe:
            xid = 9238
        setattr(self, 'xid', xid + 1)
        
        log.debug( "sending flow stats request xid: %d", xid )
        
        request.header.xid = xid
        request.header.type = openflow.OFPT_STATS_REQUEST
        request.type = openflow.OFPST_FLOW
        request.flags = 0
        
        # Create the stats request body
        body = of.ofp_flow_stats_request()
        body.match = match
        body.table_id = 0xff
        body.out_port = openflow.OFPP_NONE
        request.header.length = len(request.pack()) + len(body.pack())
        self.pending_query_xid = self.send_openflow_command(dpid, \
                    request.pack() + body.pack())
        
        return xid

    def handle_flow_stats_in(self, event):
        """ Extract 'action' from the matching flow entry 
            in order to see find the next hop
        """
        if c_ntohl(event.xid) == self.pending_query_xid:
            log.debug( "Got flow MY stats reply" )
            # See action(s) for this entry
            if len(event.flows) != 1:
                log.debug("matched to more than one flow entry! this should not happen")
            ports = []
            for action in event.flows[0]['actions']:
                if action['type'] == 0:
                    ports.append(action['port'])
            #elif ADD other action types here 
            print ports
            next_dpid = self.get_remote_dpid_for_port(event.datapath_id, ports[0])
            print next_dpid
        return CONTINUE
        
    def get_remote_dpid_for_port(self, dpid, port):
        print "outlinks", self.topology.get_outlinks(dpid, 3)
        """
        neighbors = self.topology.get_neighbors(dpid)
        for remote_dpid in neighbors:
            print "neighbor:", remote_dpid
            for link in get_outlinks(dpid, remote_dpid):
                print "port:", link.src
                if link.src == port:
                    return remote_dpid
        return null
        """
    """Communication with the GUI"""    
        
    def handle_jsonmsg_event(self, e):
        ''' Handle incoming json messenges '''
        msg = json.loads(e.jsonstring)
        
        if msg["type"] != "flowtracer" :
            return CONTINUE
            
        if not "command" in msg:
            log.debug( "Received message with no command field" )
            return CONTINUE
        
        if msg["command"] == "subscribe":
            # Add stream to interested entities for this msg_type
            if not msg["msg_type"] in self.subscribers:
                self.subscribers[msg["msg_type"]] = []     
            self.subscribers[msg["msg_type"]].append(e)
            
        elif msg["command"] == "trace":
            # Exctract the dpid and flow to be traced:
            match = msg["match"]  #(dict)
            dpid = msg["dpid"]
            
            self.trace_flow(match, dpid)
            
            return CONTINUE
        
    def send_to_gui(self, msg_type, data):
        # Construct message header
        msg = {}
        msg["type"] = "flowtracer"
        
        # Add msg_type-speficic payload
        if msg_type=="highlight":
            msg["msg_type"] = "highlight"
            msg["path"] = data
            
            if "highlight" in self.subscribers:
                for stream in self.subscribers["highlight"]:
                    stream.reply(json.dumps(msg))


def getFactory():
    class Factory:
        def instance(self, ctxt):
            return flowtracer(ctxt)

    return Factory()
