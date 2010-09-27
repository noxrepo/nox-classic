'''NodeEnterEvent
@author Rean Griffith (rean@eecs.berkeley.edu)
'''

from nox.coreapps.pyrt import *
from nox.lib.core import *

class NodeEnterEvent():
    NAME = "nodeenter"
    '''NOX event that indicates that a switch has joined the network.
    This event provides details on "who" joined and where they are in the 
    network, e.g., the layer.
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
        
