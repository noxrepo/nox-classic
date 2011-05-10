# ----------------------------------------------------------------------
# Spanning tree -- software based
# Authors: Glen Gibb <grg@stanford.edu>
# Date: 08/08/08
#
# Changes:
#
# Notes: This won't work correctly if there are more than 2 switches on
#        any one "link". ie. if we were on a broadcast network or there was an
#        extra switch in the middle
# ----------------------------------------------------------------------

import array
import struct
import time
from nox.coreapps.pyrt.pycomponent      import CONTINUE, STOP
from nox.netapps.bindings_storage.pybindings_storage import pybindings_storage
from nox.lib.core                   import *
from nox.lib.util                   import *
from nox.lib.packet.packet_utils    import longlong_to_octstr
from nox.lib.packet.ethernet        import ethernet, ETHER_ANY, ETHER_BROADCAST
from nox.lib.netinet                import *
import nox.lib.openflow as openflow

import logging

from nox.coreapps.messenger.pyjsonmsgevent import JSONMsg_event
import simplejson as json

# How often should we rebuild the flood ports?
FLOOD_PORT_UPDATE_INTERVAL = 5

# Hold time before allowing floods out a switch
FLOOD_WAIT_TIME = 10

# Minimum LLDP packet send period
MIN_LLDP_SEND_PERIOD = 0.05

log = logging.getLogger('spanning_tree')

class Spanning_Tree(Component):

    def __init__(self, ctxt):
        Component.__init__(self, ctxt)

        self.datapaths = {}
        self.debug = True
        self.ip_bypass = set()
        self.mac_bypass = set()
        self.roots = set()
        self.port_count = 0
        
        # dict {dp:[stp_ports]} holding the current ST state (ports, root)
        # check against this every time ST is update, to see if changed
        self.current_stp_ports = {}
        
    def getInterface(self):
        return str(Spanning_Tree)

    def debugPrint(self, text):
        if (self.debug):
            log.debug(text)

    def install(self):
        # Ensure LLDP queries occur more frequently by default.
        self.update_lldp_send_period()
        

        # Register to learn about datapath join and leave events
        self.register_for_datapath_join ( self.dp_join )
        self.register_for_datapath_leave( self.dp_leave )
        self.register_for_port_status( self.handle_port_status )
        self.register_for_packet_in( self.handle_packet_in)

        self.bindings = self.resolve(pybindings_storage)

        self.post_callback(1, self.update_spanning_tree)
        self.debugPrint("Spanning tree installed\n")
        
        # Register for json messages from the gui
        self.register_handler( JSONMsg_event.static_get_name(), \
                         lambda event: self.handle_jsonmsg_event(event))
        
        # Subscribers for json messages
        #(eg. self.subscribers["stp_ports"] = [guistream]
        self.subscribers = {}

    def dp_join(self, dp, stats):
        self.debugPrint("Datapath join: "+longlong_to_octstr(dp)[6:])
        if (not self.datapaths.has_key(dp)):
            # Process the port information returned by the switch

            # Build a list of ports
            now = time.time()
            ports = {}
            for port in stats['ports']:
                ports[port[core.PORT_NO]] = port
                if port[core.PORT_NO] <= openflow.OFPP_MAX:
                    port['enable_time'] = now + FLOOD_WAIT_TIME
                    port['flood'] = False
                    hw_addr = "\0\0" + port[core.HW_ADDR]
                    hw_addr = struct.unpack("!q", hw_addr)[0]
                    self.ctxt.send_port_mod(dp, port[core.PORT_NO], ethernetaddr(hw_addr),
                            openflow.OFPPC_NO_FLOOD, openflow.OFPPC_NO_FLOOD)

            # Record the datapath
            self.datapaths[dp] = ports
            self.port_count += len(ports)

            # Update the LLDP send period
            self.update_lldp_send_period()
        return CONTINUE

    def dp_leave(self, dp):

        self.debugPrint("Datapath leave, "+longlong_to_octstr(dp)[6:])
        if (self.datapaths.has_key(dp)):
            # Decrement port count by # of ports in datapath that is leaving
            self.port_count -= len(self.datapaths[dp])
            del self.datapaths[dp]
        return CONTINUE

    def update_spanning_tree(self):
        '''Get the links to update the spanning tree
        '''
        self.bindings.get_all_links(self.update_spanning_tree_callback)
        self.post_callback(FLOOD_PORT_UPDATE_INTERVAL, self.update_spanning_tree)

    def update_spanning_tree_callback(self, links):
        '''Callback called by get_all_links to process the set of links.

        Currently:
         - updates the flood ports to build a spanning tree

        Note: each link probably appears twice (once for each direction)

        As a temporary hack to deal with the fact that we don't have
        spanning tree support in NOX we build a set of "flood-ports". Each
        datapath id representing a switch has a set of ports associated
        which represent links that don't contain other OpenFlow
        switches. This set of paths can be used safely for flooding to
        ensure that we don't circulate broadcast packets.

        @param links list link tuples (src_dpid, src_port, dst_dpid, dst_port)
        '''
        # Walk through the datapaths and mark all ports 
        # that are potentially enableable
        now = time.time()
        for dp in self.datapaths.iterkeys():
            for port_no, port in self.datapaths[dp].iteritems():
                if port_no > openflow.OFPP_MAX or now > port['enable_time']:
                    port['enable'] = True
                else:
                    port['enable'] = False
                port['keep'] = False


        # Walk through the links and create a dict based on source port
        my_links = self.build_link_dict(links)
        self.verify_bidir_links(my_links)

        # Now try to build the spanning tree
        seen = set()
        roots = set()

        # Get all sources in reversed sorted order
        srcs = self.datapaths.keys()
        srcs.sort()
        srcs = srcs[::-1]

        #kyr
        if len(srcs):
            self.root = srcs[len(srcs)-1]

        # Process all sources
        while len(srcs) > 0:
            src_dpid = srcs.pop()

            # Add the dpid to the list of roots if we haven't yet seen it
            # (it must the be root of a tree)
            if src_dpid not in seen:
                roots.add(src_dpid)

            # Record that we've seen this node
            seen.add(src_dpid)

            # Make sure we know the src_dpid
            # This is necessary occasionally during start-up
            if not my_links.has_key(src_dpid):
                self.debugPrint("Warning: cannot find src_dpid %s in my_links"%longlong_to_octstr(src_dpid)[6:])
                continue

            # Walk through all dests
            dsts = my_links[src_dpid].keys()
            dsts.sort()
            next_dpids = []
            for dst_dpid in dsts:
                if dst_dpid not in seen:
                    # Attempt to find the fastest link to the other switch
                    best_speed = -1
                    best_pair = (-1, -1)
                    for (src_port, dst_port) in my_links[src_dpid][dst_dpid]:
                        try:
                            speed = self.datapaths[src_dpid][src_port]['speed']
                            if speed > best_speed:
                                best_speed = speed
                                best_pair = (src_port, dst_port)
                        except KeyError:
                            pass

                    # Disable all links but the fastest
                    for (src_port, dst_port) in my_links[src_dpid][dst_dpid]:
                        try:
                            if (src_port, dst_port) != best_pair:
                                self.datapaths[dst_dpid][dst_port]['enable'] = False
                            else:
                                self.datapaths[src_dpid][src_port]['keep'] = True
                                self.datapaths[dst_dpid][dst_port]['keep'] = True
                        except KeyError:
                            pass

                    # Record that we've seen the dpid
                    seen.add(dst_dpid)
                    next_dpids.append(dst_dpid)

                # Already-seen DPIDs
                else:
                    # Disable the link to the already-seen DPIDs
                    if src_dpid <= dst_dpid:
                        (local_src_dpid, local_dst_dpid) = (src_dpid, dst_dpid)
                    else:
                        (local_src_dpid, local_dst_dpid) = (dst_dpid, src_dpid)

                    for (src_port, dst_port) in my_links[local_src_dpid][local_dst_dpid]:
                        # If the src/dst dpids are the same, sort the ports
                        if local_src_dpid == local_dst_dpid:
                            if (src_port > dst_port):
                                (src_port, dst_port) = (dst_port, src_port)

                        # Disable the ports
                        try:
                            if not self.datapaths[local_dst_dpid][dst_port]['keep']:
                                self.datapaths[local_dst_dpid][dst_port]['enable'] = False
                            if not self.datapaths[local_src_dpid][src_port]['keep']:
                                self.datapaths[local_src_dpid][src_port]['enable'] = False
                        except KeyError:
                            pass

            # Once we've processed all links from this source, update the
            # list of sources so that the DPIDs we've just linked to will
            # be processed next. This is achieved by placing them at the
            # end of the list.
            next_dpids = next_dpids[::-1]
            for dpid in next_dpids:
                try:
                    srcs.remove(dpid)
                except ValueError:
                    pass
            srcs.extend(next_dpids)

        # Update the list of roots
        self.roots = roots
        
        # Build dictionary to send to gui
        # Format { dp: [stp_ports] }
        stp_ports = {} 
        
        # Walk through links and enable/disable as appropriate
        for dp in self.datapaths.iterkeys():
            floodports = []
            nonfloodports = []
            for port_no, port in self.datapaths[dp].iteritems():
                if port_no <= openflow.OFPP_MAX:
                    if port['enable'] != port['flood']:
                        if port['flood']:
                            port['flood'] = False
                            msg = 'Disabling'
                            config = openflow.OFPPC_NO_FLOOD
                        else:
                            port['flood'] = True
                            msg = 'Enabling'
                            config = 0

                        self.debugPrint("%s port: %s--%d"%(msg, longlong_to_octstr(dp)[6:], port_no))
                        hw_addr = "\0\0" + port[core.HW_ADDR]
                        hw_addr = struct.unpack("!q", hw_addr)[0]
                        self.ctxt.send_port_mod(dp, port[core.PORT_NO], ethernetaddr(hw_addr),
                                openflow.OFPPC_NO_FLOOD, config)

                    if port['flood']:
                        floodports.append(port_no)
                    else:
                        nonfloodports.append(port_no)

            self.debugPrint("Ports for %s: Flood: %s   Non-flood: %s"%(longlong_to_octstr(dp)[6:], floodports, nonfloodports))
            dp = str(hex(dp))
            dp = dp[2:len(dp)-1]
            while len(dp)<12:
                dp = "0"+dp
            stp_ports[dp] = floodports#, nonfloodports)
        
        # If ST has changed, update and send new enabled ports to GUI
        if cmp(self.current_stp_ports, stp_ports) != 0:
            self.current_stp_ports = stp_ports
            root = str(self.root)
            while len(root)<12:
                root = "0"+root
            stp_ports['root'] = root 
            self.send_to_gui("stp_ports", self.current_stp_ports)
        else:
            self.debugPrint("SP has not changed")

    def build_link_dict(self, links):
        '''Build a dictionary of links based on source dpid

        Dict is:
        {src_dpid: {dst_dpid: [(src_port, dst_port), ...]}}
        '''
        my_links = {}
        for (src_dpid, src_port, dst_dpid, dst_port) in links:
            # Track the link
            try:
                if self.datapaths[src_dpid][src_port]['enable'] and \
                        self.datapaths[dst_dpid][dst_port]['enable']:
                    if my_links.has_key(src_dpid):
                        if (my_links[src_dpid].has_key(dst_dpid)):
                            my_links[src_dpid][dst_dpid].add((src_port, dst_port))
                        else:
                            my_links[src_dpid][dst_dpid] = set()
                            my_links[src_dpid][dst_dpid].add((src_port, dst_port))
                    else:
                        my_links[src_dpid] = {dst_dpid:set()}
                        my_links[src_dpid][dst_dpid].add((src_port, dst_port))
            except KeyError:
                pass
        return my_links

    def verify_bidir_links(self, links):
        '''Verify that all links are bi-directional

        Delete unidirectional links and disable ports
        '''
        srcs_to_delete = []
        for src_dpid in links.keys():
            dsts_to_delete = []
            for dst_dpid in links[src_dpid].keys():
                # Work out which ports need deleting
                ports_to_delete = []
                for (src_port, dst_port) in links[src_dpid][dst_dpid]:
                    ok = True
                    try:
                        if (dst_port, src_port) not in links[dst_dpid][src_dpid]:
                            ok = False
                    except KeyError:
                        ok = False

                    if not ok:
                        self.debugPrint("WARNING: Unidirectional link detected between %s -- %d   <-->   %s -- %d"%
                                (longlong_to_octstr(src_dpid)[6:], src_port,
                                 longlong_to_octstr(dst_dpid)[6:], dst_port))
                        ports_to_delete.append((src_port, dst_port))
                        try:
                            if (src_dpid <= dst_dpid):
                                self.datapaths[dst_dpid][dst_port]['enable'] = False
                            else:
                                self.datapaths[src_dpid][src_port]['enable'] = False
                        except KeyError:
                            self.datapaths[src_dpid][src_port]['enable'] = False


                # Delete the ports and work out if we need to delete the dst_dpid
                for ports in ports_to_delete:
                    links[src_dpid][dst_dpid].discard(ports)
                    if len(links[src_dpid][dst_dpid]) == 0:
                        dsts_to_delete.append(dst_dpid)

            # Delete the dst_dpids and identify whether to delete the src_dpid
            for dst_dpid in dsts_to_delete:
                del links[src_dpid][dst_dpid]
                if len(links[src_dpid]) == 0:
                    srcs_to_delete.append(src_dpid)

        # Delete the src_dpids
        for src_dpid in srcs_to_delete:
            del links[src_dpid]

    def handle_port_status(self, dpid, reason, port):
        '''Port_status_event handler

        Handles port stats events, such as adding and deleting ports

        dpid - Datapath ID of port

        reason - what event occured

        port - port
        '''
        # Work out what sort of event we're processing
        if reason == openflow.OFPPR_ADD:
            if port['port_no'] <= openflow.OFPP_MAX:
                port['enable_time'] = time.time() + FLOOD_WAIT_TIME
                port['flood'] = False
                hw_addr = "\0\0" + port[core.HW_ADDR]
                hw_addr = struct.unpack("!q", hw_addr)[0]
                self.ctxt.send_port_mod(dp, port[core.PORT_NO], ethernetaddr(hw_addr),
                        openflow.OFPPC_NO_FLOOD, openflow.OFPPC_NO_FLOOD)
            self.datapaths[dpid][port['port_no']] = port
            self.port_count += 1
        elif reason == openflow.OFPPR_DELETE:
            if self.datapaths[dpid].has_key(port['port_no']):
                self.port_count += 1
                del self.datapaths[dpid][port['port_no']]

        return CONTINUE

    def handle_packet_in(self, dpid, inport, reason, len, bufid, packet):
        '''Packet in callback function

        Allow packets to be processed by other modules only if 
        the port is a flood port or it's an LLDP packet

        dpid - DPID of switch

        inport - inport port

        reason -

        len - length

        bufid - buffer ID of packet

        packet - received packet
        '''

        if not packet.parsed:
            log.msg('Ignoring incomplete packet',system='spanning_tree')
            
        # Allow LLDP messages to be processed
        if packet.type == ethernet.LLDP_TYPE:
            return CONTINUE

        # Check if it is a destination we know about
        try:
            # Check dest mac
            dst_mac = (struct.unpack('!I', packet.arr[0:4])[0] << 16) + struct.unpack('!H', packet.arr[4:6])[0]
            if dst_mac in self.mac_bypass:
                return CONTINUE

            # Check dest IP
            type = struct.unpack('!H', packet.arr[12:14])[0]
            ipver = struct.unpack('!b', packet.arr[14:15])[0]
            if type == 0x800 and ipver == 0x45:
                dst_ip = struct.unpack('!I', packet.arr[30:34])[0]
                if dst_ip in self.ip_bypass:
                    return CONTINUE
        except:
            pass

        # Check if the port is a flood port
        log.warn("%s : %s" %(dpid, packet))
        try:
            if self.datapaths[dpid][inport]['flood']:
                return CONTINUE
            else:
                log.warn("STOP")
                return STOP
        except KeyError:
            return STOP

    def update_lldp_send_period(self):
        '''Update the LLDP send period'''
        if self.port_count == 0:
            nox.netapps.discovery.discovery.LLDP_SEND_PERIOD = MIN_LLDP_SEND_PERIOD
        else:
            nox.netapps.discovery.discovery.LLDP_SEND_PERIOD = min(
                    MIN_LLDP_SEND_PERIOD,
                    (FLOOD_WAIT_TIME * 1.0) / 2 / self.port_count)

    def add_ip_bypass(self, ip):
        '''Add a bypass IP address

        Bypass IP addresses should be ignored when conisdering datapath'''
        self.ip_bypass.add(ip)

    def del_ip_bypass(self, ip):
        '''Delete a bypass IP address'''
        self.ip_bypass.discard(ip)

    def add_mac_bypass(self, mac):
        '''Add a bypass MAC address

        Bypass MAC addresses should be ignored when conisdering datapath'''
        self.mac_bypass.add(mac)

    def del_mac_bypass(self, mac):
        '''Delete a bypass MAC address'''
        self.mac_bypass.discard(mac)

    def reset_bypass(self):
        '''Reset all bypass IP addresses'''
        self.ip_bypass = set()
        self.mac_bypass = set()

    def get_roots(self):
        '''Get a list of all spanning tree roots'''
        return self.roots
        
    """Communication with the GUI"""    
        
    def handle_jsonmsg_event(self, e):
        ''' Handle incoming json messenges '''
        msg = json.loads(e.jsonstring)
        
        if msg["type"] != "spanning_tree" :
            return CONTINUE
            
        if not "command" in msg:
            lg.debug( "Received message with no command field" )
            return CONTINUE
        
        if msg["command"] == "subscribe":
            # Add stream to interested entities for this msg_type
            if not msg["msg_type"] in self.subscribers:
                self.subscribers[msg["msg_type"]] = []     
            self.subscribers[msg["msg_type"]].append(e)
            
            # Immediately send the current stp ports
            self.send_to_gui("stp_ports", self.current_stp_ports)
            
            return CONTINUE
            
    def send_to_gui(self, msg_type, data):
        # Construct message header
        msg = {}
        msg["type"] = "spanning_tree"
        
        # Add msg_type-speficic payload
        if msg_type=="stp_ports":
            msg["msg_type"] = "stp_ports"
            msg["ports"] = data
            
            if "stp_ports" in self.subscribers:
                for stream in self.subscribers["stp_ports"]:
                    stream.reply(json.dumps(msg))


def getFactory():
    class Factory:
        def instance(self, ctxt):
            return Spanning_Tree(ctxt)

    return Factory()
