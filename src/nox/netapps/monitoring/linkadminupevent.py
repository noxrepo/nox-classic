'''LinkAdminUpEvent
@author Rean Griffith (rean@eecs.berkeley.edu)
'''

from nox.coreapps.pyrt import *
from nox.lib.core import *

class LinkAdminUpEvent():
    NAME = "linkadminup"
    '''NOX event that indicates that a link has been administratively
    enabled. This event provides details on "what" was enabled and what
    it connects in the network.
    This will be a custom event of topology. This is an event that 
    the DispatchServer can subscribe to and then send a message to an
    external client, e.g., the gui.
    '''
    def __init__(self, xid, dpid1, port1, dpid2, port2):
        '''Init.
        @param xid the request that this reply responds to
        reply to an earlier request.
        '''
        self.xid = xid
        self.dpid1 = dpid1
        self.port1 = port1
        self.dpid2 = dpid2
        self.port2 = port2
        
