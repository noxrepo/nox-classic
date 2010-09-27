'''SilentSwitchEvent
@author Rean Griffith (rean@eecs.berkeley.edu)
'''

from nox.coreapps.pyrt import *
from nox.lib.core import *

class SilentSwitchEvent():
    NAME = "silentswitch"
    '''NOX event that flags a switch as silent, which means that the
    monitoring component hasn't heard from it in a while.
    This will be a custom event of the monitoring component.
    '''
    def __init__(self, xid, dpid):
        '''Init.
        @param xid the request that this reply responds to
        reply to an earlier request.
        '''
        self.xid = xid
        self.dpid = dpid
        self.is_silent = True
        self.last_contact = 0
