# Copyright 2008 (C) Nicira, Inc.
# 
# This file is part of NOX.
# 
# NOX is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# NOX is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with NOX.  If not, see <http://www.gnu.org/licenses/>.

import logging
import array
import struct
import types
from socket import htons, htonl
import nox.lib.openflow as openflow
import nox.lib.pyopenflow as pyopenflow

from nox.coreapps.pyrt.pycomponent import * 
from util import *
from nox.lib.netinet.netinet import Packet_expr 
from nox.lib.netinet.netinet import create_eaddr 
from nox.lib.packet import *

lg = logging.getLogger('core')

IN_PORT    = "in_port"
AP_SRC     = "ap_src"
AP_DST     = "ap_dst"
DL_SRC     = "dl_src"
DL_DST     = "dl_dst"
DL_VLAN    = "dl_vlan"
DL_VLAN_PCP = "dl_vlan_pcp"
DL_TYPE    = "dl_type"
NW_SRC     = "nw_src"
NW_SRC_N_WILD = "nw_src_n_wild"
NW_DST     = "nw_dst"
NW_DST_N_WILD = "nw_dst_n_wild"
NW_PROTO   = "nw_proto"
NW_TOS     = "nw_tos"
TP_SRC     = "tp_src"
TP_DST     = "tp_dst"
GROUP_SRC  = "group_src"
GROUP_DST  = "group_dst"

N_TABLES    = 'n_tables'
N_BUFFERS   = 'n_bufs'
CAPABILITES = 'caps'
ACTIONS     = 'actions'
PORTS       = 'ports'

TABLE_ID    = 'table_id'
NAME        = 'name'
MAX_ENTRIES = 'max_entries'
ACTIVE_COUNT = 'active_count'
LOOKUP_COUNT = 'lookup_count'
MATCHED_COUNT = 'matched_count'

PORT_NO     = 'port_no'
SPEED       = 'speed'
CONFIG      = 'config'
STATE       = 'state'
CURR        = 'curr'
ADVERTISED  = 'advertised'
SUPPORTED   = 'supported'
PEER        = 'peer'
HW_ADDR     = 'hw_addr'

RX_PACKETS = 'rx_packets'
TX_PACKETS = 'tx_packets'
RX_BYTES   = 'rx_bytes'
TX_BYTES   = 'tx_bytes'
RX_DROPPED = 'rx_dropped'
TX_DROPPED = 'tx_dropped'
RX_ERRORS  = 'rx_errors'
TX_ERRORS  = 'tx_errors'
RX_FRAME_ERROR = 'rx_frame_error'
RX_OVER_ERROR = 'rx_over_error'
RX_CRC_ERROR = 'rx_crc_error'
COLLISIONS = 'collisions'

PACKET_COUNT = 'packet_count'
BYTE_COUNT = 'byte_count'
FLOW_COUNT = 'flow_count'

MATCH = 'match'
COOKIE = 'cookie'
DUR_SEC = 'duration_sec'
DUR_NSEC = 'duration_nsec'
PRIORITY = 'priority'
IDLE_TO = 'idle_timeout'
HARD_TO = 'hard_timeout'

MFR_DESC = 'mfr_desc'
HW_DESC = 'hw_desc'
SW_DESC = 'sf_desc'
DP_DESC = 'dp_desc'
SERIAL_NUM = 'serial_num'

################################################################################
# API NOTES:
#
# Automatically returns CONTINUE for handlers that do not 
# return a value (handlers are supposed to return a Disposition)
#
# All values should be passed in host byte order.  The API changes
# values to network byte order based on knowledge of field.  (NW_SRC
# --> 32 bit val, TP_SRC --> 16 bit value, etc.).  Other than
# DL_SRC/DST and NW_SRC/DST fields, packet header fields should be
# passed as integers.  DL_SRC, DL_DST fields should be passed in as
# either vigil.netinet.ethernetaddr objects.  They can however also be
# passed in any other type that an ethernetaddr constructor has be
# defined for.  NW_SRC/NW_DST fields meanwhile can be passed either
# ints, ip strings, or vigil.netinet.ipaddr objects.
###########################################################################

class Component: 
    """\brief Abstract class to inherited by all Python components.
    \ingroup noxapi
    """
    def __init__(self, ctxt):
        self.ctxt = ctxt
        self.component_names = None 

    def configure(self, config):
        """\brief Configure the component.
        Once configured, the component has parsed its configuration and
        resolved any references with other components it may have.

        @param config configuration dictionary
        """
        pass

    def install(self):
        """\brief Install the component.
        Once installed, the component runs and is usable by other
        components.
        """
        pass

    def getInterface(self):
        """\brief Return the interface (class) component provides.
        The default implementation returns the class itself.
        """
        return self.__class__

    def resolve(self, interface):
        return self.ctxt.resolve(str(interface))    

    def is_component_loaded(self, name):
        """\brief Check if a component is loaded.
        Allow components to check at runtime whether or not others
        are loaded without having to import them (which causes
        linking errors).

        @param name name of the component
        """
        if not self.component_names:
            self.component_names = []
            for component in self.ctxt.get_kernel().get_all():
                self.component_names.append(component.get_name())
        return name in self.component_names        
                
    def register_event(self, event_name):
        return self.ctxt.register_event(event_name)

    def register_python_event(self, event_name):
        return self.ctxt.register_python_event(event_name)

    def register_handler(self, event_name, handler):
        """\brief Register an event handler.

        The handler will be called with: handler(event).
        'event' is a dictionary containing data for the
         specific event.

        @param event_name name of the event
        @param handler handler function
        """
        return self.ctxt.register_handler(event_name, handler)

    def post_timer(self, event):
        return self.ctxt.post_timer(event)

    def post(self, event):
        # if event is a swigobject, make sure that it doesn't try
        # to handle memory deletion
        if hasattr(event, 'thisown'):
            event.thisown = 0 # just in case
        return self.ctxt.post(event)

    def make_action_array(self, actions):
        action_str = ""

        for action in actions:
            args_expected = 2
            if action[0] == openflow.OFPAT_OUTPUT:
                if type(action[1]) == int or type(action[1]) == long:
                    a = struct.pack("!HHHH", action[0], 8,
                                    action[1], 0)
                else:
                    a = struct.pack("!HHHH", action[0], 8,
                                    action[1][1], action[1][0])
            elif action[0] == openflow.OFPAT_SET_VLAN_VID:
                a = struct.pack("!HHHH", action[0], 8, action[1], 0)
            elif action[0] == openflow.OFPAT_SET_VLAN_PCP:
                a = struct.pack("!HHBBH", action[0], 8, action[1], 0, 0)
            elif action[0] == openflow.OFPAT_STRIP_VLAN:
                args_expected = 1
                a = struct.pack("!HHI", action[0], 8, 0)
            elif action[0] == openflow.OFPAT_SET_DL_SRC \
                    or action[0] == openflow.OFPAT_SET_DL_DST:
                eaddr = convert_to_eaddr(action[1])
                if eaddr == None:
                    raise RuntimeError('invalid ethernet addr')
                a = struct.pack("!HH6sHI", action[0], 16,
                                eaddr.binary_str(), 0, 0)
            elif action[0] == openflow.OFPAT_SET_NW_SRC \
                    or action[0] == openflow.OFPAT_SET_NW_DST:
                iaddr = convert_to_ipaddr(action[1])
                if iaddr == None:
                    raise RuntimeError('invalid ip addr')
                a = struct.pack("!HHI", action[0], 8, ipaddr(iaddr).addr)
            elif action[0] == openflow.OFPAT_SET_TP_SRC \
                    or action[0] == openflow.OFPAT_SET_TP_DST:
                a = struct.pack("!HHHH", action[0], 8, action[1], 0)
            elif action[0] == openflow.OFPAT_SET_NW_TOS:
                a = struct.pack("!HHBBBB", action[0], 8, action[1], 0, 0, 0)
            elif action[0] == openflow.OFPAT_ENQUEUE:
                a = struct.pack("!HHHHHHI", action[0], 16, action[1][0],
                                0,0,0, action[1][1])
            else:
                raise RuntimeError('invalid action type: ' + str(action[0]))

            if len(action) != args_expected:
                raise RuntimeError('action %s expected %s arguments',
                                    action[0], args_expected)

            action_str = action_str + a

        return action_str

    def send_port_mod(self, dpid, portno, hwaddr, mask, config):    
        try:
            addr = create_eaddr(str(hwaddr)) 
            return self.ctxt.send_port_mod(dpid, portno, addr, mask, config)
        except Exception, e:    
            raise RuntimeError("unable to send port mod:" + str(e))

    def send_switch_command(self, dpid, command, arg_list):
        return self.ctxt.send_switch_command(dpid, command, ",".join(arg_list))

    def switch_reset(self, dpid):
        return self.ctxt.switch_reset(dpid)

    def switch_update(self, dpid):
        return self.ctxt.switch_update(dpid)
            

    def send_openflow_command(self, dp_id, packet):
        """\brief Send an openflow command packet to a datapath.

        @param dp_id datapath to send packet to
        @param packet data to put in openflow packet
        """
        if type(packet) == type(array.array('B')):
            packet = packet.tostring()

        self.ctxt.send_openflow_command(dp_id, packet)

    def send_openflow_packet(self, dp_id, packet, actions, 
                             inport=openflow.OFPP_CONTROLLER):
        """\brief Send an openflow packet to a datapath.

        @param dp_id datapath to send packet to
        @param packet data to put in openflow packet
        @param actions list of actions or dp port to send out of
        @param inport dp port to mark as source (defaults to Controller port)
        """
        if type(packet) == type(array.array('B')):
            packet = packet.tostring()

        if type(actions) == types.IntType:
            self.ctxt.send_openflow_packet_port(dp_id, packet, actions, inport)
        elif type(actions) == types.ListType:
            oactions = self.make_action_array(actions)
            if oactions == None:
                raise Exception('Bad action')
            self.ctxt.send_openflow_packet_acts(dp_id, packet, oactions, inport)
        else:
            raise Exception('Bad argument')

    def send_openflow_buffer(self, dp_id, buffer_id, actions, 
                             inport=openflow.OFPP_CONTROLLER):
        """\brief Tell a datapath to send out a buffer.
        
        @param dp_id datapath to send packet to
        @param buffer_id id of buffer to send out
        @param actions list of actions or dp port to send out of
        @param inport dp port to mark as source (defaults to Controller port)
        """
        if type(actions) == types.IntType:
            self.ctxt.send_openflow_buffer_port(dp_id, buffer_id, actions,
                                                inport)
        elif type(actions) == types.ListType:
            oactions = self.make_action_array(actions)
            if oactions == None:
                raise Exception('Bad action')
            self.ctxt.send_openflow_buffer_acts(dp_id, buffer_id, oactions,
                                                inport)
        else:
            raise Exception('Bad argument')

    def post_callback(self, t, function):
        from twisted.internet import reactor
        reactor.callLater(t, function)

    def send_flow_command(self, dp_id, command, attrs, 
                          priority=openflow.OFP_DEFAULT_PRIORITY,
                          add_args=None,
                          hard_timeout=openflow.OFP_FLOW_PERMANENT):
        m = set_match(attrs)
        if m == None:
            return False

        if command == openflow.OFPFC_ADD:
            (idle_timeout, actions, buffer_id) = add_args
            oactions = self.make_action_array(actions)
            if oactions == None:
                return False
        else:
            idle_timeout = 0
            oactions = ""
            buffer_id = UINT32_MAX
        
        self.ctxt.send_flow_command(dp_id, command, m, idle_timeout,
                                    hard_timeout, oactions, buffer_id, priority)

        return True

    # Former PyAPI methods

    def send_openflow(self, dp_id, buffer_id, packet, actions,
                      inport=openflow.OFPP_CONTROLLER):
        """\brief Send an openflow packet to a datapath.

        This function is a convenient wrapper for send_openflow_packet
        and send_openflow_buffer for situations where it is unknown in
        advance whether the packet to be sent is buffered.  If
        'buffer_id' is -1, it sends 'packet'; otherwise, it sends the
        buffer represented by 'buffer_id'.

        @param dp_id datapath to send packet to
        @param buffer_id id of buffer to send out
        @param packet data to put in openflow packet
        @param actions list of actions or dp port to send out of
        @param inport dp port to mark as source (defaults to Controller port)
        """
        if buffer_id != None:
            self.send_openflow_buffer(dp_id, buffer_id, actions, inport)
        else:
            self.send_openflow_packet(dp_id, packet, actions, inport)

    ###########################################################################
    # The following methods manipulate a flow entry in a datapath.
    # A flow is defined by a dictionary containing 0 or more of the
    # following keys (commented keys have already been defined above):
    # 
    # DL_SRC     = "dl_src"
    # DL_DST     = "dl_dst"
    # DL_VLAN    = "dl_vlan"
    # DL_VLAN_PCP = "dl_vlan_pcp"
    # DL_TYPE    = "dl_type"
    # NW_SRC     = "nw_src"
    # NW_DST     = "nw_dst"
    # NW_PROTO   = "nw_proto"
    # TP_SRC     = "tp_src"
    # TP_DST     = "tp_dst"
    #
    # Absent keys are interpretted as wildcards.
    ###########################################################################

    def delete_datapath_flow(self, dp_id, attrs):
        """\brief Delete all flow entries matching the passed in (potentially
        wildcarded) flow.

        @param dp_id datapath to delete the entries from
        @param attrs the flow as a dictionary (described above)
        """
        return self.send_flow_command(dp_id, openflow.OFPFC_DELETE, attrs)

    def delete_strict_datapath_flow(self, dp_id, attrs,
                        priority=openflow.OFP_DEFAULT_PRIORITY):
        """\brief Strictly delete the flow entry matching the passed in
        (potentially wildcarded) flow.

        Strict matching means that they have they also have the
        same wildcarded fields.

        @param dp_id datapath to delete the entries from
        @param attrs the flow as a dictionary (described above)
        @param priority the priority of the entry to be deleted
          (only meaningful for entries with wildcards)
        """
        return self.send_flow_command(dp_id, openflow.OFPFC_DELETE_STRICT,
                                      attrs, priority)

    def install_datapath_flow(self, dp_id, attrs, idle_timeout, hard_timeout,
                              actions, buffer_id=None, 
                              priority=openflow.OFP_DEFAULT_PRIORITY,
                              inport=None, packet=None):
        """\brief Add a flow entry to datapath.

        @param dp_id datapath to add the entry to

        @param attrs the flow as a dictionary (described above)

        @param idle_timeout # idle seconds before flow is removed from dp

        @param hard_timeout # of seconds before flow is removed from dp

        @param actions a list where each entry is a two-element list representing
        an action.  Elem 0 of an action list should be an ofp_action_type
        and elem 1 should be the action argument (if needed). For
        OFPAT_OUTPUT, this should be another two-element list with max_len
        as the first elem, and port_no as the second

        @param buffer_id the ID of the buffer to apply the action(s) to as well.
        Defaults to None if the actions should not be applied to a buffer

        @param priority when wildcards are present, this value determines the
        order in which rules are matched in the switch (higher values
        take precedence over lower ones)

        @param packet If buffer_id is None, then a data packet to which the
        actions should be applied, or None if none.

        @param inport When packet is sent, the port on which packet came in as input,
        so that it can be omitted from any OFPP_FLOOD outputs.
        """
        if buffer_id == None:
            buffer_id = UINT32_MAX

        self.send_flow_command(dp_id, openflow.OFPFC_ADD, attrs, priority,
                          (idle_timeout, actions, buffer_id), hard_timeout)
        
        if buffer_id == UINT32_MAX and packet != None:
            for action in actions:
                if action[0] == openflow.OFPAT_OUTPUT:
                    if type(action[1]) == int or type(action[1]) == long:
                        self.send_openflow_packet(dp_id, packet, action[1], inport)
                    else:
                        self.send_openflow_packet(dp_id, packet, action[1][1], inport)
                else:
                    raise NotImplementedError
                    
    def send_barrier(self, dpid, xid=None):
        #TODO: replace with real XID code
        if xid == None:
            if not hasattr(self, 'xid'):
                xid = 8238
            else:
                xid = getattr(self, 'xid')
            if xid >= 0xFFffFFfe:
                xid = 8238
            setattr(self, 'xid', xid + 1)
            data = struct.pack("!BBHL", openflow.OFP_VERSION,
            openflow.OFPT_BARRIER_REQUEST, 8, xid)
            self.send_openflow_command(dpid, data)
        return xid

    def register_for_packet_in(self, handler):
        """\brief Register a handler for a packet in event.

        The handler will be called with:
        handler(dpid, in_port, reason, total_frame_len, buffer_id, captured_data)

        \note 'dpid' is the datapath id of the switch.
        \note 'in_port' is the port on which the packet arrived.
        \note 'reason' is the reason for the packet in (see ofp_reason).
        \note 'total_frame_len' is the packet length.
        \note 'buffer_id' is the buffer id assigned by the switch,
        \note  or -1 if the entire packet was sent.
        \note 'captured_data' is the packet data.

        @param handler the handler function
        """
        self.register_handler(Packet_in_event.static_get_name(),
                              gen_packet_in_callback(handler))

    def register_for_flow_removed(self, handler):
        """\bref Register a handler for flow removed events.

        The handler will be called with:
         handler(dpid, attrs, priority, reason, cookie, dur_sec,
                dur_nsec, byte_count, packet_count)

        \note 'dpid' is the datapath id of the switch.
        \note 'attrs' is a flow dictionary (see comment above)
        \note 'priority' is the flow's priority
        \note 'reason' why the flow was removed (see ofp_flow_removed_reason)
        \note 'cookie' is the flow's cookie
        \note 'dur_sec' is how long the flow was alive in (s).
        \note 'dur_nsec' is how long the flow was alive beyond dur_sec in (ns).
        \note 'byte_count' is the number of bytes passed through this flow.
        \note 'packet_count' is the number of packets passed through this flow.
        @param handler the hander function
        """
        self.register_handler(Flow_removed_event.static_get_name(),
                              gen_flow_removed_callback(handler))

    def register_for_flow_mod(self, handler):
        """\bref Register a handler for flow mod events.

        The handler will be called with:
         handler(dpid, attrs, command, idle_to, hard_to, buffer_id,
                 priority, cookie)

        \note 'dpid' is the datapath id of the switch.
        \note 'attrs' is a flow dictionary (see comment above)
        \note 'command' is the type of flow mod (see ofp_flow_mod_command)
        \note 'idle_to' is the idle timeout of the flow
        \note 'hard_to' is the hard timeout of the flow
        \note 'buffer_id' is a buffer id assigned by the switch, or -1 if
        \note  there is no buffer. (This is not meaningful for OFPFC_DELETE command).
        \note 'priority' is the flow's priority
        \note 'cookie' is the flow's cookie

        @param handler the hander function
        """
        self.register_handler(Flow_mod_event.static_get_name(),
                              gen_flow_mod_callback(handler))

    def register_for_bootstrap_complete(self, handler):
        """\brief Register a handler for bootstrap complete events.

        The handler will be called with: handler(event).

        \note 'event' is a dictionary for a bootstrap complete event.

        @param handler the handler function
        """

        self.register_handler(Bootstrap_complete_event.static_get_name(),
                              handler)

    def register_for_datapath_join(self, handler):
        """\brief Register a handler for a datapath join event.

        The handler will be called with: handler(dpid, attrs).

        \note 'dpid' is the datapath id of the switch
        \note 'attrs' is a dictionary with the following keys:
        \note \n
        \note   N_BUFFERS, N_TABLES, CAPABILITIES, ACTIONS, PORTS

        \note The PORTS value is a list of port dictionaries where each
        \note dictionary has the keys listed in the register_for_port_status
        \note documentation.

        @param handler the handler function
        """
        self.register_handler(Datapath_join_event.static_get_name(),
                              gen_datapath_join_callback(handler))

    def register_for_table_stats_in(self, handler):
        """\brief Register a handler for flow stats in events.

        The handler will be called with: handler(dpid, stats).

        \note 'dpid' is the datapath id of the switch
        \note 'stats' is a list of dictionaries (one for each table)
        \note with the keys:
        \note \n
        \note   TABLE_ID, NAME, MAX_ENTRIES, ACTIVE_COUNT,
        \note   LOOKUP_COUNT, MAX_COUNT

        @param handler the handler function
        """
        self.register_handler(Table_stats_in_event.static_get_name(),
                              gen_table_stats_in_callback(handler))

    def register_for_port_stats_in(self, handler):
        """\brief Register a handler for port stats in events.

        The handler will be called with: handler(dpid, stats).

        \note 'dpid' is the datapath id of the switch
        \note 'stats' is a list of dictionaries (one for each port)
        \note   with the keys:
        \note \n
        \note   PORT_NO, RX_PACKETS, TX_PACKETS, RX_BYTES, TX_BYTES
        \note   RX_DROPPED, TX_DROPPED, RX_ERRORS, TX_ERRORS,
        \note   RX_FRAME_ERR, RX_OVER_ERROR, RX_CRC_ERROR, COLLISIONS

        @param handler the handler function
        """
        self.register_handler(Port_stats_in_event.static_get_name(),
                              gen_port_stats_in_callback(handler))

    def register_for_aggregate_stats_in(self, handler):
        """\brief Register a handler for aggregate stats in events.

        The handler will be called with: handler(dpid, stats).

        \note 'dpid' is the datapath id of the switch
        \note 'stats' is a dictionary of aggregate stats with the keys:
        \note \n
        \note    PACKET_COUNT, BYTE_COUNT, FLOW_COUNT

        @param handler the handler function
        """
        self.register_handler(Aggregate_stats_in_event.static_get_name(),
                              gen_aggr_stats_in_callback(handler))

    def register_for_flow_stats_in(self, handler):
        """\brief Register a handler for flow stats in events.

        The handler will be called with: handler(dpid, flows, more, xid).

        \note 'dpid' is the datapath id of the switch
        \note 'flows' is a list of dictionaries (one for each flow) with keys:
        \note \n
        \note   TABLE_ID, MATCH, COOKIE, DUR_SEC, DUR_NSEC, PRIORITY,
        \note   IDLE_TO, HARD_TO, PACKET_COUNT, BYTE_COUNT
        \note \n
        \note 'more' is a bool indicating whether or not the switch still has more
        \note  flow stats to send.

        'xid' is the request id in the packet header.\n

        @param handler the handler function
        """
        self.register_handler(Flow_stats_in_event.static_get_name(),
                              gen_flow_stats_in_callback(handler))

    def register_for_desc_stats_in(self, handler):
        """\brief Register a handler for description stats in events.

        The handler will be called with: handler(dpid, stats).

         \note 'dpid' is the datapath id of the switch
         \note 'stats' is a dictionary with keys:
         \note \n
         \note  MFR_DESC, HW_DESC, SW_DESC, DP_DESC, SERIAL_NUM

        @param handler the handler function
        """
        self.register_handler(Desc_stats_in_event.static_get_name(),
                              gen_desc_stats_in_callback(handler))

    def register_for_datapath_leave(self, handler):
        """\brief Register a handler for datapath leave events.

        The handler will be called with: handler(dpid).

        \note 'dpid' is the datapath id of the switch
        
        @param handler the handler function
        """
        self.register_handler(Datapath_leave_event.static_get_name(),
                              gen_datapath_leave_callback(handler))

    def register_for_port_status(self, handler):
        """\brief Register a handler for port status events.

        The handler will be called with: handler(dpid, reason, port).

        \note 'dpid' is the datapath id of the switch
        \note 'reason' is the reason for the event (see ofp_port_reason).
        \note 'port' is a dictionary for the port with some convenience
        \note   bool fields added ('link', 'enabled', 'flood')

        @param handler the handler function
        """
        self.register_handler(Port_status_event.static_get_name(),
                              gen_port_status_callback(handler))

    def register_for_packet_match(self, handler, priority, expr):
        """\brief Register a handler for every packet in event matching
        the passed in expression.

        The handler will be called with:
         handler(dpid, in_port, reason, total_frame_len, buffer_id, captured_data)

       \note For an explanation of these arguments, see the documentation for
       \note register_for_packet_in. In this case, 'buffer_id' == None if the
       \note datapath does not have a buffer for the frame.

        @param handler the handler function
        @param priority the priority the installed classifier rule should have
        @param expr the flow match as a dictionary (see comment above).
        """
        e = Packet_expr()
        for key, val in expr.items():
            if key == AP_SRC:
                field = Packet_expr.AP_SRC
                val = htons(val)
            elif key == AP_DST:
                field = Packet_expr.AP_DST
                val = htons(val)
            elif key == DL_VLAN:
                field = Packet_expr.DL_VLAN
                val = htons(val)
            elif key == DL_VLAN_PCP:
                field = Packet_expr.DL_VLAN_PCP
                val = val
            elif key == DL_TYPE:
                field = Packet_expr.DL_TYPE
                val = htons(val)
            elif key == DL_SRC:
                field = Packet_expr.DL_SRC
                val = convert_to_eaddr(val)
                if val == None:
                    raise RuntimeError('invalid ethernet addr')
            elif key == DL_DST:
                field = Packet_expr.DL_DST
                val = convert_to_eaddr(val)
                if val == None:
                    raise RuntimeError('invalid ethernet addr')
            elif key == NW_SRC:
                field = Packet_expr.NW_SRC
                val = convert_to_ipaddr(val)
                if val == None:
                    raise RuntimeError('invalid ip addr')
            elif key == NW_DST:
                field = Packet_expr.NW_DST
                val = convert_to_ipaddr(val)
                if val == None:
                    raise RuntimeError('invalid ip addr')
            elif key == NW_PROTO:
                field = Packet_expr.NW_PROTO
            elif key == TP_SRC:
                field = Packet_expr.TP_SRC
                val = htons(val)
            elif key == TP_DST:
                field = Packet_expr.TP_DST
                val = htons(val)
            elif key == GROUP_SRC:
                field = Packet_expr.GROUP_SRC
                val = htonl(val)
            elif key == GROUP_DST:
                field = Packet_expr.GROUP_DST
                val = htonl(val)
            else:
                raise RuntimeError('invalid key: %s' % (key,))
        
            if isinstance(val, ethernetaddr):
                e.set_eth_field(field, val)
            else:
                # check for max?
                if val > UINT32_MAX:
                    raise RuntimeError('value %u exceeds accepted range:' % (val, ))
                e.set_uint32_field(field, val)

        return self.ctxt.register_handler_on_match(gen_packet_in_callback(handler), priority, e)

    def register_for_switch_mgr_join(self, handler):
        """\brief Register a handler for switch manager join events.

        The handler will be called with: handler(mgmt_id).

        @param handler the handler function
        """
        self.register_handler(Switch_mgr_join_event.static_get_name(),
                              gen_switch_mgr_join_callback(handler))

    def register_for_switch_mgr_leave(self, handler):
        """\brief Register a handler for switch manager leave events.

        The handler will be called with: handler(mgmt_id).

        @param handler the handler function
        """
        self.register_handler(Switch_mgr_leave_event.static_get_name(),
                              gen_switch_mgr_leave_callback(handler))

    def register_for_barrier_reply(self, handler):
        """\brief Register a handler for barrier reply events.

        The handler will be called with: handler(dpid, xid).

        \note 'dpid' is the datapath id of the switch.
        \note 'xid' is the xid of the barrier request and reply.

        @param handler the handler function
        """
        self.register_handler(Barrier_reply_event.static_get_name(),
                              gen_barrier_reply_callback(handler))

    def register_for_error(self, handler):
        """\brief Register a handler for error events.

        The handler will be called with: handler(dpid, type, code, data, xid).

        \note 'dpid' is the datapath id of the switch.
        \note 'type' is the error type.
        \note 'code' is more specific and depends on 'type'.
        \note 'data' is any data returned with the error message.
        \note 'xid' is the xid of the error message.

        @param handler the handler function
        """
        self.register_handler(Error_event.static_get_name(),
                              gen_error_callback(handler))

    def register_for_barrier_reply(self, handler):
        """
        register a handler to be called on every barrier_reply
        event handler will be called with the following args:
        
        handler(dp_id, xid)
        """
        self.register_handler(Barrier_reply_event.static_get_name(),
                              gen_barrier_cb(handler))

    def unregister_handler(self, rule_id):
        """
        Unregister a handler for match.
        """
        return self.ctxt.register_handler(event_type, event_name, handler)
