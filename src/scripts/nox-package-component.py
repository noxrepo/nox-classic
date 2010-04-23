#!/usr/bin/python
import os
import commands
import sys
import getopt
import xml.dom.minidom
import subprocess
## \ingroup utility
# @class nox_package_component
# Find commits related to component and
# package using git-dependency.
#
# Run nox-package-components.py --help to see help on usage
#
# Dependencies: python-xml in Debian
#               git-dependency
#
# @author ykk
# @date March 2010
#

# TODO: switch to meta.json

class component:
    """Component in NOX.
    """
    def __init__(self, name):
        """Initialize with name.
        """
        self.name = name
        self.dependencies = []
        self.library = None
        self.files = []

def getTag(tag,name):
    """Shorthand for get Tag by name
    """
    return tag.getElementsByTagName(name)

def getName(tag):
    """Shorthand for get name tag
    """
    return getTag(tag, "name")[0].firstChild.data

def parse_makefile(filename,component):
    """Parse Makefile.am for sources
    """
    nsourceline = 0
    sourceline = "\\"
    while (sourceline[-1] == "\\"):
        sourceline = commands.getoutput("grep -A"+str(nsourceline)+" ^"+\
                                        component.library+"_la_SOURCES "+
                                        filename[:-len("meta.xml")]+"Makefile.am").strip()            
        if (len(sourceline) == 0):
            break
        nsourceline += 1
    if (len(sourceline) != 0):
        sourceline = sourceline.replace("\n","").replace("\\"," ")
        sourceline = sourceline[sourceline.index("=")+1:].strip()
        for source in sourceline.split():
            component.files.append("src"+filename[1:-len("meta.xml")]+source)

def parse_meta_xml(filename,components):
    """Parse meta.xml file
    """
    dom = xml.dom.minidom.parse(filename)
    comps = dom.getElementsByTagName("component")
    for comp in comps:
        com = component(getName(comp))
        for dep in getTag(comp, "dependency"):
            com.dependencies.append(getName(dep))
        for pylib in getTag(comp, "python"):
            com.library = pylib.firstChild.data
            com.files.append("src/"+com.library.replace(".","/")+".py")
        for lib in getTag(comp, "library"):
            com.library = lib.firstChild.data
            parse_makefile(filename,com)
        components.append(com)

def usage():
    """Display usage
    """
    print "Usage "+sys.argv[0]+" <options> component\n"+\
          "Component and related commits are packaged into tarball.\n"+\
          "Options:\n"+\
          "-i/--ignore\n\tIgnore file in dependency search(can be used multiple times)\n"+\
          "-h/--help\n\tPrint this usage guide\n"+\
          "-c/--commit\n\tCommit to add to package\n"+\
          "-n/--name\n\tName of package (defaults to that of component)\n"+\
          "-s/--since\n\tSpecify commit since\n"+\
          "-f/--force\n\tForce package creation (delete directory if available)\n"+\
          "-d/--dir <root directory>\n\tSpecify root directory to find meta.xml in (default=PWD)\n"+\
          "-e/--edit\n\tSpecify to edit package.xml (default: True for no description provided, else false)\n"+\
          "--description <text file with description>\n\tProvide description of package\n"+\
          "--pre <pre-patch shell script>\n\tProvide shell script before patching\n"+\
          "--post <post-patch shell script>\n\tProvide shell script after patching\n"+\
          ""

#Parse options and arguments
try:
    opts, args = getopt.getopt(sys.argv[1:], "hd:fec:n:i:s:",
                               ["help","directory=","force","edit",
                                "description=","pre=","post=",
                                "name=","commit=","ignore=","since="])
except getopt.GetoptError:
    print "Option error!"
    usage()
    sys.exit(2)

#Parse options
dir="."
force=False
forceedit=False
descfile=None
prescript=None
postscript=None
commits=[]
name = None
excludeopt=""
since=None
for opt,arg in opts:
    if (opt in ("-h","--help")):
        usage()
        sys.exit(0)
    elif (opt in ("-c","--commit")):
        commits.append(arg)
    elif (opt in ("-i","--ignore")):
        excludeopt += " -e "+arg
    elif (opt in ("-s","--since")):
        since=arg
    elif (opt in ("-n","--name")):
        name=arg
    elif (opt in ("-d","--dir")):
        dir=arg
    elif (opt in ("-f","--force")):
        force=True
    elif (opt in ("-e","--edit")):
        forceedit=True
    elif (opt in ("--description")):
        if (not os.path.isfile(arg)):
            print "Missing description file"
            sys.exit(1)
        descfile = arg
    elif (opt in ("--pre")):
        if (not os.path.isfile(arg)):
            print "Missing pre-patch shell script"
            sys.exit(1)
        prescript = arg
    elif (opt in ("--post")):
        if (not os.path.isfile(arg)):
            print "Missing post-patch shell script"
            sys.exit(1)
        postscript = arg
    else:
        print "Unhandled option :"+opt
        sys.exit(2)

#Check components
if (len(args) == 0):
    if (len(commits) == 0):
        print "Must have exactly one component (or commit) listed!"
        usage()
        sys.exit(2)
    if (name == None):
        print "Must specify name if not component is specificed!"
        usage()
        sys.exit(2)
elif (len(args) > 1):
    print "Must have exactly one component listed!"
    usage()
    sys.exit(2)

#Check directory
if not (os.path.isdir("nox/coreapps") and
        os.path.isdir("nox/netapps") and
        os.path.isdir("nox/webapps")):
    print "Not in nox's src directory!"
    sys.exit(2)

#Find all components and files
cmd='find '+dir+' -name "meta.xml" -print'
keycomponent=None
for metafile in os.popen(cmd).readlines():
    components=[]
    parse_meta_xml(metafile.strip(),components)
    for c in components:
        if (c.name in args):
            keycomponent = c
            if (name == None):
                name = keycomponent.name
if ((keycomponent == None) and (len(args) == 1)):
    print "Component "+args[0]+" not found"
    sys.exit(1)

#Package components
os.chdir("../")
if not os.path.isdir("component-cache"):
    os.makedirs("component-cache")
os.chdir("component-cache")
if not os.path.isdir(name):
    os.makedirs(name)
elif (force):
    for root, dirs, files in os.walk(name, topdown=False):
        for fname in files:
            os.remove(os.path.join(root, fname))
else:
    print "Component package already exist!?"
    sys.exit(1)
os.chdir(name)
gdpdopt = " -e src/etc/nox.xml"+\
          " -e configure.ac.in"+\
          excludeopt
if (since != None):
    gdpdopt += " -s "+since
if (keycomponent != None):
    print commands.getoutput("git-dependency -p"+\
                             gdpdopt+\
                             " -f "+" -f ".join(keycomponent.files)+\
                             " "+" ".join(commits))
else:
    print commands.getoutput("git-dependency -p"+\
                             gdpdopt+\
                             " "+" ".join(commits))

#Create XML file
impl = xml.dom.minidom.getDOMImplementation()
newdoc = impl.createDocument(None, "nox_package", None)

name_element = newdoc.createElement("name")
name_element.appendChild(newdoc.createTextNode(name))
newdoc.documentElement.appendChild(name_element)

desc_element = newdoc.createElement("description")
if (descfile == None):
    desc_element.appendChild(newdoc.createTextNode("Some description here"))
else:
    fileRef = open("../../src/"+descfile, "r")
    for line in fileRef:
        desc_element.appendChild(newdoc.createTextNode(line.strip()))
    fileRef.close()
newdoc.documentElement.appendChild(desc_element)

if (keycomponent != None):
    for d in keycomponent.dependencies:
        depend_element = newdoc.createElement("dependency")
        depend_element.appendChild(newdoc.createTextNode(d))
        newdoc.documentElement.appendChild(depend_element)

pre_element = newdoc.createElement("pre-patch")
if (prescript == None):
    if (forceedit or (descfile==None)):
        pre_element.appendChild(newdoc.createTextNode("#Pre-patch shell script here"))
else:
    fileRef = open("../../src/"+prescript, "r")
    for line in fileRef:
        pre_element.appendChild(newdoc.createTextNode(line.rstrip()))
    fileRef.close()
newdoc.documentElement.appendChild(pre_element)

post_element = newdoc.createElement("post-patch")
if (postscript == None):
    if (forceedit or (descfile==None)):
        post_element.appendChild(newdoc.createTextNode("#Post-patch shell script here"))
else:
    fileRef = open("../../src/"+postscript, "r")
    for line in fileRef:
        post_element.appendChild(newdoc.createTextNode(line.rstrip()))
    fileRef.close()
newdoc.documentElement.appendChild(post_element)

fileRef = open("package.xml","w")
newdoc.writexml(fileRef,addindent="   ",newl="\n")
fileRef.close()

if (forceedit or (descfile==None)):
    p = subprocess.Popen("/usr/bin/editor package.xml",
                         stdin=sys.stdin, stdout=sys.stdout, shell=True)
    subprocess.Popen.wait(p)

os.chdir("..")
print "Adding to tarball..."
print commands.getoutput("tar czvf "+name+\
                         "-package.tgz "+name)
print "Packaged "+name
