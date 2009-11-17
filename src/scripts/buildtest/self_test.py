#!/usr/bin/python
#
# 5/9/08 TARP
# Using powerset to test all possible combinations of options for builder.py
#

from utilities import *
from subprocess import Popen

#! This could be less hardcoded, if it wasn't hardcoded in builder.py
builder_options = ['--preserve', '--git-fetch', \
                   '--committed', '--web-update', '-p', '-n', '-a', \
                   '-s','--dummy-arg']

# This takes insanely long ...
def main():
  for options in powerset(builder_options):
    Popen('./builder.py --only-twisted ' + ' '.join(options), shell=True).wait()

########
# Main #
########
if __name__ == "__main__":
    main()
