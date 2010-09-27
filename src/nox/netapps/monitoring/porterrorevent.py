'''PortErrorEvent
@author Rean Griffith (rean@eecs.berkeley.edu)
'''

from nox.coreapps.pyrt import *
from nox.lib.core import *

class PortErrorEvent():
    NAME = "porterror"
    '''NOX event that describes a port error, e.g., bytes/packets dropped,
    on tx/rx, etc. This will be a custom event of the monitoring component.
    '''
    def __init__(self, xid, dpid, port_num):
        '''Init.
        @param xid the request that this reply responds to
        reply to an earlier request.
        '''
        self.xid = xid
        self.dpid = dpid
        self.port_num = port_num
        self.rx_dropped = 0
        self.tx_dropped = 0
        self.rx_errors = 0
        self.tx_errors = 0
        self.rx_frame_err = 0
        self.rx_over_err = 0
        self.rx_crc_err = 0
        self.collisions = 0
        
