from nox.lib import core
from nox.lib.core import Component
from nox.lib import openflow
import nox.lib.pyopenflow as pyopenflow
from nox.lib.netinet import netinet
from nox.lib.packet.ethernet import ethernet
from nox.coreapps.pyrt.pycomponent import CONTINUE
from nox.netapps.authenticator.pyflowutil import Flow_in_event

from nox.netapps.routing import pyrouting

from socket import ntohs, htons
import logging

import simplejson as json

from nox.coreapps.messenger.pyjsonmsgevent import JSONMsg_event

from nox.lib.netinet.netinet import c_ntohl

from time import sleep

U32_MAX = 0xffffffff
DP_MASK = 0xffffffffffff
PORT_MASK = 0xffff

BROADCAST_TIMEOUT   = 2 # was 60
FLOW_TIMEOUT        = 5

log = logging.getLogger('samplerouting')

# DOESN'T YET NAT UNKNOWN DESTINATION PACKETS THAT ARE FLOODED

class SampleRouting(Component):
    def __init__(self, ctxt):
        Component.__init__(self, ctxt)
        self.routing = None
        
        # Subscribers for json messages
        #(eg. self.subscribers["highlight"] = [guistream]
        self.subscribers = {}
        
        # list of routes installations that are waiting for barrier_replies
        # (holds barrier xids and packet out info)
        self.pending_routes = []

    def install(self):
        self.routing = self.resolve(pyrouting.PyRouting)
        
        self.register_handler(Flow_in_event.static_get_name(),
                              self.handle_flow_in)
                              
        self.register_for_barrier_reply(self.handle_barrier_reply)       
        
        # Register for json messages from the gui
        self.register_handler( JSONMsg_event.static_get_name(), \
                         lambda event: self.handle_jsonmsg_event(event))
                         
                              

    def handle_flow_in(self, event):
    
    
        if not event.active:
            return CONTINUE
        indatapath = netinet.create_datapathid_from_host(event.datapath_id)
        route = pyrouting.Route()
        
        sloc = event.route_source
        if sloc == None:
            sloc = event.src_location['sw']['dp']
            route.id.src = netinet.create_datapathid_from_host(sloc)
            inport = event.src_location['port']
            sloc = sloc | (inport << 48)
        else:
            route.id.src = netinet.create_datapathid_from_host(sloc & DP_MASK)
            inport = (sloc >> 48) & PORT_MASK
        if len(event.route_destinations) > 0:
            dstlist = event.route_destinations
        else:
            dstlist = event.dst_locations
        
        checked = False
        for dst in dstlist:
            if isinstance(dst, dict):
                if not dst['allowed']:
                    continue
                dloc = dst['authed_location']['sw']['dp']
                route.id.dst = netinet.create_datapathid_from_host(dloc & DP_MASK)
                outport = dst['authed_location']['port']
                dloc = dloc | (outport << 48)
            else:
                dloc = dst
                route.id.dst = netinet.create_datapathid_from_host(dloc & DP_MASK)
                outport = (dloc >> 48) & PORT_MASK
            if dloc == 0:
                continue
            if self.routing.get_route(route):
                checked = True
                if self.routing.check_route(route, inport, outport):
                    log.debug('Found route %s.' % hex(route.id.src.as_host())+\
                            ':'+str(inport)+' to '+hex(route.id.dst.as_host())+\
                            ':'+str(outport))
                    if route.id.src == route.id.dst:
                        firstoutport = outport
                    else:
                        firstoutport = route.path[0].outport
                    
                    p = []
                    if route.id.src == route.id.dst:
                        p.append(str(inport))
                        p.append(str(indatapath))
                        p.append(str(firstoutport))
                    else:
                        s2s_links = len(route.path)
                        p.append(str(inport))
                        p.append(str(indatapath))
                        for i in range(0,s2s_links):
                            p.append(str(route.path[i].dst))
                        p.append(str(outport))
                            
                    self.routing.setup_route(event.flow, route, inport, \
                                    outport, FLOW_TIMEOUT, [], True)
                                    
                    # Send Barriers                
                    pending_route = []
                    #log.debug("Sending BARRIER to switches:")
                    # Add barrier xids
                    for dpid in p[1:len(p)-1]:
                        log.debug("Sending barrier to %s", dpid)
                        pending_route.append(self.send_barrier(int(dpid,16)))
                    # Add packetout info
                    pending_route.append([indatapath, inport, event])
                    # Store new pending_route (waiting for barrier replies)
                    self.pending_routes.append(pending_route)
                           
                    # send path to be highlighted to GUI
                    self.send_to_gui("highlight",p)
                    
                    # Send packet out (do it after receiving barrier(s))
                    if indatapath == route.id.src or \
                        pyrouting.dp_on_route(indatapath, route):
                        pass
                        #self.routing.send_packet(indatapath, inport, \
                        #    openflow.OFPP_TABLE,event.buffer_id,event.buf,"", \
                        #    False, event.flow)
                    else:
                        log.debug("Packet not on route - dropping.")
                    return CONTINUE
                else:
                    log.debug("Invalid route between %s." \
                        % hex(route.id.src.as_host())+':'+str(inport)+' to '+\
                        hex(route.id.dst.as_host())+':'+str(outport))
            else:
                log.debug("No route between %s and %s." % \
                    (hex(route.id.src.as_host()), hex(route.id.dst.as_host())))
        if not checked:
            if event.flow.dl_dst.is_broadcast():
                log.debug("Setting up FLOOD flow on %s", str(indatapath))
                self.routing.setup_flow(event.flow, indatapath, \
                    openflow.OFPP_FLOOD, event.buffer_id, event.buf, \
                        BROADCAST_TIMEOUT, "", \
                        event.flow.dl_type == htons(ethernet.IP_TYPE))
            else:
                inport = ntohs(event.flow.in_port)
                log.debug("Flooding")
                self.routing.send_packet(indatapath, inport, \
                    openflow.OFPP_FLOOD, \
                    event.buffer_id, event.buf, "", \
                    event.flow.dl_type == htons(ethernet.IP_TYPE),\
                    event.flow)
        else:
            log.debug("Dropping packet")

        return CONTINUE

    def getInterface(self):
        return str(SampleRouting)
    
    def handle_barrier_reply(self, dpid, xid):
        # find the pending route this xid belongs to
        intxid = c_ntohl(xid)
        for pending_route in self.pending_routes[:]:
            if intxid in pending_route:
                pending_route.remove(intxid)
                # If this was the last pending barrier_reply_xid in this route
                if len(pending_route) == 1:
                    log.debug("All Barriers back, sending packetout")
                    indatapath, inport, event = pending_route[0]
                    self.routing.send_packet(indatapath, inport, \
                        openflow.OFPP_TABLE,event.buffer_id,event.buf,"", \
                        False, event.flow)
                    
                    self.pending_routes.remove(pending_route)
                    
        return CONTINUE
             
    """Communication with the GUI"""    
        
    def handle_jsonmsg_event(self, e):
        ''' Handle incoming json messenges '''
        msg = json.loads(e.jsonstring)
        
        if msg["type"] != "sample_routing" :
            return CONTINUE
            
        if not "command" in msg:
            lg.debug( "Received message with no command field" )
            return CONTINUE
        
        if msg["command"] == "subscribe":
            # Add stream to interested entities for this msg_type
            if not msg["msg_type"] in self.subscribers:
                self.subscribers[msg["msg_type"]] = []     
            self.subscribers[msg["msg_type"]].append(e)
            
            return CONTINUE
        
    def send_to_gui(self, msg_type, data):
        # Construct message header
        msg = {}
        msg["type"] = "sample_routing"
        
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
            return SampleRouting(ctxt)

    return Factory()
