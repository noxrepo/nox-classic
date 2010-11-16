import sys
import xml.dom.minidom
import json
import xml.dom
from xml.dom import Node

def parse_dependency (n):
  n = n.firstChild
  while n:
    if n.nodeType == Node.ELEMENT_NODE:
      if n.tagName == 'name':
        return str(n.firstChild.data)

    n = n.nextSibling

  return None

def parse_component (n):
  n = n.firstChild
  data = {}
  dependencies = []

  while n:
    if n.nodeType == Node.ELEMENT_NODE:
      if n.tagName == 'dependency':
        dependencies.append(parse_dependency(n))
      else:
        data[n.tagName] = str(n.firstChild.data)

    n = n.nextSibling

  if len(dependencies) > 0:
    data["dependencies"] = dependencies

  return data

def parse_components (n):
  n = n.firstChild
  components = []
  while n:
    if n.nodeType == Node.ELEMENT_NODE:
      if n.tagName == 'component':
        components.append(parse_component(n))
    n = n.nextSibling

  return components

def parse_top (n):
  n = n.firstChild
  components = []
  while n:
    if n.nodeType == Node.ELEMENT_NODE:
      if n.tagName == 'components:components':
        components += parse_components(n)
    n = n.nextSibling

  return components

if __name__ == "__main__":
  try:
    if len(sys.argv) != 2: raise

    d = xml.dom.minidom.parse(sys.argv[1])

    print json.dumps({"components" : parse_top(d)}, indent = 2)
  except:
    print "Usage:\n  ", sys.argv[0], " meta.xml > meta.json"
