'''LinkUtilizationReplyEvent
@author Rean Griffith (rean@eecs.berkeley.edu)
'''

from nox.coreapps.pyrt import *
from nox.lib.core import *

class LinkUtilizationReplyEvent():
    NAME = "linkutilizationreply"
    '''NOX event that describes a reply to a request for port utilizations.
    This will be a custom event of the monitoring component.
    '''
    def __init__(self, xid, port_utils):
        '''Init.
        @param xid the request that this reply responds to
        reply to an earlier request.
        '''
        self.xid = xid
        self.port_utils = port_utils
