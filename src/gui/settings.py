'''
This class stores global settings for the GUI
@author Kyriakos Zarifis
'''

class Settings():
    def __init__(self, parent):
        self.node_id_size = 2
        
    def set_node_id_size_small(self):
        self.node_id_size = 1
    def set_node_id_size_normal(self):
        self.node_id_size = 2
    def set_node_id_size_large(self):
        self.node_id_size = 3
        
