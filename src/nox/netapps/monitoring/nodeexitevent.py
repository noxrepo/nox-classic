'''NodeExitEvent
@author Rean Griffith (rean@eecs.berkeley.edu)
'''

from nox.coreapps.pyrt import *
from nox.lib.core import *

class NodeExitEvent():
    NAME = "nodeexit"
    '''NOX event that indicates that a switch has left the network.
    This event provides details on "who" left and (possibly) where 
    they were in the network, e.g., the layer.
    This will be a custom event of topology. This is an event that 
    the DispatchServer can subscribe to and then send a message to an
    external client, e.g., the gui.
    '''
    def __init__(self, xid, dpid, layer):
        '''Init.
        @param xid the request that this reply responds to
        reply to an earlier request.
        '''
        self.xid = xid
        self.dpid = dpid
        self.layer = layer
        
