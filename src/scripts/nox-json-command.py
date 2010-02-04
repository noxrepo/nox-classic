#!/usr/bin/python
import os
import sys
import getopt
import socket

## \ingroup utility
# @class nox_json_command
# Sends a JSON to NOX.
# Uses \ref jsonmessenger to proxy commands.
# Individual components will execute the commands accordingly.
#
# This can only be run in the source directory of NOX
# unless that directory is added to the PYTHONPATH
# environment variable.
#
# Run nox-json-command.py --help for help on usage
# 
# @author ykk
# @data February, 2010
#

##Print usage guide
def usage():
    """Display usage
    """
    print "Usage "+sys.argv[0]+" <options> string_command"
    print "\tTo send JSON command to NOX"
    print  "Options:"
    print "-h/--help\n\tPrint this usage guide"
    print "-n/--noxhost\n\tSpecify where NOX is hosted (default:localhost)"
    print "-p/--port\n\tSpecify port number for messenger (default:2703)"
    print "-r/--reply\n\tSpecify if reply is expected (default:False)"
    print "-v/--verbose\n\tVerbose output"

#Parse options and arguments
try:
    opts, args = getopt.getopt(sys.argv[1:], "hvn:p:r",
                               ["help","verbose","noxhost=","port=",
                                "reply"])
except getopt.GetoptError:
    print "Option error!"
    usage()
    sys.exit(2)

if not (len(args) >= 1):
    print "Missing command!"
    usage()
    sys.exit(2)
else:
    str_cmd = " ".join(args)

#Parse options
##Verbose debug output or not
debug = False
##NOX host
nox_host = "localhost"
##Port number
port_no = 2703
##Wait for reply
expectReply = False
for opt,arg in opts:
    if (opt in ("-h","--help")):
        usage()
        sys.exit(0)
    elif (opt in ("-v","--verbose")):
        debug=True
    elif (opt in ("-n","--noxhost")):
        nox_host=arg
    elif (opt in ("-r","--reply")):
        expectReply = True
    elif (opt in ("-p","--port")):
        port_no=int(arg)
    else:
        print "Unhandled option :"+opt
        sys.exit(2)

#Send command
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((nox_host,port_no))
sock.send(str_cmd)
if (expectReply):
    print sock.recv(4096)
sock.send("{\"type\":\"disconnect\"}")
sock.shutdown(1)
sock.close()
