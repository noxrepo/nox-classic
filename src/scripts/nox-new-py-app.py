#!/usr/bin/python
import os
import os.path
import sys
import getopt
import commands
import simplejson
## \ingroup utility
# @class nox_new_py_app
# nox-new-c-app.py utility creates a new Python component in NOX.
# It is to be run in coreapps, netapps, webapps or one of their subdirectory. 
#
# Run nox-new-py-app.py --help for usage guide.
#
# @author ykk
# @date January 2011

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
appdirname=None
appcategory=noxdir[(noxdir.rfind("/")+1):]
newdir=False
if (not (appcategory in ("coreapps","netapps","webapps"))):
    appdirname = appcategory
    noxdir = noxdir[:-(len(appdirname)+1)]
    appcategory = noxdir[(noxdir.rfind("/")+1):]
    if (not (appcategory in ("coreapps","netapps","webapps"))):
        print "This script adds a new application in NOX and"
        print "has to be run in coreapps, netapps or webapps"
        print "or one of their subdirectories accordingly."
        print "You can currently in invalid directory "+currdir
        sys.exit(2)
    else:
        print "Creating new application"
else:
    newdir=True
    print "Create new application and directory"

#Check sed
sedcmd=commands.getoutput("which sed")
if (sedcmd == ""):
    print "sed not found."
    sys.exit(2)

#Check configure.ac.in
configfile=None
if (newdir):
    configfile="../../../configure.ac.in"
    check_file(configfile)

#Check sample file
samplefile="simple_app"
sampleappname="simple_py_app"
sampledir="../coreapps/simple_py_app/"
if (appdirname != None):
    sampledir="../"+sampledir
check_file(sampledir+samplefile+".py")
check_file(sampledir+"meta.json")
check_file(sampledir+"Makefile.am")

#Check application not existing
appname=appname.replace(" ","_")
if (newdir):
    appdirname=appname
    if (os.path.isdir(appdirname)):
        print appdirname+" already existing!"
        sys.exit(2)
else:
    if (os.path.isfile(appname+".py")):
        print appname+" already existing!"
        sys.exit(2)

#Create application
if (newdir):
    run("mkdir "+appdirname, dryrun, verbose)
    #meta.json
    fileRef = open(sampledir+"meta.json","r")
    metafile = ""
    for line in fileRef:
        metafile += line
    fileRef.close()
    metainfo = simplejson.loads(metafile)
    meta = metainfo["components"][0]
    meta["name"] = appname
    meta["python"] = "nox."+appcategory+"."+\
                     appdirname.replace("/",".")+\
                     "."+appname
    if (dryrun):
        print "Write to "+appdirname+"/meta.json"
        print simplejson.dumps(metainfo, indent=4)
    else:
        fileRef = open(appdirname+"/meta.json","w")
        fileRef.write(simplejson.dumps(metainfo, indent=4))
        fileRef.close()
    #Makefile.am
    run("sed -e 's:"+samplefile+":"+appdirname+":g'"+\
        " -e 's:coreapps:"+appcategory+":g'"+\
        " < "+sampledir+"Makefile.am"+\
        " > "+appdirname+"/Makefile.am",
        dryrun, verbose)
    run("sed -e 's:#add "+appcategory+" component here:"+\
        appdirname+" #add "+appcategory+" component here:g'"+\
        " < "+configfile+\
        " > "+configfile+".tmp",
        dryrun, verbose)
    run("mv "+configfile+".tmp "+configfile,
        dryrun, verbose)
    #Python file
    run("sed -e 's:"+samplefile+":"+appname+":g'"+\
        " -e 's:coreapps:"+appcategory+":g'"+\
        " -e 's:"+sampleappname+":"+appdirname+":g'"+\
        " < "+sampledir+samplefile+".py"+\
        " > "+appdirname+"/"+appname+".py",
        dryrun, verbose)
    #Init.py
    run("touch "+appdirname+"/__init__.py",dryrun,verbose)
else:
    #meta.json
    fileRef = open("meta.json","r")
    metafile = ""
    for line in fileRef:
        metafile += line
    fileRef.close()
    metainfo = simplejson.loads(metafile)
    appinfo = {}
    appinfo["name"] = appname.replace("_"," ")
    appinfo["dependencies"] = ["python"]
    appinfo["python"] = "nox."+appcategory+"."+\
                        appdirname.replace("/",".")+\
                        "."+appname
    metainfo["components"].append(appinfo)
    if (dryrun):
        print "Writing to meta.json"
        print simplejson.dumps(metainfo, indent=4)
    else:
        fileRef = open("meta.json","w")
        fileRef.write(simplejson.dumps(metainfo, indent=4))
        fileRef.close()
    #Makefile.am
    run("sed -e 's:EXTRA_DIST =:EXTRA_DIST = \\\\\\n\t"+\
        appname+".py:g'"+\
        " -e 's:NOX_RUNTIMEFILES =:NOX_RUNTIMEFILES = \\\\\\n\t"+\
         appname+".py :g'"+\
        " < Makefile.am"+\
        " > Makefile.am.tmp",
        dryrun, verbose)
    run("mv Makefile.am.tmp Makefile.am",dryrun, verbose)
    #Python file
    run("sed -e 's:"+samplefile+":"+appname+":g'"+\
        " -e 's:coreapps:"+appcategory+":g'"+\
        " -e 's:"+sampleappname+":"+appdirname+":g'"+\
        " < "+sampledir+samplefile+".py"+\
        " > "+appname+".py",
        dryrun, verbose)
    #Init.py
    run("touch __init__.py",dryrun,verbose)

if (newdir):
    print "Please rerun ./boot.sh and ./configure"
