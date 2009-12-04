#!/usr/bin/python
import os
import os.path
import sys
import getopt
import commands
## \ingroup utility
# @class nox_new_c_app
# nox-new-c-app.py utility creates a new C/C++ component in NOX.
# It is to be run in coreapps, netapps, or webapps.
# Additional description is found in \ref new-c-component.
#
# Run nox-new-c-app.py --help for usage guide.
#
# @author ykk
# @date December 2009

##Run command
def run(cmd, dryrun=False, verbose=False):
    if (verbose):
        print cmd
    if (not dryrun):
        print commands.getoutput(cmd)

##Check file exists
def check_file(filename):
    if (not os.path.isfile(filename)):
        print filename+" not found!"
        sys.exit(2)

##Print usage guide
def usage():
    """Display usage
    """
    print "Usage "+sys.argv[0]+" <options> application_name"
    print "\tTo be run in coreapps, netapps or webapps of NOX source"
    print  "Options:"
    print "-h/--help\n\tPrint this usage guide"
    print "-d/--dry-run\n\tDry run"
    print "-v/--verbose\n\tVerbose"

#Parse options and arguments
##Dry-run or not
dryrun=False
##Verbose or not
verbose=False
try:
    opts, args = getopt.getopt(sys.argv[1:], "hdv",
                               ["help","dry-run","verbose"])
except getopt.GetoptError:
    print "Option error!"
    usage()
    sys.exit(2)

#Check there is only 1 application name
if not (len(args) == 1):
    print "Missing application name!"
    usage()
    sys.exit(2)
else:
    appname = args[0]

#Parse options
for opt,arg in opts:
    if (opt in ("-h","--help")):
        usage()
        sys.exit(0)
    elif (opt in ("-v","--verbose")):
        verbose=True
    elif (opt in ("-d","--dry-run")):
        dryrun=True
    else:
        print "Unhandled option :"+opt
        sys.exit(2)

#Check current directory
currdir=os.getcwd()
noxdir=currdir[currdir.find("src/nox/"):]
apppath=noxdir[(noxdir.rfind("/")+1):]
if (not (apppath in ("coreapps","netapps","webapps"))):
    print "This script adds a new application in NOX and"
    print "has to be run in coreapps, netapps or webapps accordingly."
    print "You can currently in invalid directory "+currdir
    sys.exit(2)

#Check sed
sedcmd=commands.getoutput("which sed")
if (sedcmd == ""):
    print "sed not found."
    sys.exit(2)

#Check configure.ac.in
configfile="../../../configure.ac.in"
check_file(configfile)

#Check sample file
samplefile="simple_cc_app"
sampledir="../coreapps/simple_c_app/"
check_file(sampledir+samplefile+".hh")
check_file(sampledir+samplefile+".cc")
check_file(sampledir+"meta.xml")
check_file(sampledir+"Makefile.am")

#Check application not existing
appdir=appname.replace(" ","_")
if (os.path.isdir(appdir)):
    print appdir+" already existing!"
    sys.exit(2)

#Create application
run("mkdir "+appdir, dryrun, verbose)
run("sed -e 's:"+samplefile+":"+appdir+":g'"+\
    " < "+sampledir+samplefile+".hh"+\
    " > "+appdir+"/"+appdir+".hh",
    dryrun, verbose)
run("sed -e 's:"+samplefile+":"+appdir+":g'"+\
    " < "+sampledir+samplefile+".cc"+\
    " > "+appdir+"/"+appdir+".cc",
    dryrun, verbose)
run("sed -e 's:"+samplefile+":"+appdir+":g'"+\
    " -e 's:"+samplefile.replace("_"," ")+":"+appname+":g'"+\
    " < "+sampledir+"meta.xml"+\
    " > "+appdir+"/meta.xml",
    dryrun, verbose)
run("sed -e 's:"+samplefile+":"+appdir+":g'"+\
    " -e 's:coreapps:"+apppath+":g'"+\
    " < "+sampledir+"Makefile.am"+\
    " > "+appdir+"/Makefile.am",
    dryrun, verbose)
run("sed -e 's:#add "+apppath+" component here:"+\
    appdir+" #add "+apppath+" component here:g'"+\
    " < "+configfile+\
    " > "+configfile+".tmp",
    dryrun, verbose)
run("mv "+configfile+".tmp "+configfile,
    dryrun, verbose)
print "Please rerun ./boot.sh and ./configure"

