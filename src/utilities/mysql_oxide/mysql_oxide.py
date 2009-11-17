import sys

# modify path so that components will see fake component class
# in nox.lib 
# nox.lib.packet and nox.apps are symlinks to the real python files
sys.path.insert(0, sys.path[0] + "/mysql_oxide") 

from nox.lib.packet.packet_utils import *
from socket import ntohl, ntohs , htonl, htons
from nox.lib.packet.ipv4 import ipv4
from nox.lib.packet.tcp import tcp
from nox.lib.packet.ethernet import ethernet
import MySQLdb


if len(sys.argv) != 3:
  print "usage: [module for app] [app class-name]"
  sys.exit(1) 

module_name = sys.argv[1]
class_name = sys.argv[2] 

# clunky way of instantiating an object based only on a name from
# the command-line

exec("from " + module_name + " import " + class_name) 

exec("obj = " + class_name + "(None,None)") 

conn = MySQLdb.connect ('localhost','nox_dwh','nox_dwh', 'nox_dwh')
cursor = conn.cursor() 

cursor.execute ("SELECT ID, CREATED_DT, DP_ID, PORT_ID, REASON, BUFFER, TOTAL_LEN FROM FLOW_SETUP ORDER BY ID")
#cursor.execute ("SELECT ID, CREATED_DT, DP_ID, PORT_ID, REASON, BUFFER, TOTAL_LEN FROM FLOW_SETUP ORDER BY ID LIMIT 10000")
rows = cursor.fetchall ()
for row in rows:

  id = row[0] 
  created_dt = row[1]
  dp_id = row[2] 
  port_id = row[3]
  reason = row[4]
  buffer = row[5]
  total_len = row[6] 
  packet = ethernet(array.array('B', buffer))

  obj.packet_in_callback(dp_id, port_id, reason, total_len, id, packet, created_dt)

print "Number of rows returned: %d" % cursor.rowcount

cursor.close()
conn.close()



obj.timer_callback(0) 

