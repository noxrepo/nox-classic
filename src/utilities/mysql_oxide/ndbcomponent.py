
from nox.lib.core     import Component

class NDBComponent(Component):
    """Abstract class for components that log network data to NDB"""

    def __init__(self, ctxt, name):
        Component.__init__(self, ctxt, name)

    def configure(self,configuration):
      pass

    def install(self):
      pass

    def getInterface(self):
        return str(NDBComponent) 
  

    def update_entry(self, dict): 
      print "update: " + str(dict)
      pass 

    def dump_cache(self): 
      print "can't dump fake ndbcomponent"

    def packet_in_callback(self, dpid, inport, reason, len, bufid, packet) : 
        raise Exception, "NDBComponent class must implement packet_in_callback" 

    def init_table_info(self):
        raise Exception, "NDBComponent class must implement init_table_info" 

    def dict_to_key(self, dict):
        raise Exception, "NDBComponent class must implement dict_to_key" 

    def key_to_dict(self, key):
        raise Exception, "NDBComponent class must implement key_to_dict" 

