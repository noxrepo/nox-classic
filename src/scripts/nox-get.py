#!/usr/bin/python
import os
import commands
import sys
import getopt
import xml.dom.minidom
import urllib
import subprocess
## \ingroup utility
# @class nox_get
# Retrieve and install packages in NOX.
# This is not meant to be scalable.
# Most code that make senses should be incorporated
# into the main branch of NOX instead of using this
# packaging system.  Instead, this tool is for
# short code that are project centric and should not
# be incorporated into the main branch.
# Experimental code that is not proven might be another
# candidate for use with this tool, once NOX is progress
# to a fairly mature state.
#
# Run nox-get.py --help to see help on usage
#
# @author ykk
# @date March 2010
#

class package:
    """Class to hold package information
    """
    def __init__(self, source, domNode):
        """Initialize package
        """
        self.source = source
        self.name = domNode.getElementsByTagName("name")[0].firstChild.data.strip()
        self.description = domNode.getElementsByTagName("description")[0].firstChild.data
        self.md5sum = domNode.getElementsByTagName("md5sum")[0].firstChild.data.strip()
        self.file = source.url[:-len("nox-index.xml")]+\
                    domNode.getElementsByTagName("file")[0].firstChild.data.strip()
        self.localfile = self.file[self.file.rindex("/")+1:]
        self.dependency = []
        for d in domNode.getElementsByTagName("dependency"):
            self.dependency.append(d.firstChild.data.strip())

    def __str__(self):
        """String representation
        """
        return self.name+"\n"+\
               self.description+"\n"+\
               "Depends on "+str(self.dependency)+"\n"+\
               "Source from "+str(self.file)+"\n"

    def shortdesc(self):
        """Short description
        """
        for l in self.description.strip().split("\n"):
            return self.name+"\t"+l.strip()

class source:
    """Class to hold source information
    """
    def __init__(self, url):
        """Initialize source with url of its nox-index.xml
        """
        self.url = url
        self.packages = []
        try:
            self.__dom = xml.dom.minidom.parseString(readUrl(url))
            self.__get_packages()
        except IOError:
            self.url = None
        
    def __get_packages(self):
        """Parse packages from source's description
        """
        for p in self.__dom.getElementsByTagName("nox_package"):
            self.packages.append(package(self, p))

def readUrl(url):
    content = ""
    fileRef = urllib.urlopen(url)
    for line in fileRef:
        content += line
    fileRef.close()
    return content

def getTag(tag,name):
    """Shorthand for get Tag by name
    """
    return tag.getElementsByTagName(name)

def getName(tag):
    """Shorthand for get name tag
    """
    return getTag(tag, "name")[0].firstChild.data

def parse_meta_xml(filename,components):
    """Parse meta.xml file
    """
    dom = xml.dom.minidom.parse(filename)
    comps = dom.getElementsByTagName("component")
    for comp in comps:
        components.append(getName(comp))

def get_install_sources(name, sources):
    """Get install package among sources
    """
    packagesrc=[]
    for s in sources:
        for p in s.packages:
            if (p.name == name):
                packagesrc.append(p)
    return packagesrc

def get_source_n_dependencies(checkinstalled, installsource, scheduledsources,
                              sources, installed, toinstall):
    """Get list of installation sources including dependencies
    """
    if (checkinstalled):
        if (toinstall in installed):
            return
    if (toinstall in scheduledsources):
        return
    #Find source
    src = get_install_sources(toinstall, sources)
    chosensrc = None
    if (len(src) == 0):
        print "Cannot find any source for package "+toinstall
        sys.exit(1)
    elif (len(src) > 1):
        choice = -1
        while (choice < 0 or choice >= len(src)):
            print "More than one source for package "+toinstall
            for s in src:
                print str(src.index(s))+") "+s.source.url
            try:
                choice = int(raw_input("Choose source (enter number) > "))
            except ValueError:
                choice = -1
        chosensrc = src[choice]
    else:
        chosensrc = src[0]
    #Schedule dependencies
    for d in chosensrc.dependency:
        get_source_n_dependencies(True, installsource, scheduledsources,
                                  sources, installed, d)
    #Schedule current
    installsource.append(chosensrc)
    scheduledsources.append(toinstall)

def usage():
    """Display usage
    """
    print "Usage "+sys.argv[0]+" <options> component/package_name\n"+\
          "Find NOX packages and install (with dependencies).\n"+\
          "Options:\n"+\
          "-h/--help\n\tPrint this usage guide\n"+\
          "-s/--skip-check-installed\n\tSkip check if component is installed\n"+\
          ""

#Parse options and arguments
checkinstalled=True
sourcedoc="etc/noxget/sources.xml"
try:
    opts, args = getopt.getopt(sys.argv[1:], "hs",
                               ["help","skip-check-installed"])
except getopt.GetoptError:
    print "Option error!"
    usage()
    sys.exit(2)

#Parse options
for opt,arg in opts:
    if (opt in ("-h","--help")):
        usage()
        sys.exit(0)
    elif (opt in ("-s","--skip-check-installed")):
        checkinstalled = False
    else:
        print "Unhandled option :"+opt
        sys.exit(2)
        
#Check for action
if (len(args) < 0):
    print "Action is needed!"
    usage()
    sys.exit(2)
action = args[0]
if not (action in ("install", "list")):
    print "Unknown action "+action
    sys.exit(1)

#Check directory
if not (os.path.isdir("nox/coreapps") and
        os.path.isdir("nox/netapps") and
        os.path.isdir("nox/webapps")):
    print "Not in nox's src directory!"
    sys.exit(2)

#Get all components installed
cmd='find . -name "meta.xml" -print'
installed=[]
for metafile in os.popen(cmd).readlines():
    parse_meta_xml(metafile.strip(),installed)

#Get all sources
sources=[]
dom = xml.dom.minidom.parse(sourcedoc)
print "Retrieving sources..."
for repo in dom.getElementsByTagName("source"):
    src = source(repo.firstChild.data)
    if (src.url != None):
        sources.append(src)

#List if action is list
if (action == "list"):
    for s in sources:
        print s.url
        for p in s.packages:
            print "\t"+p.shortdesc()
    sys.exit(0)

#Check for package if install action
if (len(args) != 2):
    print "Install action needs exactly one component/package"
    sys.exit(1)
package=args[1]

#Check if component is installed
if (checkinstalled):
    if (package in installed):
        print "Skipping "+package+" which is already installed!"
        sys.exit(1)

#Get package source for packages to install
installsource=[]
scheduledsources=[]
get_source_n_dependencies(checkinstalled, installsource, scheduledsources,
                          sources, installed, package)

#Retrieve sources
os.chdir("../component-cache")
for isrc in installsource:
    if (isrc.file == "../component-cache/"+isrc.localfile):
        print "Skipping local file "+isrc.localfile
    else:
        print "Retrieving "+isrc.file+" to "+isrc.localfile
        fileRef = open(isrc.localfile, "w")
        remoteRef = urllib.urlopen(isrc.file)
        fileRef.write(remoteRef.read())
        fileRef.close()
        remoteRef.close()

    #Check md5
    md5sum = commands.getoutput("md5sum "+isrc.localfile).split()[0]
    if (md5sum != isrc.md5sum):
        print "md5sum of "+isrc.localfile+" failed!"
        sys.exit(1)
    
#Extract and apply patches
for isrc in installsource:
    print "Extracting "+isrc.localfile
    taroutput=commands.getoutput("tar zxvf "+isrc.localfile)
    #Get package.xml
    fname=None
    for filename in taroutput.split("\n"):
        if (filename.endswith("package.xml")):
            fname = filename
            break
    if (fname == None):
        print "Failed to find package.xml in "+isrc.localfile
        sys.exit(1)
    dom = xml.dom.minidom.parse(fname)
    precmd = dom.getElementsByTagName("pre-patch")[0].firstChild.data.strip()
    postcmd = dom.getElementsByTagName("post-patch")[0].firstChild.data.strip()
    #Pre-patch
    if (len(precmd) > 0):
        print "Executing pre-patch script..."
        for cmd in precmd.split("\n"):
            print "\t"+cmd
            if (cmd.strip()[0] != '#'):
                print commands.getoutput(cmd)
    #Apply patches
    patches = commands.getoutput("tar tf "+isrc.localfile+\
                                 "| grep .patch$").split("\n")
    patches.sort()
    patches.reverse()
    for p in patches:
        print "Apply patch "+p
        subprocess.Popen("git am "+p,shell=True)
    #Post-patch
    if (len(postcmd) > 0):
        print "Executing post-patch script..."
        for cmd in postcmd.split("\n"):
            print "\t"+cmd
            if (cmd.strip()[0] != '#'):
                print commands.getoutput(cmd)
