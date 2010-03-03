#!/usr/bin/python
import os
import commands
import sys
import getopt
import xml.dom.minidom
## \ingroup utility
# @class nox_package_index
# Create index of packages that can be installed
# using nox-get.py by searching current directory
# and its subdirectories.
#
# Run nox-package-index --help to see help on usgae
#
# @author ykk
# @date March 2010
#

def getTag(tag,name):
    """Shorthand for get Tag by name
    """
    return tag.getElementsByTagName(name)

def usage():
    """Display usage
    """
    print "Usage "+sys.argv[0]+" <options>\n"+\
          "Find NOX packages and create index.\n"+\
          "Options:\n"+\
          "-h/--help\n\tPrint this usage guide\n"+\
          ""

#Parse options and arguments
try:
    opts, args = getopt.getopt(sys.argv[1:], "h",
                               ["help"])
except getopt.GetoptError:
    print "Option error!"
    usage()
    sys.exit(2)

#Parse options
for opt,arg in opts:
    if (opt in ("-h","--help")):
        usage()
        sys.exit(0)
    else:
        print "Unhandled option :"+opt
        sys.exit(2)


impl = xml.dom.minidom.getDOMImplementation()
newdoc = impl.createDocument(None, "nox_package_index", None)

for candidates in os.popen('find . -name "*-package.tgz" -print').readlines():
    packagename = candidates.strip()
    packagename = packagename[packagename.rindex("/")+1:\
                              packagename.rindex("-package.tgz")]
    packagexml = commands.getoutput("tar tf "+candidates.strip()+\
                                    "| grep package.xml$")
    if (packagexml.strip() == ""):
        print "Skipping "+candidates.strip()+" (no package.xml found)"
    else:    
        packagedesc = commands.getoutput("tar zxvfO "+candidates.strip()+" "+\
                                         packagexml)
        print "Reading package.xml in "+candidates.strip()
        desc = packagedesc[len(packagename+"/package.xml")+1:]
        dom = xml.dom.minidom.parseString(desc)
        dom.documentElement.removeChild(dom.getElementsByTagName("pre-patch")[0])
        dom.documentElement.removeChild(dom.getElementsByTagName("post-patch")[0])
        fileElement = newdoc.createElement("file")
        fileElement.appendChild(newdoc.createTextNode(candidates.strip()[2:]))
        dom.documentElement.appendChild(fileElement)
        md5Element = newdoc.createElement("md5sum")
        md5sum = commands.getoutput("md5sum "+candidates.strip()).split()[0]
        md5Element.appendChild(newdoc.createTextNode(md5sum))
        dom.documentElement.appendChild(md5Element)
        newdoc.documentElement.appendChild(dom.documentElement)
    
fileRef = open("nox-index.xml","w")
newdoc.writexml(fileRef)
fileRef.close()
print "Created index of NOX packages"

prevComponents = []
dom = xml.dom.minidom.parse("nox-index.xml")
for nodes in dom.getElementsByTagName("name"):
    com_name = nodes.firstChild.data.strip()
    if (com_name in prevComponents):
        print "Warning: "+com_name+" is defined more than once!"
    else:
        prevComponents.append(com_name)
