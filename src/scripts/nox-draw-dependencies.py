#!/usr/bin/python
import os
import commands
import sys
import getopt
import xml.dom.minidom
## \ingroup utility
# @class nox_draw_dependencies
# Build dependency graph from meta.xml
# Color called and its dependencies
#
# Run nox-draw-dependencies.py --help to see help on usage
#
# Dependency: python-xml in Debian 
#
# @author ykk
# @date April 2009
#

class component:
    """Component in NOX.
    """
    def __init__(self, name):
        """Initialize with name.
        """
        self.name = name
        self.dependencies = []
        self.called = 0

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
        com = component(getName(comp))
        for dep in getTag(comp, "dependency"):
            com.dependencies.append(getName(dep))
        components.append(com)
        
def draw_components(filename, components):
    """Output graphviz file for dependency graph
    """
    fileRef = open(filename,"w")
    fileRef.write("digraph dependencies {\n")
    for comp in components:
        #Color called components
        if (comp.called == 1):
            fileRef.write("\""+comp.name+"\" [shape=diamond, style=filled, fillcolor=red];\n")
        elif (comp.called == 2):
            fileRef.write("\""+comp.name+"\" [shape=diamond, style=filled, fillcolor=orange];\n")
        #Draw edges
        for dep in comp.dependencies:
            fileRef.write("\""+comp.name+"\" -> \""+\
                          dep+"\";\n")
    fileRef.write("}\n")
    fileRef.close()

def highlight_called(components, called, secondary=False):
    """Highlight/mark called components.
    """
    for comp in components:
        if (comp.name in called):
            if (secondary):
                comp.called=2
            else:
                comp.called=1
            highlight_called(components, comp.dependencies, True)

def usage():
    """Display usage
    """
    print "Usage "+sys.argv[0]+" <options> [components called]\n"+\
          "Components called are highlighted, together with their dependencies.\n"+\
          "Options:\n"+\
          "-h/--help\n\tPrint this usage guide\n"+\
          "-f/--format <valid format for Graphviz>\n\tSpecify format to draw in (default=ps)\n"+\
          "-p/--program <valid Graphviz program>\n\tSpecify program to draw with (default=dot)\n"+\
          "-d/--dir <root directory>\n\tSpecify root directory to find meta.xml in (default=PWD)\n"+\
          "-o/--output <filename>\n\tfilename of outputs (default=nox-component-dependency)\n"+\

#Parse options and arguments
try:
    opts, args = getopt.getopt(sys.argv[1:], "hf:p:d:o:",
                               ["help","format=","program=","directory=",
                                "output="])
except getopt.GetoptError:
    print "Option error!"
    usage()
    sys.exit(2)

#Parse options
format="ps"
filename="nox-component-dependency"
program="dot"
dir="."
for opt,arg in opts:
    if (opt in ("-h","--help")):
        usage()
        sys.exit(0)
    elif (opt in ("-f","--format")):
        format=arg
    elif (opt in ("-p","--program")):
        program=arg
    elif (opt in ("-o","--output")):
        filename=arg
    elif (opt in ("-d","--dir")):
        dir=arg
    else:
        print "Unhandled option :"+opt
        sys.exit(2)
       
#Check program
cmdloc=commands.getoutput("which "+program)
if (cmdloc == ""):
    print program+" not found."
    sys.exit(2)

#Check directory
if not (os.path.isdir("nox/coreapps") and
        os.path.isdir("nox/netapps") and
        os.path.isdir("nox/webapps")):
    print "Not in nox's src directory!"
    sys.exit(2)
    
#Find all meta.xml
cmd='find '+dir+' -name "meta.xml" -print'
components=[]
for metafile in os.popen(cmd).readlines():
    parse_meta_xml(metafile.strip(),components)
highlight_called(components, args)
draw_components(filename+".dot",components)    
print commands.getoutput(program+" -T"+format+" "+\
                         filename+".dot > "+\
                         filename+"."+format)
