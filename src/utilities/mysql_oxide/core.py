
# this is a fake component class so that we can load components in a
# all python environment without oxide

class Component:
  def __init__(self, ctx, name):
    pass

  def configure(self, configuration):
    pass

  def install(self):
    pass

  def getInterface():
    raise Exception("sub-class must implement getInterface()")

