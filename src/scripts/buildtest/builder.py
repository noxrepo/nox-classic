#!/usr/bin/python
#
# 2/28/08 TARP
# Prototype for automated source-tree builder for nox
# 3/3/08 TARP
# Working beta, attempting to remove verbose output with output
# redirection, replacing some os/shell calls with subprocess.Popen
# 3/4/08 TARP
# Functionality seems to be complete, poking at some ways to make
# it intelligble as well as able to die gracefully
# 3/19/08 TARP
# Added scrupulous mode to archiving, supresses non-new information,
# this may be extended to some notification changes someday.  Minor
# bugfixes as well.
# 3/20/08 TARP
# Modifying to meet with new directory structure
# 4/9/08 TARP
# Near-total redesign, separated display/archive/result into other files
# hoping to be able to expand to include benchmarking
# 5/7/08 TARP
# Continuing minor modifications, changing directories and implementing
# use of local commited material rather than all local material (via git-clone)
#
# Note that directories end with '/', files are not preceeded by '/' or './'
#
# Notes on Comments:
# '#!' Indicates a pressing concern
# '#?' Indicates a question
# '#@' Indicates an answer
# '#T' Indicates a segment altered (often commented out) for testing
#
# Somewhat Implied Structure:
# .../[dir]/
#          /asena/nox/              -  base directory
#                    /src/          -  source directory
#                        /scripts   -  this file's directory
#
# /tmp/
#     /build/                       -  build directory
#           /user/                  -  user's build directory
#                /default/          -  default build
#                /ndebug/           -  not debugged
#                /twisted/          -  with twisted
#                /twisted_ndebug/   -  with twisted, not debugged
#
# The 'nox_core' command does most work now:
#  $builddir/$buildtype/src/nox_core [tests | noop | pynoop | pyloop |
#                                  -i [pgen:# | pcap:in[:out] | pcapt:in[:out]]]
#
# Strongly Implied Web Structure:
# /var/www/.../                 -  last results, logs, archive
#             /results/         -  symlink to build directory
#             /archive/         -  archive index
#                     /[...]/   - archive files
#

"""
builder.py

Generates and tests various configurations of the NOX tree
run without arguments from .../nox/src/scripts/buildtest/, or provide
it with the base (nox) directory.

Creates and empties directory /tmp/build/[username], fills it with the
appropriately configured options

Options:
  --performance   run and archive performance tests (increases time)
  --only-twisted  only builds once, with twisted and debugging (bug catcher)
  --src-dir=      set the base (nox) directory directly
  --verbosity=    set the level of detail, numbers: (least)[-1, 101](most)
                                           strings: error,print,shallow,
                                                    default,deep,debug
  -v              equivalent to '--verbosity=debug'

  --preserve      do not remove existing build directories, for fast testing
                  (seems to have problems when used with --committed)

  --git-fetch     updates the git repository before building
                  applied to clone, not original, if --committed is used

  --committed     create and use a copy of the git repository via git-clone
                  this will ensure only committed files are included


  --web-update    updates webpage with build information
   (Only with web-update)
    -p            allows progressive webpage generation (created during build)
    -n            turns on e-mail notification of errors
    -a            turns on archiving of webpage results
     (Only with archiving or notification)
      -s          turns on scrupulous (ignore repeat fail) archiving/email

Deprecated:
  --force         (default) will remove existing build subdirectories
                  last argument read honored if used with --preserve
"""

###########
# Imports #
###########

import sys
import os
import subprocess
import time
from signal import signal, SIGINT
import stat
import pwd

import result
import archive
import summary
import performance
from utilities import *


##############
# NoxBuilder #
##############
class NoxBuilder:
    # All variables defined relatively to 'base_directory' are
    # recalculated every time 'base_directory' itself is changed
    # Hardcoded, sadly =)

    user = pwd.getpwuid(os.getuid())[0]

    src_subpath = "src/"
    boot_subpath = "./"   # In base directory
    config_subpath = "./" # In base directory
    oxide_subpath = src_subpath
    openflow_subpath = "../openflow/"
    clone_subpath = "clone/"
    ext_subpath = "src/nox/"

    build_directory = "/tmp/build/%s/" % user
    clone_directory = build_directory + clone_subpath

    fetch = Command("git fetch", "/usr/bin/", "fetch")
    rebase = Command("git rebase origin/master", "/usr/bin/", "rebase")
    clone = Command("git clone", "/usr/bin/", "clone")
    make = Command("make -j3", "/usr/bin/", "make")
    check = Command("make check", "/usr/bin/", "make_check")
    oxide = Command("nox_core", "./", "oxide")
    oxide_pgen = '-i pgen:1 exit'
    oxide_tests = 'tests'

    build_options = {"twisted" : "--with-python=`which python2.5`", \
                     "ndebug" : "--enable-ndebug"}
    src_tree_test_set = ["include/", "lib/", "nox/", \
                         "scripts/", "tests/", \
                         "utilities/"]

    #T mail_to = "nicira-dev@nicira.com"
    mail_to = "reid@nicira.com"
    mail_from = "nicira-dev@nicira.com"
    mail_subject = "Build Failure"
    mail_maintainer = "reid@nicira.com; casado@nicira.com"

    web_directory = '/var/www/buildtest/' + user +'/'
    web_results = 'results/index.html' # symlinked to build directory
    web_logs = {build_directory:'results/'}
    css = '../results.css'

    archive_subdir = "archive/"
    archive_directory = web_directory + archive_subdir
    archive_data = 'archive.pkl'

    benchmark_archive = 'performance.pkl'

    def __init__(self, base_directory = "./../../.."):
        self.__dict__['base_directory'] = base_directory
        self.src_directory = self.base_directory + self.src_subpath
        self.openflow_directory = self.base_directory + self.openflow_subpath
        self.boot = Command("boot.sh", \
                            self.base_directory + self.boot_subpath, \
                            "boot")
        self.config = Command("configure", \
                              self.base_directory + self.config_subpath, \
                              "configure")
        # Re-calculate to un-relativize any directories
        self.base_directory = self.base_directory
        self.result = result.BuildResult(self.build_directory, \
                                         self.base_directory,
                                         self.build_options)

        self.notary= Notary(self.build_directory + 'notes.dump')
        self.note = self.notary.note # This is a function

        # Set up when option is enabled
        self.archive = None
        self.mail = None
        self.page = None
        self.benchmark = None

        self.lock = None # Until build directory created

        # Options
        self.error_notification = False
        self.archiving = False
        self.scrupulous = False
        self.progressive = False
        self.git_fetch = False
        self.clone_src = False
        self.wipe_build = True
        self.new_build = False
        self.new_result = False
        self.conflict = False
        self.web_update = False
        self.performance_testing = False
        self.only_twisted = False


#################
# Set Attribute #
#################
    def __setattr__(self, name, value):
        if name == 'base_directory':
            # Simple_dir gives an absolute path (sans '../')
            value = simple_dir(value)
            self.src_directory = simple_dir(value + self.src_subpath)
            self.openflow_directory = simple_dir(value + self.openflow_subpath)
            self.config.directory = simple_dir(value + self.config_subpath)
            self.boot.directory = simple_dir(value + self.boot_subpath)

        self.__dict__[name] = value


################
# Exit Program #
################
    def fail(self, msg):
        self.note("/* %s" % str(msg),'error')
        if self.lock and self.lock.locked:
            if not self.lock.unlock():
                self.note(' * Unlock Warn: Lock "%s" is missing in "%s"'\
                          % (self.file, self.directory), 'error')
        self.note("\*   Exiting ...",'error')

        if self.web_update and not self.conflict:
            self.result.error = "Irrecoverable failure: %s" % msg
            self.result.success = False
            path = self.web_directory + self.web_results
            self.result.index_path = path

            if self.archiving:
                if (self.scrupulous and \
                   not (self.new_build or self.new_result)):
                    self.note("Nothing new, scrupulously avoiding archival")
                else:
                    self.page.create(path,archiving=True)
                    self.archive.most_recent = path
                    self.archive.add_archive(self.result, self.build_directory)
                    self.archive.create_index()
                    self.archive.save_archive()

            self.page.create(path)

        if self.error_notification:
            self.notify(msg)

        self.notary.epic_fail()
        subrahmanyan(self, self.build_directory + 'dump.html','Builder')
        sys.exit(1)

##########
# Notify #
##########
    def notify(self,msg):
        if self.archive and self.archive.last and \
           self.archive.last.success == False:
            self.note("Suppressing e-mail on repeated failures")
        else:
            self.note("Sending notification e-mail ... ")
            mail = Mailer(self.mail_to, self.mail_from, \
                          self.mail_subject, self.mail_maintainer)
            mail.write('Unsuccessful Build')

            mail.write(msg)
            # Redundant web_update here, since can fail with bad options to
            # this point and send a unacceptable archive link
            if self.web_update and self.archiving and \
               (not self.scrupulous or (self.new_build or self.new_result)):
                self.note("archive ... ")
                mail.write("Permanent Link: %s" % self.archive.last.url)
            mail.write("")
            mail.write("-------------")
            mail.write("For questions, or to report bugs/errors within "+\
                       "the testing program, contact a maintainer:\n" +\
                       "%s\n" % self.mail_maintainer)
            mail.send()
            self.note("Sent mail to %s" % self.mail_to)


##########################
# Call and Log a Command #
##########################
    def logged_call(self, command, args=None, section=None):
        if section == None:
            try:
                note_sec = self.result.current.name
            except:
                note_sec = self.result.default_section
        self.note("[%s] Executing `%s` with %s" %
                  (note_sec, command, (args and args or "no arguments")),'deep')
        success = self.result.logged_call(command, args, section)
        if not success:
            self.note("process returncode = %d"%self.result.last_return,'deep')
            self.note('/* Encountered error ($?=%d) with "%s"' \
                      % (self.result.last_return, command))
            if command.logdir == False:
                self.note("\* No log available")
            else:
                self.note('\* Review log: "%s.log" in "%s""'
                          % (command.logname, command.logdir and
                                              command.logdir or command.cwd))
        else:
            self.note("Executed")
        #! This and BuildCommand.__init__ would have to change to get
        #  the handy feature of ".log"s showing up before they are finished
        if self.web_update and self.progressive:
            self.page.create(self.web_directory + self.web_results, \
                             archiving=False, incomplete=True)
        return success


############################
# Create Build Directories #
############################
    def setup_build_directories(self):
        dir = self.build_directory

        if not os.access(dir, os.F_OK):
            os.mkdir(dir)
        if not os.access(dir, os.F_OK):
            fail('Unable to create build directory "%s"' % dir)

        option_combos = powerset(self.build_options)
        for option in option_combos:
            subdirectory = dir + name_test(option)
            if not os.access(subdirectory, os.F_OK):
                os.mkdir(subdirectory)
            if not os.access(subdirectory, os.F_OK):
                fail('Unable to create build directory "%s"' % subdirectory)

#------------------#
####################
# Validity Testing #
####################
#------------------#

#########################
# Source Tree Existence #
#########################
    def check_src_tree(self):
        num_missing = 0
        for file in self.src_tree_test_set:
            if not os.access(self.src_directory + file, os.F_OK):
                if num_missing == 0:
                    self.note('/* Missing source:', 'error')
                self.note('|*   [%d] "%s"' % (num_missing, file), 'error')
                num_missing += 1

        if num_missing > 0:
            self.note('\* In directory "%s"' % self.src_directory, 'error')
            return False
        else:
            self.note("Source tree verified")
            return True


##########################
# Test For Build Success #
##########################
    def build_checks(self, option):
        success = True
        option_dir = name_test(option.keys())
        self.oxide.cwd = self.build_directory + option_dir + self.oxide_subpath
        self.oxide.logdir = self.build_directory + option_dir

        self.oxide.logname = "oxide_pgen"
        args = [self.oxide_pgen]
        success = success and self.logged_call(self.oxide, args)

        # Temporarily necessary while tests hang without twisted
        # If permanent, can rebuild using dictionary-dependency technique
        if 'twisted' in option:
            self.oxide.logname = "oxide_tests"
            args = [self.oxide_tests]
            success = success and self.logged_call(self.oxide, args)

        # Only test if successful thus far, but do not influence final result 
        if success and self.performance_testing:
            make_time = None
            if self.wipe_build:
                for cmd in self.result.current.commands:
                   if cmd.logname == 'make.log':  #? Hard coded :/
                       make_time = cmd.duration
                       break
            self.benchmark.run_tests(self.logged_call,option.keys(),make_time)

        return success




#----------#
############
# Building #
############
#----------#

###########################
# NOX Builder - All Types #
###########################
    def build_all(self):
        last_build = os.stat(self.build_directory)[stat.ST_ATIME]
        if last_build < self.result.commit_date:
            self.new_build = True

        if self.only_twisted:
            option_combos = [{'twisted': self.build_options['twisted']}]
        else:
            option_combos = powerset(self.build_options)

        for option in option_combos:
            name = name_test(option.keys())
            self.result.section(name)
            self.note('Building "%s" ...' % name)
            if self.build_nox(option):
                self.note('Built "%s"' % name)
            else:
                self.note('** Building "%s" failed' % name, 'print')

#################
# Configuration #
#################
    def build_nox(self, option):
        option_dir = self.build_directory + name_test(option.keys())
        if not os.access(option_dir, os.F_OK):
            self.note('Missing build directory, attempting to create "%s"' \
                      % option_dir)
            os.mkdir(option_dir)
        if not os.access(option_dir, os.F_OK):
            fail('Unable to create build directory "%s"' % option_dir)

        # could switch this to stop after a fail, try that out once rest is
        # working, just mean putting 'success and [blah]' instead
        #T (did so)
        self.config.cwd = option_dir
        success = self.logged_call(self.config, option.values())
        self.make.cwd = option_dir
        success = success and self.logged_call(self.make)
        return success and self.build_checks(option)

###############
# Get Options #
###############
    def get_options(self, argv):
        self.result.section('setup')

        import getopt
        try:
            opts, args = getopt.getopt(argv, "hpansv", \
                                       ["help", "force", "git-fetch", \
                                        "src-dir=", "web-update", \
                                        "only-twisted", "preserve", \
                                        "committed", "performance",
                                        "verbosity="])
        except getopt.error, msg:
            print msg
            print "For help use --help"
            sys.exit(2)

        for o,a in opts:
            # Help
            if o in ("-h", "--help"):
                print __doc__
                sys.exit(0)
            # Standard Options
            elif o == "-a":              self.archiving = True
            elif o == "-n":              self.error_notification = True
            elif o == "-s":              self.scrupulous = True
            elif o == "-p":              self.progressive = True
            elif o == '-v':              self.notary.set_depth('debug')
            elif o == "--preserve":      self.wipe_build = False
            elif o == "--git-fetch":     self.git_fetch = True
            elif o == "--committed":     self.clone_src = True
            elif o == "--src-dir":       self.base_directory = a
            elif o == "--web-update":    self.web_update = True
            elif o == "--only-twisted":  self.only_twisted = True
            elif o == "--performance":   self.performance_testing = True
            elif o == "--verbosity":     self.notary.set_depth(a)

            # Deprecated / Unknown options
            elif o == "--force":
                self.note('Using deprecated opt: --force is default', 'print')
                self.wipe_build = True
            else:
                self.note('Unknown option %s' % o, 'error')

        # Set-up
        if self.error_notification:
                self.mail = Mailer(self.mail_to, self.mail_from, \
                                   self.mail_subject, self.mail_maintainer)
        if self.archiving:
                self.archive = archive.NoxArchive(self.archive_directory,
                                                  self.css, load_old=True)
        if self.web_update:  # Must execute after archive initialized
            self.page = summary.Summary(self.archive, self.result, \
                                        self.web_logs, self.css)
        if self.performance_testing:
            self.benchmark = performance.Benchmarker(self.archive_directory +\
                                                     self.benchmark_archive)

        # Conflict resolution
        if (self.archiving or self.progressive) and not self.web_update:
            self.fail("Must enable web updates for progressive/archive mode."+\
                      " (options -p/-a)")
        if self.scrupulous and not (self.archiving or self.error_notification):
            self.fail("Must archive/email for scrupulous to have an effect."+\
                      " (option -s)")

        # Value checking
        if not os.access(self.base_directory, os.F_OK):
            self.fail('Non-existant base dir "%s" given' % self.base_directory)
        if self.base_directory[-1] != '/':
            self.base_directory += '/'
        if not os.access(self.base_directory, os.F_OK):
            self.fail('Non-directory base dir "%s" given' %self.base_directory)

####################
# Nox Build Tester #
####################
    def test(self):
        if not self.check_src_tree():
            self.fail('Incomplete source tree in "%s"' % self.src_directory)
        if self.git_fetch:
            self.update_git_repository()
        if not os.access(self.config.path(), os.F_OK):
            self.note('Missing config, trying to create with "%s"'%self.boot)
            self.run_boot_script()

        self.build_all()

        self.note('Make Results:')
        self.note('%d of %d Pass' % (self.result.passed(),self.result.total()))
        if self.result.success:
            self.note('All Builds Successful', 'print')
        else:
            self.fail("Did not succeed on every build (Passed: %d/%d)" % \
                      (self.result.passed(), self.result.total()))

        if self.archive and self.archive.last:
            self.new_result = (self.result.success != self.archive.last.success)
        else:
            self.new_result = True

##########################
# Create Build Directory #
##########################
    def create_build_directory(self):
        if not os.access(self.build_directory, os.F_OK):
            self.note('Creating missing build-dir "%s"' % self.build_directory)
            os.makedirs(self.build_directory) # Creates intermediate dirs
        if not os.access(self.build_directory, os.F_OK):
            return False  # Creation failed
        self.lock = Lock(self.build_directory)
        return True

###########################
# Create Duplicate Source #
###########################
    def clone_source_tree(self):
        if os.access(self.clone_directory, os.F_OK):
            self.note('Clone directory exists, removing ...')
            # Deliberately non-global variables/functions
            wipe_args = "rm -rf %s" % self.clone_subpath
            p = subprocess.Popen(wipe_args, stdout=subprocess.PIPE, \
                                 stderr=subprocess.PIPE, shell=True, \
                                 cwd=self.clone_directory.replace( \
                                 self.clone_subpath,'')).wait()
            if os.access(self.clone_directory, os.F_OK):
                return False  # Removal failed

        # Create a clean copy
        os.mkdir(self.clone_directory)

        # Hard coded :(
        self.clone.cwd = self.clone_directory
        self.clone.logdir = self.build_directory
        self.clone.logname = "clone_nox"
        args = [self.base_directory, self.clone_directory + "nox/"]
        if not self.logged_call(self.clone,args):
            self.fail('Unable to clone nox with "%s"' % self.clone)

        self.clone.logdir = self.build_directory
        args = [self.openflow_directory, self.clone_directory + "openflow/"]
        self.clone.logname = "clone_openflow"
        if not self.logged_call(self.clone,args):
            self.fail('Unable to clone openflow with "%s"' % self.clone)

        ##################\   /############################       This Line is
        self.base_directory = self.clone_directory + "nox/" # <-- Non-Trivial
        ##################/   \############################       In Effect

        return True

#########################
# Update Git Repository #
#########################
    def update_git_repository(self):
        self.fetch.cwd = self.base_directory
        self.fetch.logdir = self.build_directory
        if not self.logged_call(self.fetch):
            self.fail('Unable to fetch repository with "%s"' % self.fetch)
        self.rebase.cwd = self.base_directory
        self.rebase.logdir = self.build_directory
        if not self.logged_call(self.rebase):
            self.fail('Unable to rebase repository with "%s"' % self.rebase)

        #! Extension cludge
        self.fetch.logname = "fetch_ext"
        self.fetch.cwd = self.base_directory + self.ext_subpath
        self.fetch.logdir = self.build_directory
        if not self.logged_call(self.fetch):
            self.fail('Unable to fetch repository with "%s"' % self.fetch)
        self.rebase.logname = "rebase_ext"
        self.rebase.cwd = self.base_directory
        self.rebase.logdir = self.build_directory
        if not self.logged_call(self.rebase):
            self.fail('Unable to rebase repository with "%s"' % self.rebase)

        # Update information
        info = git_info(self.result.base_directory)
        self.result.commit = info['commit']
        self.result.merge = info['merge']
        self.result.author = info['author']
        self.result.email = info['email']
        self.result.commit_date = info['date']
        return True

##############################
# Create Configure Directory #
##############################
    def run_boot_script(self):
        path = self.config.directory + self.config.command
        self.boot.cwd = self.base_directory
        self.boot.logdir = self.build_directory
        if not (self.logged_call(self.boot) and os.access(path, os.F_OK)):
            self.fail('Unable to find or create confgure file: "%s"' % path)

#########################
# Erase Build Directory #
#########################
    def erase_build_directory(self):
        # Empty directories in build directory - cuidado => explicit exact call
        if not self.build_directory.endswith(self.user + '/'):
            self.fail('Not rm-ing suspicious build-dir location "%s"' % \
                       self.build_directory)
        # Deliberately non-global variables/functions
        clean_args = "find -nowarn -type d -exec rm -rf {} \;" # o_0
        p = subprocess.Popen(clean_args, stdout=subprocess.PIPE, \
                             stderr=subprocess.PIPE, shell=True, \
                             cwd=self.build_directory)
        for line in p.stdout.readlines():
            self.note(line[:-len('\n')],'shallow')

##########
# Sigint #
##########
def sigint_handler(signal, mask):
    global gbuilder
    dump(gbuilder)
    gbuilder.notary.epic_fail()
    gbuilder.fail("SIGINT caught")

########
# Main #
########
gbuilder = None # Global for sigint

def main():
    builder = NoxBuilder()

    # For sigint testing
    global gbuilder
    gbuilder = builder

    # Prepration / Retreiving Options
    builder.get_options(sys.argv[1:])
    if not builder.create_build_directory():
        builder.fail('Unable to create build-dir "%s"'%builder.build_directory)

    # Lock check
    if not builder.lock.lock():
        builder.conflict = True
        builder.fail("Lock Fail: Another build test is already in progress")

    # Setup
    if builder.wipe_build:
        builder.erase_build_directory()
    if builder.clone_src:
        if not builder.clone_source_tree():
            builder.fail('Unable to git clone in "%s"'%builder.build_directory)

    # Test
    builder.test()

    # Archive
    path = builder.web_directory + builder.web_results
    if builder.web_update and builder.archiving:
        builder.result.index_path = path
        builder.archive.most_recent =  path
        if builder.scrupulous and not (builder.new_build or builder.new_result):
            builder.note("Nothing new, scrupulously avoiding archival")
        else:
            builder.note('Creating archive page')
            builder.archive.most_recent = path
            builder.page.create(path,archiving=True)
            builder.archive.add_archive(builder.result, builder.build_directory)
            builder.archive.create_index()
            builder.archive.save_archive()

    if builder.web_update:
        builder.page.create(path)

    if builder.performance_testing:
        builder.benchmark.show_results()

    # Unlock
    if not builder.lock.unlock():
        builder.fail('Unlock Fail: Lock "%s" missing from "%s"' \
             % (builder.lock.file, builder.lock.directory))

    subrahmanyan(builder,'./dump.html','Builder')


##############
# Main Stuff #
##############
if __name__ == "__main__":
    signal(SIGINT, sigint_handler)
    main()
