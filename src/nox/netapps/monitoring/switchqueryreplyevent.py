'''SwitchQueryReplyEvent
@author Rean Griffith (rean@eecs.berkeley.edu)
'''

from nox.coreapps.pyrt import *
from nox.lib.core import *

class SwitchQueryReplyEvent():
    NAME = "switchqueryreply"
    QUERY_TABLE_STATS = "tablestats"
    QUERY_PORT_STATS = "portstats"
    QUERY_AGG_STATS = "aggstats"
    QUERY_LATEST_SNAPSHOT = "latestsnapshot"
    QUERY_FLOW_STATS = "flowstats"
    QUERY_QUEUE_STATS = "queuestats"
    '''NOX event that describes a reply to a request (query) for some 
    switch data,
    e.g., its flow table, port stats, latest snapshot, aggregate stats.
    This will be a custom event of the monitoring component.
    '''
    def __init__(self, xid, dpid, query_type, reply):
        '''Init.
        @param xid the request that this reply responds to
        reply to an earlier request.
        '''
        self.xid = xid
        self.dpid = dpid
        self.query_type = query_type
        self.reply = reply

class SwitchQuery:
    """Class represents a switch query. Simple container."""
    def __init__(self, xid, dpid, query_type):
        self.xid = xid
        self.dpid = dpid
        self.query_type = query_type
