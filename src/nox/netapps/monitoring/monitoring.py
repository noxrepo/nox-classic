'''monitoring core'''

# Written for Ripcord by
# Author: Rean Griffith (rean@eecs.berkeley.edu)
# Ported to NOX to use LAVI/messenger by
# Author: Kyriakos Zarifis (kyr.zarifis@gmail.com)

import time
import logging
from collections import defaultdict
from collections import deque
from twisted.python import log

from nox.coreapps.pyrt.pycomponent import Table_stats_in_event, \
Aggregate_stats_in_event
from nox.lib.core import Component, Flow_mod_event, Datapath_join_event, \
Datapath_leave_event, Port_stats_in_event, Table_stats_in_event, \
Aggregate_stats_in_event, CONTINUE, STOP, pyevent, Flow_stats_in_event, \
Queue_stats_in_event
import nox.lib.openflow as openflow
import nox.lib.pyopenflow as of

from nox.lib.packet.packet_utils  import mac_to_str
from nox.lib.netinet.netinet import datapathid, create_ipaddr, c_htonl, c_ntohl
from nox.lib.directory import Directory, LocationInfo
from nox.lib.packet.packet_utils import longlong_to_octstr


from switchqueryreplyevent import \
SwitchQueryReplyEvent, SwitchQuery as MonitorSwitchQuery
from linkutilreplyevent import LinkUtilizationReplyEvent

from nox.coreapps.messenger.pyjsonmsgevent import JSONMsg_event
import simplejson as json

# Default values for the periodicity of polling for each class of
# statistic

# Use a poll frequency of 20ms per switch (this frequency works)
#DEFAULT_POLL_TABLE_STATS_PERIOD     = 0.02
#DEFAULT_POLL_PORT_STATS_PERIOD      = 0.03
#DEFAULT_POLL_AGGREGATE_STATS_PERIOD = 0.04

# For testing, poll less aggressively
DEFAULT_POLL_TABLE_STATS_PERIOD     = 20 # seconds
DEFAULT_POLL_PORT_STATS_PERIOD      = 20 # seconds
DEFAULT_POLL_AGGREGATE_STATS_PERIOD = 20 # seconds


DEFAULT_POLL_UTIL_PERIOD = 1 # seconds

# Arbitrary limits on how much stats history we keep per switch
DEFAULT_COLLECTION_EPOCH_DURATION = 10 # seconds
DEFAULT_MAX_STATS_SNAPSHOTS_PER_SWITCH = 10

# Static log handle
lg = logging.getLogger('monitoring')

## \ingroup noxcomponents
# Collects and maintains switch and port stats for the network.  
#
# Monitors switch and port stats by sending out port_stats requests
# periodically to all connected switches.  
#
# The primary method of accessing the ports stats is through the
# webserver (see switchstatsws.py)  however, components can also
# register port listeners which are called each time stats are
# received for a particular port.
#

class Monitoring(Component):

    def __init__(self, ctxt):
        Component.__init__(self, ctxt)
        self.ctxt_ = ctxt
        lg.debug( 'Simple monitoring started!' )
        # We'll keep track of the logical time we've been 
        # collecting data so that we can group snapshots from different
        # switches in the network across time i.e. we want to look 
        # at changes in monitoring data within a single
        # collection epoch as well as across collection epochs
        self.collection_epoch = 0
        # Keep track of the latest collection epoch included in a 
        # stats reply so we know what
        self.max_stats_reply_epoch = -1
        # Keep track of the set of the switches we are monitoring. 
        # As switches join and leave the network we can enable or disable
        # the timers that poll them for their stats
        self.switches = set([])
        # Track the switches that we haven't heard from in a while
        self.silent_switches = set([])
        # Store the snapshots of the switch stats
        # [dpid][<snapshot1>,<snapshot2>,...,<snapshotN>]
        self.snapshots = {}
        # Store the capabilities of each port for each switch
        # [dpid][<port1>,<port2>,...,<portN>
        self.port_cap = {}
        # Pending queries - things we've been asked for but have not yet
        # satisfied
        self.pending_switch_queries = set([])
        # Mapping of gui query ID's to streams. This way Monitoring knows where
        # to send a specific reply from a switch stats query
        self.pending_gui_queries = {}
        # Subscribers for monitoring messages
        #(eg. self.subscribers["linkutils"] = [guistream]
        self.subscribers = {}
        """
        # Set defaults
        self.table_stats_poll_period = DEFAULT_POLL_TABLE_STATS_PERIOD
        self.aggregate_stats_poll_period = DEFAULT_POLL_AGGREGATE_STATS_PERIOD
        self.port_stats_poll_period = DEFAULT_POLL_PORT_STATS_PERIOD
        self.collection_epoch_duration = DEFAULT_COLLECTION_EPOCH_DURATION
        self.max_snapshots_per_switch = DEFAULT_MAX_STATS_SNAPSHOTS_PER_SWITCH
        """
        
    def aggregate_timer(self, dpid):
        flow = of.ofp_match() 
        flow.wildcards = 0xffff
        self.ctxt.send_aggregate_stats_request(dpid, flow,  0xff)
        self.post_callback(MONITOR_TABLE_PERIOD, lambda : self.aggregate_timer(dpid))

    def table_timer(self, dpid):
        self.ctxt.send_table_stats_request(dpid)
        self.post_callback(MONITOR_TABLE_PERIOD, lambda : self.table_timer(dpid))

    def port_timer(self, dpid):
        self.ctxt.send_port_stats_request(dpid, OFPP_NONE)
        self.post_callback(MONITOR_PORT_PERIOD, lambda : self.port_timer(dpid))

    # For each new datapath that joins, create a timer loop that monitors
    # the statistics for that switch
    def datapath_join_callback(self, dpid, stats):
        self.post_callback(MONITOR_TABLE_PERIOD, lambda : self.table_timer(dpid))
        self.post_callback(MONITOR_PORT_PERIOD + 1, lambda :  self.port_timer(dpid))
        self.post_callback(MONITOR_AGGREGATE_PERIOD + 2, lambda :  self.aggregate_timer(dpid))
    
    def configure(self, configuration):
    
        #self.register_event(JSONMsg_event.static_get_name())
        JSONMsg_event.register_event_converter(self.ctxt)
        self.register_python_event( LinkUtilizationReplyEvent.NAME )
        self.register_python_event(SwitchQueryReplyEvent.NAME)
        self.register_handler( SwitchQueryReplyEvent.NAME, \
                               self.handle_switch_query_reply_event )
                               
        # Set everything to the default values initially
        self.table_stats_poll_period = DEFAULT_POLL_TABLE_STATS_PERIOD
        self.aggregate_stats_poll_period = DEFAULT_POLL_AGGREGATE_STATS_PERIOD
        self.port_stats_poll_period = DEFAULT_POLL_PORT_STATS_PERIOD
        self.collection_epoch_duration = DEFAULT_COLLECTION_EPOCH_DURATION
        self.max_snapshots_per_switch = DEFAULT_MAX_STATS_SNAPSHOTS_PER_SWITCH
        
        # Start our logical clock                     
        self.fire_epoch_timer()
        
        # Start some internal debugging
        self.fire_stats_debug_timer()
        self.fire_utilization_broadcasts()
        
        lg.debug( "Finished configuring monitoring" )
    
    def install(self):
        self.register_handler( JSONMsg_event.static_get_name(), \
                         lambda event: self.handle_jsonmsg_event(event))
                         
        """ Installs the monitoring component. Register all the event handlers\
        and sets up the switch polling timers."""
        self.register_handler( Datapath_join_event.static_get_name(), \
                         lambda event: self.handle_datapath_join(event))
        self.register_handler( Datapath_leave_event.static_get_name(), \
                         lambda event: self.handle_datapath_leave(event))
        # Stats reporting events
        self.register_handler( Table_stats_in_event.static_get_name(), \
                         lambda event: self.handle_table_stats_in(event))
        self.register_handler( Port_stats_in_event.static_get_name(), \
                         lambda event: self.handle_port_stats_in(event))
        self.register_handler( Aggregate_stats_in_event.static_get_name(), \
                         lambda event: self.handle_aggregate_stats_in(event))
        self.register_handler( Flow_stats_in_event.static_get_name(), \
                         lambda event: self.handle_flow_stats_in(event))
        self.register_handler( Queue_stats_in_event.static_get_name(), \
                         lambda event: self.handle_queue_stats_in(event))
        self.register_handler( LinkUtilizationReplyEvent.NAME, \
                               self.handle_link_util_reply_event )
        
    def handle_jsonmsg_event(self, e):
        
        msg = json.loads(e.jsonstring)
        
        if msg["type"] != "monitoring" :
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
        
        # Store 
        self.pending_gui_queries[msg["xid"]] = e
        
        lg.debug( "got JSON switch query request")
        dpid = int(str(msg["dpid"]), 16)
        if msg["command"] == "portstats" :
            self.pending_switch_queries.add( msg["xid"] )
            self.send_port_stats_request( dpid, msg["xid"] )
            
        elif msg["command"] == "tablestats":
            self.pending_switch_queries.add( msg["xid"] )
            self.send_table_stats_request( dpid, msg["xid"] )
            
        elif msg["command"] == "aggstats":
            self.pending_switch_queries.add( msg["xid"] )
            flow = of.ofp_match()
            flow.wildcards = 0xffffffff
            self.send_aggregate_stats_request( dpid, flow,  0xff, msg["xid"] )
            
        elif msg["command"] == "latestsnapshot":
            # Look at the latest snapshot we have (if any) for this switch
            # and post a custom event
            if dpid in self.switches:
                self.pending_switch_queries.add( msg["xid"] )
                latest_snapshot = self.get_latest_switch_stats(dpid)
                if latest_snapshot != None:
                    reply = SwitchQueryReplyEvent( msg["xid"], dpid, \
                                SwitchQueryReplyEvent.QUERY_LATEST_SNAPSHOT,\
                                      latest_snapshot )
                    self.post( pyevent( SwitchQueryReplyEvent.NAME, reply ) )
        
        elif msg["command"] == "flowstats":
            self.pending_switch_queries.add( msg["xid"] )
            flow = of.ofp_match()
            flow.wildcards = 0xffffffff
            self.send_flow_stats_request(dpid, flow,  0xff, msg["xid"])
        
        elif msg["command"] == "queuestats":
            self.pending_switch_queries.add( msg["xid"] )
            self.send_queue_stats_request(dpid, msg["xid"])
            
        return CONTINUE
    
    def handle_switch_query_reply_event(self, event):
        lg.debug( "handling switch_query_reply_event" )
        
        if event.pyevent.xid in self.pending_switch_queries:
            
            # Remove the xid from our todo list
            self.pending_switch_queries.remove( event.pyevent.xid )
            
            # Look at the query type and craft the right kind of
            # message
            msg = {}
            msg["type"] = "monitoring"
            msg["xid"] = event.pyevent.xid
            msg["dpid"] = event.pyevent.dpid
            msg["data"] = json.dumps(event, sort_keys=True, \
                                      default=self.encode_switch_query)
            
            # Figure out what kind of query reply came back
            if event.pyevent.query_type == \
                    SwitchQueryReplyEvent.QUERY_PORT_STATS:
                lg.debug( "got port stats reply" )
                msg["msg_type"] = "portstats"
            elif event.pyevent.query_type == \
                    SwitchQueryReplyEvent.QUERY_TABLE_STATS:
                lg.debug( "got table stats reply" )
                msg["msg_type"] = "tablestats"
            elif event.pyevent.query_type == \
                    SwitchQueryReplyEvent.QUERY_AGG_STATS:
                lg.debug( "got agg stats reply" )
                msg["msg_type"] = "aggstats"
            elif event.pyevent.query_type == \
                    SwitchQueryReplyEvent.QUERY_LATEST_SNAPSHOT:
                lg.debug( "got latest snapshot reply" )
                msg["msg_type"] = "latestsnapshot"
            elif event.pyevent.query_type == \
                    SwitchQueryReplyEvent.QUERY_FLOW_STATS:
                lg.debug( "got flow stats reply" )
                msg["msg_type"] = "flowstats"
            elif event.pyevent.query_type == \
                    SwitchQueryReplyEvent.QUERY_QUEUE_STATS:
                lg.debug( "got queue stats reply" )
                msg["msg_type"] = "queuestats"
                                          
            stream = self.pending_gui_queries.pop( event.pyevent.xid )
            stream.reply(json.dumps(msg))
            
        return CONTINUE
        
    # Construct and send our own stats request messages so we can make use
    # of the xid field (store our logical clock/collection epoch here) to
    # detect whether stats replies from switches are delayed, lost or
    # re-ordered
    def send_table_stats_request(self, dpid, xid=-1):
        """Send a table stats request to a switch (dpid).
        @param dpid - datapath/switch to contact
        """
        # Build the request 
        request = of.ofp_stats_request()
        if xid == -1:
            request.header.xid = c_htonl(long(self.collection_epoch))
        else:
            request.header.xid = c_htonl(xid)
        request.header.type = openflow.OFPT_STATS_REQUEST
        request.type = openflow.OFPST_TABLE
        request.flags = 0
        request.header.length = len(request.pack())
        self.send_openflow_command(dpid, request.pack())
        
    def send_port_stats_request(self, dpid, xid=-1):
        """Send a port stats request to a switch (dpid).
        @param dpid - datapath/switch to contact
        """
        # Build port stats request message
        request = of.ofp_stats_request()
        if xid == -1:
            request.header.xid = c_htonl(long(self.collection_epoch))
        else:
            request.header.xid = c_htonl(xid)
        request.header.type = openflow.OFPT_STATS_REQUEST
        request.type = openflow.OFPST_PORT
        request.flags = 0
        
        # Need a body for openflow v1.x.x but not for 0.9.x
        # Construct body as a port_stats_request - need something packable
        body = of.ofp_port_stats_request()
        # Get stats on all ports using OFPP_NONE
        body.port_no = openflow.OFPP_NONE

        request.header.length = len(request.pack()) + len(body.pack())
        self.send_openflow_command(dpid, request.pack() +  body.pack())

    def send_aggregate_stats_request(self, dpid, match,  table_id, xid=-1):
        """Send an aggregate stats request to a switch (dpid).
        @param dpid - datapath/switch to contact
        @param match - ofp_match structure
        @param table_id - table to query
        """
        # Create the stats request header
        request = of.ofp_stats_request()
        if xid == -1:
            request.header.xid = c_htonl(long(self.collection_epoch))
        else:
            request.header.xid = c_htonl(xid)
        request.header.type = openflow.OFPT_STATS_REQUEST
        request.type = openflow.OFPST_AGGREGATE
        request.flags = 0
        # Create the stats request body
        body = of.ofp_aggregate_stats_request()
        body.match = match
        body.table_id = table_id
        body.out_port = openflow.OFPP_NONE
        # Set the header length
        request.header.length = len(request.pack()) + len(body.pack())
        self.send_openflow_command(dpid, request.pack() + body.pack())

    def send_flow_stats_request(self, dpid, match, table_id, xid=-1):
        """Send a flow stats request to a switch (dpid).
        @param dpid - datapath/switch to contact                               
        @param match - ofp_match structure                                     
        @param table_id - table to query 
        """
        # Create the stats request header
        request = of.ofp_stats_request()
        if xid == -1:
            request.header.xid = c_htonl(long(self.collection_epoch))
        else:
            request.header.xid = c_htonl(xid)
        
        lg.debug( "sending flow stats request xid: %d" % \
                      (c_htonl(request.header.xid)) )
        request.header.type = openflow.OFPT_STATS_REQUEST
        request.type = openflow.OFPST_FLOW
        request.flags = 0
        # Create the stats request body
        body = of.ofp_flow_stats_request()
        body.match = match
        body.table_id = table_id
        body.out_port = openflow.OFPP_NONE
        request.header.length = len(request.pack()) + len(body.pack())
        self.send_openflow_command(dpid, request.pack() + body.pack())

    def send_queue_stats_request(self, dpid, xid=-1):
        lg.debug( "sending queue stats request" )
        """Send a queue stats request to a switch (dpid). 
        @param dpid - datapath/switch to contact
        """
        # Create the stats request header 
        request = of.ofp_stats_request()
        if xid == -1:
            request.header.xid = c_htonl(long(self.collection_epoch))
        else:
            request.header.xid = c_htonl(xid)
        request.header.type = openflow.OFPT_STATS_REQUEST
        request.type = openflow.OFPST_QUEUE
        request.flags = 0
        # Create the stats request body
        body = of.ofp_queue_stats_request()
        body.port_no = openflow.OFPP_ALL
        body.queue_id = openflow.OFPQ_ALL
        request.header.length = len(request.pack()) + len(body.pack())
        self.send_openflow_command(dpid, request.pack() + body.pack())

    # Command API
    def count_silent_switches(self):
        """Count the number of switches that have not responded to stats
           requests."""
        return len(self.silent_switches)

    def get_all_silent_switches(self):
        """Return the set of switches that have not responded to stats
           requests."""
        return self.silent_switches

    def get_all_switch_stats(self, dpid):
        """API call to get all the recent readings of switch stats
        @param dpid - datapath/switch snapshots to return
        """
        if dpid in self.switches:
            return self.snapshots[dpid]
        else: 
            return {}

    def get_max_stats_reply_epoch(self):
        """API call to return the latest epoch for which we have at
        least 1 switch stats reply"""
        return self.max_stats_reply_epoch

    def get_latest_port_bps(self, time_consistent=True):
        port_utilizations = []
        # Look at the latest reply epoch
        # For each switch get any snapshot that is ready with
        # collected for the latest reply epoch
        # Go through that snapshot and pull out the port
        # info
        # Create portutilization instance: 
        # [dpid,port,bps_transmitted,bps_received]
        for dpid in self.switches:
            # Get the latest snapshot for each switch
            latest_snapshot = self.get_latest_switch_stats(dpid)
            # If there's a recent snapshot see if it's ready (complete)
            # AND for the most recent collection epoch
            if latest_snapshot != None and latest_snapshot.ready(): 
                #lg.debug( "found latest snapshot for dpid 0x%x" % (dpid) )
                # If we want the snapshots to all be from the same 
                # most recent collection epoch then ignore the ones that aren't
                if time_consistent and (latest_snapshot.collection_epoch != \
                        self.max_stats_reply_epoch):
                    continue
                    
                #if latest_snapshot.ready() and \
                        #latest_snapshot.collection_epoch\
                        #== self.max_stats_reply_epoch:
                    # Now go thru the snapshot's port info and
                    # create port utilization instances and
                    # add them to the list
                for port in latest_snapshot.port_info:
                    portinfo = latest_snapshot.port_info[port]
                    port_util = PortUtilization()
                    port_util.dpid = dpid
                    port_util.port = portinfo.port_number
                    
                    port_util.bps_transmitted = \
                        portinfo.estimate_bits_sent_per_sec()
                    port_util.bps_received = \
                        portinfo.estimate_bits_received_per_sec()
                        
                    port_util.capacity = (self.port_cap[port_util.dpid][port_util.port].to_dict())['max_speed']
                    
                    port_utilizations.append(port_util)
            else:
                pass

        return port_utilizations

    def get_latest_switch_stats(self, dpid):
        """API call to get the latest stats snapshot for a switch
        @param dpid - datapath/switch snapshot to return
        """
        if dpid not in self.switches:
            return None

        switch_stats_q = self.snapshots[dpid]
        if len(switch_stats_q) > 0: 
            return switch_stats_q[0]
        else:
            return None

    def get_all_port_capabilities(self, dpid):
        """API call to get all the port capabilities for a switch
        @param dpid - datapath/switch port capabilities to return
        """
        if dpid not in self.port_cap:
            return None
        else:
            return self.port_cap[dpid]
    
    def get_port_capabilities(self, dpid, port_num):
        """API call to get the capabilities of a specific port for a switch
        @param dpid - datapath/switch to get capabilities for
        @param port_num - specific port to get capabilities for
        """
        if dpid not in self.port_cap:
            return None
        else: 
            return (self.port_cap[dpid])[port_num]

    # Timers
    # Stats debugging timer
    def fire_stats_debug_timer(self):
        self.get_latest_port_bps()
        # re-post timer at some multiple of the collection epoch
        self.post_callback( self.collection_epoch_duration*2, \
                                self.fire_stats_debug_timer )

    def fire_utilization_broadcasts(self):
        port_utils = self.get_latest_port_bps()
        # Set xid = -1 when its unsolicited
        event = LinkUtilizationReplyEvent( -1, port_utils )
        # Post event
        self.post( pyevent( LinkUtilizationReplyEvent.NAME, event ) )
        self.post_callback( DEFAULT_POLL_UTIL_PERIOD,\
                        self.fire_utilization_broadcasts )

    # Logical clock timer    
    def fire_epoch_timer(self):
        """Handler updates the logical clock used by Monitoring."""        
        
        '''
        lg.debug( "---silent switches start at epoch: %d---" \
                       % (self.collection_epoch) )
        for dpid in self.silent_switches:
            lg.debug( dpid )
            if self.topo.all_connected():
                self.topo.setNodeFaultStatus(dpid, True)
            # Publish an event for each silent switch
            silentSwitch = SilentSwitchEvent( -1, dpid )
            self.post( pyevent( SilentSwitchEvent.NAME, silentSwitch ) )
        lg.debug( "---silent switches end at epoch: %d---" \
                       % (self.collection_epoch))
        
        # Add all switches to the silent list at the start of every
        # epoch. We'll remove them as they reply to stats requests
        for dpid in self.switches:
            if dpid not in self.silent_switches:
                #self.topo.setNodeFaultStatus(dpid, False)
                self.silent_switches.add(dpid)
        '''
        # Update the epoch
        self.collection_epoch += 1
        lg.debug( "updated clock: %d" % (self.collection_epoch) )
        self.post_callback( self.collection_epoch_duration, \
                                self.fire_epoch_timer )
    
    # Table stats timer
    def fire_table_stats_timer(self, dpid):
        """Handler polls a swtich for its table stats.
        @param dpid - datapath/switch to contact
        """
        #collection epoch: {0:d}".format(self.collection_epoch)    
        # Send a message and renew timer (if the switch is still around)       
        if dpid in self.switches:
            # Send a table stats request  
            self.send_table_stats_request(dpid)    
            self.post_callback(self.table_stats_poll_period, \
                       lambda : self.fire_table_stats_timer(dpid))

    # Port stats timer
    def fire_port_stats_timer(self, dpid):
        """Handler polls a switch for its port stats.
        @param dpid - datapath/switch to contact
        """
        # collection epoch: {0:d}".format(self.collection_epoch)
        # Send a ports stats message and renew timer 
        # (if the switch is still around)
        if dpid in self.switches:
            self.send_port_stats_request(dpid)    
            self.post_callback(self.port_stats_poll_period, \
                        lambda :  self.fire_port_stats_timer(dpid))

    # Aggregate stats timer    
    def fire_aggregate_stats_timer(self, dpid):
        """Handler polls a switch for its aggregate stats.
        @param dpid - datapath/switch to contact
        """
        # collection epoch: {0:d}".format(self.collection_epoch)
        # Send a message and renew timer (if the switch is still around)
        if dpid in self.switches:
            # Grab data for all flows
            flow = of.ofp_match() 
            flow.wildcards = 0xffffffff
            self.send_aggregate_stats_request(dpid, flow,  0xff)    
            self.post_callback(self.aggregate_stats_poll_period, \
                        lambda :  self.fire_aggregate_stats_timer(dpid))

    def fire_flow_stats_timer(self, dpid):
        """
        Handler polls a switch for its aggregate stats.
        @param dpid - datapath/switch to contact
        """
        if dpid in self.switches:
            # Grab data for all flows
            flow = of.ofp_match()
            flow.wildcards = 0xffffffff
            self.send_flow_stats_request(dpid, flow,  0xff)
            self.post_callback(10, lambda : self.fire_flow_stats_timer(dpid))
    
    def fire_queue_stats_timer(self, dpid):
        """
        Handler polls a switch for its queue stats.
        @param dpid - datapath/switch to contact
        """
        if dpid in self.switches:
            self.send_queue_stats_request(dpid)
            self.post_callback(10, lambda : self.fire_queue_stats_timer(dpid))
        
    # Event handlers. FYI if you need/want to find out what fields exist 
    # in a specific event type look at src/nox/lib/util.py at the utility 
    # functions that are used to manipulate them
    def handle_datapath_join(self, event):
        """Handler responds to switch join events.
        @param event datapath/switch join event to handle
        """
        # grab the dpid from the event
        dpid = event.datapath_id
        epoch = self.collection_epoch

        '''
        ports = event.ports
        for item in ports:
            # Figure out what speeds are supported
            port_enabled = (item['config'] & openflow.OFPPC_PORT_DOWN) == 0
            link_enabled = (item['state'] & openflow.OFPPS_LINK_DOWN) == 0
            # Look at features supported, advertised and curr(ent)
            supports_10MB_HD = (item['curr'] & openflow.OFPPF_10MB_HD) == \
                                                     openflow.OFPPF_10MB_HD
            supports_10MB_FD = (item['curr'] & openflow.OFPPF_10MB_FD) > 0
            supports_100MB_HD = (item['curr'] & openflow.OFPPF_100MB_HD) > 0
            supports_100MB_FD = (item['curr'] & openflow.OFPPF_100MB_FD) == \
                                                      openflow.OFPPF_100MB_FD
            supports_1GB_HD = (item['curr'] & openflow.OFPPF_1GB_HD) > 0
            supports_1GB_FD = (item['curr'] & openflow.OFPPF_1GB_FD) > 0
            supports_10GB_FD = (item['curr'] & openflow.OFPPF_10GB_FD) > 0
        '''
        
        # Set up some timers for polling this switch periodically
        # Whenever a new switch joins set up some timers for polling it 
        # for its stats (using the monitor.py example as a rough reference)
        if not dpid in self.switches:
            lg.debug( "Handling switch join. Epoch: %d, dpid: 0x%x" % \
                       (epoch,dpid) )
            # Add this switch to the set of switches being monitored
            self.switches.add(dpid)
            # Create an entry to store its stats snapshots
            self.snapshots[dpid] = deque()
            # Create an entry to store its port capabilities
            self.port_cap[dpid] = dict()
            # Add ports
            ports = event.ports
            for item in ports:
                # create port capability
                new_port_cap = PortCapability()
                # set fields
                new_port_cap.port_name = item['name']
                new_port_cap.port_number = item['port_no']
                new_port_cap.port_enabled = ((item['config'] & \
                                             openflow.OFPPC_PORT_DOWN) == 0)
                new_port_cap.link_enabled = (item['state'] & \
                                             openflow.OFPPS_LINK_DOWN) == 0
                new_port_cap.supports_10Mb_hd = (item['curr'] & \
                                                openflow.OFPPF_10MB_HD) == \
                                                openflow.OFPPF_10MB_HD
                new_port_cap.supports_10Mb_fd = (item['curr'] & \
                                                 openflow.OFPPF_10MB_FD) > 0
                new_port_cap.supports_100Mb_hd = (item['curr'] & \
                                                  openflow.OFPPF_100MB_HD) > 0
                new_port_cap.supports_100Mb_fd = (item['curr'] & \
                                                  openflow.OFPPF_100MB_FD) == \
                                                  openflow.OFPPF_100MB_FD
                new_port_cap.supports_1Gb_hd = (item['curr'] & \
                                                openflow.OFPPF_1GB_HD) > 0
                new_port_cap.supports_1Gb_fd = (item['curr'] & \
                                                openflow.OFPPF_1GB_FD) > 0
                new_port_cap.supports_10Gb_fd = (item['curr'] & \
                                                openflow.OFPPF_10GB_FD) > 0
                # Have the port capability instance compute the
                # max port speed
                new_port_cap.compute_max_port_speed_bps()
                # store the port capability instance to the port map/dict
                (self.port_cap[dpid])[new_port_cap.port_number]=new_port_cap
                
            # Set up timers            
            self.post_callback(self.table_stats_poll_period, \
                         lambda : self.fire_table_stats_timer(dpid))
            self.post_callback(self.port_stats_poll_period, \
                         lambda :  self.fire_port_stats_timer(dpid))
            self.post_callback(self.aggregate_stats_poll_period, \
                         lambda :  self.fire_aggregate_stats_timer(dpid))
                         
        # Mark switch as silent until we get a stats reply from it
        if dpid not in self.silent_switches:
            self.silent_switches.add(dpid)

        return CONTINUE

    def handle_datapath_leave(self, event):
        """Handler responds to switch leave events.
        @param event - datapath leave event to handle
        """
        dpid = event.datapath_id
        lg.debug( "Handling switch leave. Epoch: %d, dpid: 0x%x" % \
                                              (self.collection_epoch, dpid) )
        # drop all the stats for this switch
        if dpid in self.switches:
            self.switches.remove(dpid)
            # Throw away its stats snapshots
            del self.snapshots[dpid]

        # Remove switch from the slient_switch list if it's currently on it
        if dpid in self.silent_switches:
            self.silent_switches.remove(dpid)
            
        return CONTINUE
    
    # Handlers for switch stats events
    def handle_aggregate_stats_in(self, event):
        """Handler responds to receiving aggregate switch stats.
        @param event - aggregate stats in event to handle
        """
        # Get the snapshot list
        dpid = event.datapath_id
        # Use the xid as the current collection epoch
        current_collection_epoch = event.xid #self.collection_epoch

        if event.xid in self.pending_switch_queries:
            lg.debug( "responding to switch query for aggregate stats" )
            # Publish custom event
            reply = SwitchQueryReplyEvent( event.xid, event.datapath_id, \
                                       SwitchQueryReplyEvent.QUERY_AGG_STATS,\
                                       event )
            self.post( pyevent( SwitchQueryReplyEvent.NAME, reply ) )
            '''
            # Remove the xid from our todo list
            self.pending_switch_queries.remove( event.xid )
            '''


        # Check whether this stats reply pushes forward out notion of   
        # "latest" 
        '''
        if current_collection_epoch > self.max_stats_reply_epoch:
            self.max_stats_reply_epoch = current_collection_epoch
        '''
        
        # Remove switch from silent_switch list if it's on it
        if dpid in self.silent_switches:
            self.silent_switches.remove(dpid)

        # Get the deque holding our snapshots
        try:
            switch_stats_q = self.snapshots[dpid]

            # Are we adding a new snapshot?    
            if len(switch_stats_q) == 0:
                # Create new snapshot and save it
                new_snapshot = Snapshot( self )
                # Set the collection epoch and the datapath id
                new_snapshot.collection_epoch = current_collection_epoch
                new_snapshot.timestamp = time.time()
                new_snapshot.dpid = dpid
                new_snapshot.number_of_flows = event.flow_count
                new_snapshot.bytes_in_flows = event.byte_count
                new_snapshot.packets_in_flows = event.packet_count
                # Always add the most recent snapshot to the front of the queue
                switch_stats_q.appendleft(new_snapshot)
            else:
                pass
            
            # Get the latest snapshot
            latest_snapshot = switch_stats_q[0]

            # If it's for this collection epoch, just update it/overwrite it
            if latest_snapshot.collection_epoch == current_collection_epoch:
                latest_snapshot.timestamp = time.time()
                latest_snapshot.number_of_flows = event.flow_count
                latest_snapshot.bytes_in_flows = event.byte_count
                latest_snapshot.packets_in_flows = event.packet_count
            else:
                # Only add a new snapshot if it's later in time
                # than the "latest" snapshot
                if current_collection_epoch > latest_snapshot.collection_epoch:
                    new_snapshot = Snapshot( self )
                    new_snapshot.collection_epoch = current_collection_epoch
                    new_snapshot.timestamp = time.time()
                    new_snapshot.dpid = dpid
                    new_snapshot.number_of_flows = event.flow_count
                    new_snapshot.bytes_in_flows = event.byte_count
                    new_snapshot.packets_in_flows = event.packet_count
                    # Calculate any deltas from the latest snapshot
                    new_snapshot.epoch_delta = current_collection_epoch - \
                        latest_snapshot.collection_epoch
                    # Always add the most recent snapshot to the front 
                    # of the queue
                    switch_stats_q.appendleft(new_snapshot)
                    # Limit the number of old snapshots we keep around        
                    if len(switch_stats_q) > self.max_snapshots_per_switch:
                        switch_stats_q.pop()
                        
        except Exception:
            pass
        finally:        
            pass

        return CONTINUE

    def handle_table_stats_in(self, event):
        """Handle receipt of table stats from a switch.
        @param event - table stats event to handle
        """
        dpid = event.datapath_id
        
        if event.xid in self.pending_switch_queries:
            lg.debug( "responding to switch query for table stats" )
            # Publish custom event
            reply = SwitchQueryReplyEvent( event.xid, event.datapath_id, \
                                      SwitchQueryReplyEvent.QUERY_TABLE_STATS,\
                                      event )
            self.post( pyevent( SwitchQueryReplyEvent.NAME, reply ) )

        # Remove switch from silent_switch list if it's on it 
        if dpid in self.silent_switches:
            self.silent_switches.remove(dpid)

        tables = event.tables
        return CONTINUE

    def handle_port_stats_in(self, event):
        """Handle receipt of port stats from a switch.
        @param event - port stats event to handle
        """
        dpid = event.datapath_id
        if event.xid in self.pending_switch_queries:
            lg.debug( "responding to switch query for port stats" )
            # Publish custom event
            reply = SwitchQueryReplyEvent( event.xid, event.datapath_id, \
                                          SwitchQueryReplyEvent.QUERY_PORT_STATS,\
                                          event )
            self.post( pyevent( SwitchQueryReplyEvent.NAME, reply ) )

        # Use the reply xid as the current collection epoch
        current_collection_epoch = event.xid #self.collection_epoch

        # Check whether this stats reply pushes forward out notion of
        # "latest"
        if current_collection_epoch > self.max_stats_reply_epoch:
            self.max_stats_reply_epoch = current_collection_epoch

        # Remove switch from silent_switch list if it's on it
        if dpid in self.silent_switches:
            self.silent_switches.remove(dpid)
            '''
            self.topo.setNodeFaultStatus(dpid, False)
            '''
        ports = event.ports
        try:            
            switch_stats_q = self.snapshots[dpid]

            # Are we adding a new snapshot?    
            if len(switch_stats_q) == 0:
                # Create new snapshot and save it
                new_snapshot = Snapshot( self )
                # Set the collection epoch and the datapath id
                new_snapshot.collection_epoch = current_collection_epoch
                new_snapshot.timestamp = time.time()                
                new_snapshot.dpid = dpid
                new_snapshot.store_port_info(ports, self.port_cap[dpid])
                # Always add the most recent snapshot to the front of the queue
                switch_stats_q.appendleft(new_snapshot)
            else:
                pass
            
            # Get the latest snapshot
            latest_snapshot = switch_stats_q[0]

            # If the latest snapshot is for this collection epoch, just 
            # update it
            if latest_snapshot.collection_epoch == current_collection_epoch:
                latest_snapshot.timestamp = time.time()
                latest_snapshot.store_port_info(ports, self.port_cap[dpid])
                # update deltas if we can
                if len(switch_stats_q) > 1:
                    previous_snapshot = switch_stats_q[1]
                    latest_snapshot.compute_delta_from(previous_snapshot)
            else:
                # Only add a new snapshot if it's more recent
                # than the collection epoch of the "latest" snapshot
                if current_collection_epoch > latest_snapshot.collection_epoch:
                    new_snapshot = Snapshot( self )
                    new_snapshot.collection_epoch = current_collection_epoch
                    new_snapshot.timestamp = time.time()
                    '''
                    new_snapshot.ports_active = ports_active
                    '''
                    new_snapshot.dpid = dpid
                    # store port info
                    new_snapshot.store_port_info(ports, self.port_cap[dpid])
                    # Compute deltas from the previous snapshot
                    new_snapshot.compute_delta_from(latest_snapshot)
                    # Always add the most recent snapshot to the 
                    # front of the queue
                    switch_stats_q.appendleft(new_snapshot)
                    # Limit the number of old snapshots we keep around        
                    if len(switch_stats_q) > self.max_snapshots_per_switch:
                        switch_stats_q.pop()
        except Exception:
            pass
        finally:        
            pass
        return CONTINUE
    
    def handle_flow_stats_in(self, event):

        if event.xid in self.pending_switch_queries:
            lg.debug( "responding to switch query for flow stats" )
            # Publish custom event
            reply = SwitchQueryReplyEvent( event.xid, event.datapath_id, \
                               SwitchQueryReplyEvent.QUERY_FLOW_STATS, event )
            self.post( pyevent( SwitchQueryReplyEvent.NAME, reply ) )
        return CONTINUE

    def handle_queue_stats_in(self,event):
        lg.debug( "handle queue stats in: %s" % (event.__dict__) )
        
        if event.xid in self.pending_switch_queries:
            lg.debug( "responding to switch query for queue stats" )
            # Publish custom event
            reply = SwitchQueryReplyEvent( event.xid, event.datapath_id, \
                               SwitchQueryReplyEvent.QUERY_QUEUE_STATS, event )
            self.post( pyevent( SwitchQueryReplyEvent.NAME, reply ) )
        return CONTINUE
    
    # Static functions for encoding custom events as json
    def encode_switch_query( self, obj ):
        if isinstance( obj.pyevent, SwitchQueryReplyEvent ):
            if obj.pyevent.query_type == \
                    SwitchQueryReplyEvent.QUERY_PORT_STATS:
                return [obj.pyevent.reply.ports]
            elif obj.pyevent.query_type == \
                    SwitchQueryReplyEvent.QUERY_TABLE_STATS:
                return [obj.pyevent.reply.tables]
            elif obj.pyevent.query_type == \
                    SwitchQueryReplyEvent.QUERY_AGG_STATS:
                # Create a dict
                dict = {}
                dict['packet_count']=obj.pyevent.reply.packet_count
                dict['byte_count']=obj.pyevent.reply.byte_count
                dict['flow_count']=obj.pyevent.reply.flow_count
                return [dict]
            elif obj.pyevent.query_type == \
                    SwitchQueryReplyEvent.QUERY_LATEST_SNAPSHOT:
                return obj.pyevent.reply.to_dict()
            elif obj.pyevent.query_type == \
                    SwitchQueryReplyEvent.QUERY_FLOW_STATS:
                return [obj.pyevent.reply.flows]
            elif obj.pyevent.query_type == \
                    SwitchQueryReplyEvent.QUERY_QUEUE_STATS:
                return [obj.pyevent.reply.queues]
        else:
            lg.debug( "not encoding switch query reply event" )
            raise TypeError( repr(obj) + " is not JSON serializable" )
    
    def handle_link_util_reply_event(self, event):
        if len(event.pyevent.port_utils) > 0:
        
            portUtilsMsg = {}
            portUtilsMsg['type'] = "monitoring"
            portUtilsMsg['msg_type'] = "linkutils"
            utils = []
            for util in event.pyevent.port_utils:
                u = {}
                u['dpid'] = hex(util.dpid)[2:len(hex(util.dpid))-1]
                u['port'] = str(util.port)
                
                '''***THIS CALCULATION OF UTILIZATION IS DISPUTABLE***'''
                add = util.bps_transmitted+util.bps_received
                avgrate = add/2
                if util.capacity:
                    ut = float(avgrate) / float(util.capacity)
                else:
                    ut = float(0)
                u['utilization'] = ut
                
                utils.append(u)
            portUtilsMsg['utils'] = utils
            if event.pyevent.xid != -1:
                lg.debug( "Replying to active poll" )
                if event.pyevent.xid in self.pending_queries:
                    proto = self.pending_queries.pop( event.pyevent.xid )
                    if proto.connected:
                        proto.send(portUtilsMsg)
            else:
                # send to subscribed listeners
                if "linkutils" in self.subscribers:
                    for stream in self.subscribers["linkutils"]:
                        stream.reply(json.dumps(portUtilsMsg))
        return CONTINUE


    def getInterface(self):
        return str(Monitoring)


def getFactory():
    """Returns an object able to create monitoring instances."""
    class Factory:
        """A class able to create monitoring instances."""
        def instance(self, ctxt):
            """Returns a/the monitoring instance."""
            return Monitoring(ctxt)

    return Factory()






class PortCapability: 
    """Class keeps track of port capabilities/capcity"""
    def __init__(self):
        self.port_name = ""
        self.port_number = -1                                                  
        self.port_enabled = False                                              
        self.link_enabled = False                                              
        self.supports_10Mb_hd = False                                          
        self.supports_10Mb_fd = False                                          
        self.supports_100Mb_hd = False                                         
        self.supports_100Mb_fd = False                                         
        self.supports_1Gb_hd = False                                           
        self.supports_1Gb_fd = False                                           
        self.supports_10Gb_fd = False                                          
        self.max_speed = 0                                                     
        self.full_duplex = False   
    
    def compute_max_port_speed_bps(self):
        """Compute the max port speed in bps"""
        if self.supports_10Gb_fd == True:
            self.max_speed = 10000 * 1e6
        elif self.supports_1Gb_hd == True or self.supports_1Gb_fd == True:
            self.max_speed = 1000 * 1e6
        elif self.supports_100Mb_hd == True or self.supports_100Mb_fd == True:
            self.max_speed = 100 * 1e6
        elif self.supports_10Mb_hd == True or self.supports_10Mb_fd == True:
            self.max_speed = 10 * 1e6
        else:
            self.max_speed = 0
        return self.max_speed
    
    def to_dict(self):
        dict = {}
        dict['port_name'] = self.port_name
        dict['port_number'] = self.port_number
        dict['port_enabled'] = self.port_enabled
        dict['max_speed'] = self.compute_max_port_speed_bps()
        dict['full_duplex'] = self.supports_10Gb_fd or self.supports_1Gb_fd\
            or self.supports_100Mb_fd or self.supports_10Mb_fd
        return dict

class PortUtilization:
    """Class stores port tx/rx utilization"""
    def __init__(self):
        self.dpid = -1
        self.port = -1
        self.bps_transmitted = 0.0
        self.bps_received = 0.0
        ###self.max_speed = 0

class PortInfo:
    """Class keeps track of port capabilities and recent usage"""
    def __init__(self, port_capabilities, monitoring_module):
        """Init 
        @param port_capabilities - port capacity data
        """
        self.owner_snapshot = None # Snapshot we belong to
        self.port_cap = port_capabilities
        self.port_number = -1
        self.monitoring = monitoring_module
        # Per-port counters
        self.total_rx_bytes = -1
        self.total_tx_bytes = -1
        self.total_rx_packets = -1
        self.total_tx_packets = -1
        self.total_rx_packets_dropped = -1
        self.total_tx_packets_dropped = -1
        self.total_rx_errors = -1
        self.total_tx_errors = -1
        # changes in port stats data since the last collection epoch
        self.delta_rx_bytes = -1
        self.delta_tx_bytes = -1
        self.delta_rx_packets = -1
        self.delta_tx_packets = -1
        self.delta_rx_packets_dropped = -1
        self.delta_tx_packets_dropped = -1
        self.delta_rx_errors = -1
        self.delta_tx_errors = -1

    def to_dict(self):
        dict = {}
        dict['port_number'] = self.port_number
        # Save the nested capabilities structure
        dict['port_cap'] = self.port_cap.to_dict()
        # Counters
        dict['total_rx_bytes'] = self.total_rx_bytes
        dict['total_tx_bytes'] = self.total_tx_bytes
        dict['total_rx_packets'] = self.total_rx_packets
        dict['total_tx_packets'] = self.total_tx_packets
        dict['total_rx_packets_dropped'] = self.total_rx_packets_dropped
        dict['total_tx_packets_dropped'] = self.total_tx_packets_dropped
        dict['total_rx_errors'] = self.total_rx_errors
        dict['total_tx_errors'] = self.total_tx_errors
        # Deltas
        dict['delta_rx_bytes'] = self.delta_rx_bytes
        dict['delta_tx_bytes'] = self.delta_tx_bytes
        dict['delta_rx_packets'] = self.delta_rx_packets
        dict['delta_tx_packets'] = self.delta_tx_packets
        dict['delta_rx_packets_dropped'] = self.delta_rx_packets_dropped
        dict['delta_tx_packets_dropped'] = self.delta_tx_packets_dropped
        dict['delta_rx_errors'] = self.delta_rx_errors
        dict['delta_tx_errors'] = self.delta_tx_errors
        return dict
      
    def compute_delta_from(self, rhs, send_alarm = True):
        """Compute the counter and epoch deltas between this snapshot 
        and another (rhs)
        @param rhs - port info object to compute delta from
        """
        self.delta_rx_bytes = max(0, self.total_rx_bytes - rhs.total_rx_bytes)
        self.delta_tx_bytes = max(0, self.total_tx_bytes - rhs.total_tx_bytes)
        self.delta_rx_packets = max(0, \
                                self.total_rx_packets - rhs.total_rx_packets)
        self.delta_tx_packets = max(0,\
                                 self.total_tx_packets - rhs.total_tx_packets)
        self.delta_rx_packets_dropped = max(0, \
                                      self.total_rx_packets_dropped - \
                                        rhs.total_rx_packets_dropped)
        self.delta_tx_packets_dropped = max(0,\
                                        self.total_tx_packets_dropped - \
                                        rhs.total_tx_packets_dropped)
        self.delta_rx_errors = max(0,\
                                 self.total_rx_errors - rhs.total_rx_errors)
        self.delta_tx_errors = max(0,\
                                 self.total_tx_errors - rhs.total_tx_errors)
        
        port_has_problems = False
        if self.delta_rx_packets_dropped > 0 or \
                self.delta_tx_packets_dropped > 0:
            port_has_problems = True
        elif self.delta_rx_errors > 0 or self.delta_tx_errors > 0:
            port_has_problems = True
        
        if port_has_problems and send_alarm:
            # Post a custom port error event
             portError = PortErrorEvent( -1, self.owner_snapshot.dpid, \
                                              self.port_number )
             portError.rx_dropped = self.delta_rx_packets_dropped
             portError.tx_dropped = self.delta_tx_packets_dropped
             portError.rx_errors = self.delta_rx_errors
             portError.tx_errors = self.delta_tx_errors
             self.post( pyevent( PortErrorEvent.NAME, portError ) )
        
    def compute_max_port_speed_bps(self):
        """Compute the max port speed in bps"""
        if self.port_cap.supports_10Gb_fd:
            self.port_cap.max_speed = 10000 * 1e6
        elif self.port_cap.supports_1Gb_hd or self.port_cap.supports_1Gb_fd:
            self.port_cap.max_speed = 1000 * 1e6
        elif self.port_cap.supports_100Mb_hd or \
                self.port_cap.supports_100Mb_fd:
            self.port_cap.max_speed = 100 * 1e6
        elif self.port_cap.supports_10Mb_hd or self.port_cap.supports_10Mb_fd:
            self.port_cap.max_speed = 10 * 1e6
        else:
            self.port_cap.max_speed = 0
        return self.port_cap.max_speed

    def estimate_packets_received_per_sec(self):
        """Estimate the packets received per sec
           as delta_rx_packets/(time since last collection in seconds)"""
        if self.delta_rx_packets == -1:
            return 0
        else:
            return self.delta_rx_packets / self.owner_snapshot.time_since_delta
            #(self.monitoring.collection_epoch_duration * \
            #     self.owner_snapshot.epoch_delta)
        
    def estimate_packets_sent_per_sec(self):
        """Estimate the packets sent per sec
           as delta_tx_packets/(time since last collection in seconds)"""
        if self.delta_tx_packets == -1:
            return 0
        else:
            return self.delta_tx_packets / self.owner_snapshot.time_since_delta
            #(self.monitoring.collection_epoch_duration * \
            #     self.owner_snapshot.epoch_delta)

    def estimate_bits_received_per_sec(self):
        """Estimate the bits received per sec 
           as delta_rx_bits/(time since last collection in seconds)"""
        if self.delta_rx_bytes == -1:
            return 0
        else:
            return (self.delta_rx_bytes*8) / \
                self.owner_snapshot.time_since_delta
            #(self.monitoring.collection_epoch_duration * \
            #     self.owner_snapshot.epoch_delta)

    def estimate_bits_sent_per_sec(self):
        """Estimate the bits sent per sec
           as delta_tx_bits/(time since last collection in seconds)"""
        if self.delta_tx_bytes == -1:
            return 0
        else:
            return (self.delta_tx_bytes*8) / \
                self.owner_snapshot.time_since_delta
            #(self.monitoring.collection_epoch_duration * \
            #     self.owner_snapshot.epoch_delta)

    def estimate_port_rx_utilization(self):
        """Estimate the port rx utilization as 
        [(bits received/s)/max port speed in bits per sec]*100"""
        port_speed_bps = self.port_cap.compute_max_port_speed_bps()
        #self.port_cap[self.port_number].compute_max_port_speed_bps()
        if port_speed_bps > 0:
            return (self.estimate_bits_received_per_sec()/port_speed_bps)*100
        else:
            return 0

    def estimate_port_tx_utilization(self):
        """Estimate the port rx utilization as
        [(bits received/s)/max port speed in bits per sec]*100"""
        port_speed_bps = self.port_cap.compute_max_port_speed_bps()
        #self.port_cap[self.port_number].compute_max_port_speed_bps()    
        if port_speed_bps > 0:
            return (self.estimate_bits_sent_per_sec()/port_speed_bps)*100
        else:
            return 0

    def estimate_avg_port_utilization(self):
        """Estimate the average port utilization."""
        return ( self.estimate_port_rx_utilization()+\
                    self.estimate_port_tx_utilization() )/2.0

class Snapshot:
    """Simple container for storing statistics snapshots for a switch"""
    def __init__(self, monitor_inst):
        self.monitor = monitor_inst
        # Initialize all counters to -1 that way we'll know 
        # whether things have actually been
        # updated. An update gives each counter a value >= 0
        self.dpid = -1 # what switch
        self.collection_epoch = -1 # when collected
        self.time_since_delta = 0
        self.timestamp = -1 # system time stamp
        # spacing between this snapshot and
        # the last collection epoch, should usually be 1 so check
        self.epoch_delta = -1 
        #self.ports_active = -1
        # From aggregate stats - these are point in time counts 
        # i.e. number of flows active "now"
        self.number_of_flows = -1
        self.bytes_in_flows = -1
        self.packets_in_flows = -1
        # Port stats dict - dictionary of per port counters
        self.port_info = dict()
        # Aggregate counters over ALL the ports for a specific switch
        self.total_rx_bytes = -1
        self.total_tx_bytes = -1
        self.total_rx_packets = -1
        self.total_tx_packets = -1
        self.total_rx_packets_dropped = -1
        self.total_tx_packets_dropped = -1
        self.total_rx_errors = -1
        self.total_tx_errors = -1
        # changes in Aggregate switch-level snapshot data since the 
        # last collection epoch
        self.delta_rx_bytes = -1
        self.delta_tx_bytes = -1
        self.delta_rx_packets = -1
        self.delta_tx_packets = -1
        self.delta_rx_packets_dropped = -1
        self.delta_tx_packets_dropped = -1
        self.delta_rx_errors = -1
        self.delta_tx_errors = -1
    
    def to_dict(self):
        dict = {}
        dict['dpid'] = self.dpid
        dict['collection_epoch'] = self.collection_epoch
        dict['timestamp'] = self.timestamp
        dict['time_since_delta'] = self.time_since_delta
        dict['epoch_delta'] = self.epoch_delta
        dict['number_of_flows'] = self.number_of_flows
        dict['bytes_in_flows'] = self.bytes_in_flows
        dict['packets_in_flows'] = self.packets_in_flows
        # Port info
        ports = {}
        for port_num in self.port_info:
            ports[port_num] = self.port_info[port_num].to_dict()
        dict['ports'] = ports
        # Counters
        dict['total_rx_bytes'] = self.total_rx_bytes
        dict['total_tx_bytes'] = self.total_tx_bytes
        dict['total_rx_packets'] = self.total_rx_packets
        dict['total_tx_packets'] = self.total_tx_packets
        dict['total_rx_packets_dropped'] = self.total_rx_packets_dropped
        dict['total_tx_packets_dropped'] = self.total_tx_packets_dropped
        dict['total_rx_errors'] = self.total_rx_errors
        dict['total_tx_errors'] = self.total_tx_errors
        # Deltas
        dict['delta_rx_bytes'] = self.delta_rx_bytes
        dict['delta_tx_bytes'] = self.delta_tx_bytes
        dict['delta_rx_packets'] = self.delta_rx_packets
        dict['delta_tx_packets'] = self.delta_tx_packets
        dict['delta_rx_packets_dropped'] = self.delta_rx_packets_dropped
        dict['delta_tx_packets_dropped'] = self.delta_tx_packets_dropped
        dict['delta_rx_errors'] = self.delta_rx_errors
        dict['delta_tx_errors'] = self.delta_tx_errors
        return dict
    
    def compute_delta_from(self, rhs):
        """Compute the counter and epoch deltas between this 
        snapshot and another (rhs)
        @param rhs - snapshot to compute delta from
        """
        if self.collection_epoch != rhs.collection_epoch:
            self.epoch_delta = self.collection_epoch - rhs.collection_epoch
            self.time_since_delta = self.timestamp - rhs.timestamp

        self.delta_rx_bytes = max(0, self.total_rx_bytes - rhs.total_rx_bytes)
        self.delta_tx_bytes = max(0, self.total_tx_bytes - rhs.total_tx_bytes)
        self.delta_rx_packets = max(0, \
                                self.total_rx_packets - rhs.total_rx_packets)
        self.delta_tx_packets = max(0, \
                                self.total_tx_packets - rhs.total_tx_packets)
        self.delta_rx_packets_dropped = max(0,\
                                        self.total_rx_packets_dropped - \
                                        rhs.total_rx_packets_dropped)
        self.delta_tx_packets_dropped = max(0,self.total_tx_packets_dropped - \
                                        rhs.total_tx_packets_dropped)
        self.delta_rx_errors = max(0, \
                               self.total_rx_errors - rhs.total_rx_errors)
        self.delta_tx_errors = max(0, \
                                  self.total_tx_errors - rhs.total_tx_errors)
        
        # Send an event to indicate that this switch is having problems
        # when delta_*_packets_dropped or delta_*_errors is > 0?
        # At this point we wouldn't be able to nail down any more
        # specific port info. We could probably let the port delta
        # computation do that. An event/alert at this point 
        # may be a high-level (or wasted)
        # alert if the port delta sends a more specific event as well.
        
        # Compute port deltas
        for key in self.port_info:
            self.port_info[key].compute_delta_from( rhs.port_info[key] )
    
    def store_port_info(self, ports, port_cap):
        """Save per-port counters
        @param ports - collection of port info structures
        @param port_cap - collection of port capacity structures
        """
        self.total_rx_bytes = 0
        self.total_tx_bytes = 0
        self.total_rx_packets = 0
        self.total_tx_packets = 0
        self.total_rx_packets_dropped = 0
        self.total_tx_packets_dropped = 0
        self.total_rx_errors = 0
        self.total_tx_errors = 0

        for item in ports:    
            # Compute all the counter totals
            self.total_rx_bytes += item['rx_bytes']
            self.total_tx_bytes += item['tx_bytes']
            self.total_rx_packets += item['rx_packets']
            self.total_tx_packets += item['tx_packets']
            self.total_rx_packets_dropped += item['rx_dropped']
            self.total_tx_packets_dropped += item['tx_dropped']
            self.total_rx_errors += item['rx_errors']
            self.total_tx_errors += item['tx_errors']
            # Store each item in the ports collection in a port dict
            new_port_info = PortInfo(port_cap[item['port_no']], self.monitor)
            #new_port_info = PortInfo(port_cap)
            new_port_info.owner_snapshot = self
            new_port_info.port_number = item['port_no']
            new_port_info.total_rx_bytes = item['rx_bytes']
            new_port_info.total_tx_bytes = item['tx_bytes']
            new_port_info.total_rx_packets = item['rx_packets']
            new_port_info.total_tx_packets = item['tx_packets']
            new_port_info.total_rx_packets_dropped = item['rx_dropped']
            new_port_info.total_tx_packets_dropped = item['tx_dropped']
            new_port_info.total_rx_errors = item['rx_errors']
            new_port_info.total_tx_errors = item['tx_errors']
            self.port_info[new_port_info.port_number] = new_port_info

    def get_total_rx_bytes(self):
        """Return the total number of bytes received at this switch
           across all its ports."""
        # For each port in the port dict
        # sum the total rx bytes
        return self.total_rx_bytes

    def get_total_tx_bytes(self):
        """Return the total number of bytes transmitted by this switch
           across all its ports."""
        return self.total_tx_bytes

    def ready(self):
        """Indicate whether this snapshot has been filled in with data
        from table, aggregate and port stats replies. A snaphot is not
        ready until all three sets of counter data have been received."""
        # Check whether our delta counters have been filled in
        # If the collection epoch = 1 then we're ready
        if self.collection_epoch == 1:
            return True
        elif self.delta_rx_bytes == -1:
            return False
        elif self.delta_tx_bytes == -1:
            return False
        elif self.delta_rx_packets_dropped == -1:
            return False
        elif self.delta_tx_packets_dropped == -1:
            return False
        elif self.delta_rx_errors == -1:
            return False
        elif self.delta_tx_errors == -1:
            return False
        else: 
            return True
