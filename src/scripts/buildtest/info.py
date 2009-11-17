#!/usr/bin/python
#
# TARP
# 5/15/08
# Extracting Info and derived class from performance.py, for ease of
# documentation, maintenance, and clarity.
#

from utilities import git_info, Command, Notary
from copy import copy
from pylab import date2num
from datetime import datetime
from time import strptime, ctime

# Might not need these once fully incorporated, can pull from builder
from pwd import getpwuid
from os import getuid
from platform import uname

class Info:
    def matches(self, other):
        match = []
        keys = self.__dict__.keys()
        keys.sort()
        if other == False:
            for k in keys:
               match.append(None)
        elif other == None:
            for k in keys:
               match.append(self.__dict__[k])
            return match
        else:
            for k in keys:
                match.append(self.match_check(other.__dict__[k], \
                                              self.__dict__[k], \
                                              "%s: " % k.title()))
                if match[-1] == False:
                    return False

        return tuple(match)

    def match_check(self, input, value, name):
        # Input:
        # None -> Discrete graphing
        # True -> Independent variable
        # False -> Unused
        # Value -> Exact match
        #
        # Return:
        # None -> Unused
        # False -> No match
        # Value -> Part of a point's classification

        if input == None:
            return name + str(value)
        elif input == True or input == False:
            return None
        elif input != value:
            return False

    # These five functions are only used for making strings in the
    # legend, might be overkill in some sense
    def graph_match(self, style):
        keys = self.__dict__.keys()
        keys.sort()
        match = []
        # Variable (independent), Unused (ignore), Used (wildcard)
        if style in (True, False, None):
            for k in keys:
                if self.__dict__[k] == style:
                    match.append(k)
        # Considered (exact)
        else:
            for k in keys:
                if self.__dict__[k] not in (True, False, None):
                    match.append(k)
        return match

    def graph_variable(self):
        return graph_match(True)

    def graph_used(self):
        return graph_match(None)

    def graph_unused(self):
        return graph_match(False)

    def graph_considered(self):
        return graph_match('this is not None or True or False')

    def __str__(self):
        string = ""
        keys = self.__dict__.keys()
        keys.sort()
        for k in keys:
            string += "%s:  %s\n" % (k.replace("_"," ").title(), \
                                     self.__dict__[k])
        return string


class Profile(Info):
    def __init__(self, user=None, machine=None, run_date=None):
        if user == None:
            user = getpwuid(getuid())[0]
        if machine == None:
            machine = uname()[1]
        if run_date == None:
            run_date = ctime()
        self.user = user
        self.machine = machine
        self.run_date = run_date

class Build(Info):
    def __init__(self, commit=None, last_author=None, build_date=None):
        if (commit == None) or (last_author==None) or (build_date==None):
            info = git_info('./') #? Needs fix? src_directory
            if info:
                commit = commit or info['commit']
                last_author = last_author or info['author']
                build_date = build_date or info['date']
        self.commit = commit
        self.last_author = last_author
        self.build_date = build_date

class Test(Info):
    def __init__(self, configuration=None, command=None, packets=None):
        self.configuration = configuration
        self.command = command
        self.packets = packets
        self.rules = None
        self.policies = None

class Result(Info):
    def __init__(self, total=None, user=None, system=None):
        self.total = total
        self.user = user
        self.system = system



# Archive storage use:
# About 1 Kb / 3 points, which is perhaps rubbish, seems like I could do
# that in plaintext much easier.  If you run a 4 prong test every ten
# minutes, it takes a little over five days to accumulate a megabyte
# of data.  Further storage gains could easly be procured via non-raw
# data type (pre-sort by build, machine, etc)

class RawData:
    # Used by the 'matches(search)' function
    # Result is ommitted, since no exact matches would ever occur
    #?#! Once ranges implemented, could be useful to add it back in
    # (e.g.: you could find operations taking less than 10 seconds,
    #  or builds that took over 20 minutes)
    checklist = ("profile", "build", "test")
    #? Should this include pps and spmp and whatever else is defined
    # by users?, better to just list result as to-be-excluded?
    #? Or even just hardcode in result as excluded?
    #? Perhaps could prefix un-looked-at variables with a '_'

    notary = Notary() # This does not have its own logfile
    note = notary.note # This is a function

    def __init__(self, profile=Profile(), build=Build(), \
                 test=Test(), result=Result()):
        from copy import copy
        # The first two could be not-copied, equivalently
        # They aren't going to vary, under this implementation
        self.profile = copy(profile)
        self.build = copy(build)
        self.test = copy(test)
        self.result = copy(result)

        # In theory, these are readonly/calculated values
        # TODO define __getattr__ for them later
        if (result and result.total) and (test and test.packets):
            self.pps = test.packets/result.total
            self.spmp = 10**6*result.total/test.packets
        else:
            self.pps = None
            self.spmp = None

    def __str__(self):
        pps = self.pps
        if self.pps:
            pps = "%d" % self.pps

        spmp = self.spmp
        if self.spmp:
            spmp = "%.2f" % self.spmp

        return "Profile:\n%s\n\nBuild:\n%s\n\nTest:\n%s\n\nResult:\n%s\n\n" \
                % (self.profile, self.build, self.test, self.result) + \
               "Pkt/sec: %s\nsec/MPkt: %s\n" % (pps, spmp)

    def matches(self, search):
#        match = (self.profile.matches(search.profile),
#                 self.build.matches(search.build),
#                 self.test.matches(search.test))
        match = []
        #! This checklist can be removed with better search defaults
        # Ideally, this would also accept tuples of min/max range, as
        # well as lists of exact matches, for any input
        for item in self.checklist:
            check = self.__dict__[item].matches(search.__dict__[item])
            if check:    match.append(check)
            else:        return False

        #?  Forget why tuple is necessary
        return tuple(match)


    def get(self, attribute):
       from pylab import date2num
       from time import strptime

       # e.g.: 'result.system' => ['result','system']
       attribute = attribute.split('.')
       value = self
       try:
           for subattr in attribute:
               value = value.__dict__[subattr]
           #! pyplot is irritating, this should be done elsewhere
           if 'date' in attribute[-1]:  # 'value is a date' kludge
               value = date2num(datetime(*strptime(value)[0:6]))
           return value
       except AttributeError:
          self.note('Attribute "%s" not found'%' '.join(attribute),'error')
          # This could be improved by storing valid subattr along the way
          return None

    def str_graph(self, style):
        text_string = []
        string_header = {'value': 'Fixed over:', \
                         None:   'Varying over:', \
                         False:  'Ignoring:'}
        if style in string_header:
            text_string.append(string_header[style])
        else:
            text_string.append(string_header['value'])

        #! These aren't all sections, e.g.: pps, spmp
        keys = self.__dict__.keys()
        keys.sort()
        for k in keys:
            if k == 'checklist':  continue #? Instead 'in self.ignorelist'?
            section = self.__dict__[k]
            assert section != True
            # If not 'False' or 'None' (illegal for entire section to be True)
            # Then it is precisely defined, and used to evaluate
            if section:
                for item in section.graph_match(style):
                    text_string.append("  %s.%s" % (k.title(), item))
                    if section.__dict__[item]:  # Has a value
                        text_string[-1] += "=%s" % section.__dict__[item]
            elif section == style:  # i.e.: Entire section is None/False
                    # Is a class
                    if k in self.checklist or k == 'result':
                        #! >< Kludge for formatting's sake
                        text_string.append("  %s.*" % k.title())
                    # Is a variable
                    else:
                        text_string.append("  %s" % k)
        return "\n".join(text_string)

    def str_graph_fixed(self):
        return self.str_graph('not None or True or False')

    def str_graph_used(self):
        return self.str_graph(None)

    def str_graph_ignored(self):
        return self.str_graph(False)
