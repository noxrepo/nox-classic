#!/usr/bin/python
#
# TARP
# 3/13/08
# Prototype to print out results of running a couple million packets
# through various configurations of NOX and packet handling
#
# TARP
# 3/14/08
# Corrected resource consumption, switched from time() to getrusage(),
# print out a few more statistics to get a feel for the ranges expected.
#
# TARP
# 3/17/08
# Added graphing via matplotlib/pylab, lines and such, classes to hold data
#
# TARP
# 3/18/08
# Included bar plot support, automatically used for discrete variables
#
# TARP
# 3/19/08
# Restructuring so that data control smoother, seperating locating points
# from plotting them, adding standard deviation support for viewability
# creating dataset class
#  ... 3/20/08
# Sleep the wee hours.  Total reformat complete, old version left in for final
# reviewing, soon to be trimmed, probably only keep a barplot method.
# More minor changes with legend, visual aspects.
#
# TARP
# 4/24/08
# Returning after directory rehash, only change should hopefully just be
# trivial command change for testing purposes.
#
# TARP
# 5/13/08
# Beginning effort to incorporate performance into build testing
#
# TARP
# 5/14/08
# Stripped Info() and derived classes into info.py.  Additionally placed
# all of the graphing functions into graph.py.
#

# Fixes silly pylab dependency error
import matplotlib
matplotlib.use('Agg')

import os
import pwd
import pickle
import info
import graph
from utilities import name_test, Notary, Command
from datetime import datetime


class Benchmarker:
    user = pwd.getpwuid(os.getuid())[0]
    build_path = "/tmp/build/%s/" % user
    build_default = "default/"
    src_directory = "/home/%s/base_directory/asena/" % user # Only for gitinfo
    # This is probably incorrect, check against builder
    #? Should we need once integrated?
    oxide = Command("nox_core -i pgen:","./src/","oxide pgen")
    #T For now... leaving old version
    test_command = oxide.command
    test_subdir = oxide.directory[len('./'):]
    test_finish = 'exit'
    test_all = ["noop", "switch"]
    test_options = {"twisted":["pynoop", "sepl routing"], "ndebug":[]}
    #test_options = {"twisted":["pynoop"], "ndebug":[]}

    notary = Notary() # No individual log file
    note = notary.note # This is a function

    def __init__(self, input=False, output=None):
        if output == None:    output = input
        self.retrieving = input
        self.storing = output

        self.raw_points = []
        self.test_packets = 100000
        self.control_packets = 1000

        if self.storing and not os.access(self.storing,os.F_OK):
            self.note("Creating new archive at %s" % self.storing)
            pickle.dump([],open(self.storing,'w'))
        if self.retrieving:
            try:
                self.raw_points = pickle.load(open(self.retrieving,'r'))
            except:
                self.note("Error unpickling %s, continuing..." % \
                     self.retrieving,'shallow')

    def run_tests(self, logged_call, option_set, make_total_time):
        from subprocess import Popen, PIPE
        from resource import getrusage, RUSAGE_CHILDREN

        start_use = getrusage(RUSAGE_CHILDREN)[0:2]

        testing = info.Test()
        testing.configuration = option_set
        result = info.Result()
        build = info.Build()

        # Is passed 'None' when not fully built
        if make_total_time:
            result.total = make_total_time
            testing.command = 'make'
            self.raw_points.append(info.RawData(test=testing, \
                                                result=result, \
                                                build=build))

        testing.packets = self.test_packets
        subpath = self.build_path + name_test(option_set)
        self.note("%s starting ..." % subpath)
        for tests in [self.test_all] + \
                     [self.test_options[opt] for opt in option_set]:
            # This does not take advantage of multiple processors
            for test in tests:
                testing.command = test
                run = self.test_command + str(self.test_packets)+" "+test
                if 'sepl' in self.test_command:
                    run += " --verbose='sepl:ANY:ERR'"
                self.note("Executing: ./%s ... " % run,'deep')

                f = open('/dev/null','w')

                # Correct for start-up time somewhat
                older = getrusage(RUSAGE_CHILDREN)[0:2]
                ctl = self.test_command + str(self.control_packets)+" "+test
                p = Popen(subpath+self.test_subdir+ctl+" "+self.test_finish,\
                          stdout=f, stderr=f, \
                          shell=True, cwd=subpath + self.test_subdir).wait()

                old = getrusage(RUSAGE_CHILDREN)[0:2]
                p = Popen(subpath+self.test_subdir+run+" "+self.test_finish,\
                          stdout=f, stderr=f, \
                          #? Have to send this somewhere else (than PIPE), sepl
                          # routing gets massive amounts of data, better off
                          # going to /dev/null if I don't use anyway
                          # sepl seems to crash if PIPE used even with 1M pkt
                          shell=True, cwd=subpath + self.test_subdir).wait()

                new = getrusage(RUSAGE_CHILDREN)[0:2]

                result.user = (new[0] - old[0]) - (old[0] - older[0])
                result.system = (new[1] - old[1]) - (old[1] - older[1])
                result.total = result.user + result.system

                retval = p and 'false' or 'true'  # i.e.: the unix command
                c = Command(retval, '/bin/', '%s [performance] (%.2f)' \
                            % (test, result.total))
                c.logdir = False
                logged_call(c)

                if p != 0:
                    #! This doesn't catch pynoop's problem
                    self.note("Execution failed ... continuing",'shallow')
                    continue

                outcome =info.RawData(test=testing,result=result,build=build)
                self.raw_points.append(outcome)

                self.note("Took: %ss" % result.total,'deep')
                if(outcome.pps):
                    self.note("Pkt/sec: %d" % \
                         (testing.packets/result.total), 'deep')
                if(outcome.spmp):
                    self.note("sec/MPkt: %.2f" % \
                         (10**6*result.total/testing.packets),'deep')

        end_use = getrusage(RUSAGE_CHILDREN)[0:2]
        elapsed = (end_use[0] + end_use[1]) - (start_use[0] + start_use[1])

        if self.storing:
            self.note("Archiving result in %s" % self.storing, 'deep')
            pickle.dump(self.raw_points,open(self.storing,'w'))

        #! This could be simplified readily, particularly if the
        # significant digits of seconds stay constant throughout.
        if elapsed > 60*60:
            self.note("Total time: %dh %dm %ds" % \
                  (elapsed / (60*60), (elapsed % (60*60)) /60, elapsed % 60))
        elif elapsed > 60:
            self.note("Total time: %dm %.2fs" % (elapsed / 60, elapsed % 60))
        else:
            self.note("Total time: %.4fs" % elapsed)

        self.note("%s finished" % subpath)


    def show_results(self):

        # Graphing seconds per mega-packet vs commit date
        search_profile = info.Profile()
        search_build = info.Build()
        search_test = info.Test()
        search_result = info.Result()

        # Independent Variable
        search_build.build_date = True
        # Not considered:
        search_profile = False
        search_build.commit = False
        search_build.last_author = False
        search_test.rules = False
        search_test.policies = False
        search_result = False
        # All values of:
        search_test.configuration = None
        search_test.packets = None

        # By not recreating grapher each time, expose self to the
        # xx-small font bug if too much to show for any one of these
        # This is deliberate, good incentive to fix =)
        g = graph.Grapher(self.raw_points,'placeholder') # The name of the image

        #######################
        # pgen:1000000 sepl routing [audit exit]
        # Exact match:
        search_test.command = 'sepl routing'
        search = info.RawData(profile = search_profile, \
                              build = search_build, \
                              test = search_test, \
                              result = search_result)
        g.image_dst = 'sepl_routing_cmd'
        g.graph('build.build_date', 'pps', search)

        #######################
        # pgen:10000000 switch
        # Exact match:
        search_test.command = 'switch'
        search = info.RawData(profile=search_profile,
                              build=search_build,
                              test=search_test,
                              result=search_result)
        #! Write a function for this assignment
        g.image_dst = 'switch_cmd'
        g.graph('build.build_date', 'pps', search)

        #######################
        # pgen:10000000 noop
        # exact match:
        search_test.command = 'noop'
        search = info.RawData(profile=search_profile,
                              build=search_build,
                              test=search_test,
                              result=search_result)
        #! write a function for this assignment
        g.image_dst = 'noop_cmd'
        g.graph('build.build_date', 'pps', search)


        #######################
        # pgen:10000000 pynoop
        # exact match:
        search_test.command = 'pynoop'
        search = info.RawData(profile=search_profile,
                              build=search_build,
                              test=search_test,
                              result=search_result)
        #! write a function for this assignment
        g.image_dst = 'pynoop_cmd'
        g.graph('build.build_date', 'pps', search)

        #######################
        # build time
        # Exact match:
        search_test.command = 'make'
        search_test.packets = False
        search = info.RawData(profile=search_profile,
                              build=search_build,
                              test=search_test,
                              result=search_result)
        #! Write a function for this assignment
        search.pps = False
        search.spmp = False
        g.image_dst = 'make_cmd'
        g.graph('build.build_date', 'result.total', search)


#def main():
#   b = Benchmarker('zz_performance_archive')
## Fake make times are the integers
#   b.run_tests(['twisted'],314)
#   b.run_tests(['ndebug'],213)
#   b.run_tests([],218)
#   b.run_tests(['ndebug','twisted'],227)
#   b.show_results()
#
#if __name__ == '__main__':
#    main()
