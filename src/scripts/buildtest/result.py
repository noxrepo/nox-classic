#!/usr/bin/python
#
# 3/7/08 TARP
# Attempting to disintegrate results process from builder.py, archive.py
#

import time
import os
import sys
import pwd
import subprocess
import platform

from utilities import *


class BuildResult:
    git_log_command = 'git-log -n 1'
    user = pwd.getpwuid(os.getuid())[0]
    machine = platform.uname()[1]
    default_section = 'Miscellaneous'
    commands = sys.argv[1:]

    def __init__(self, dir, base_dir, options, time_exact=None,index_path=None):
        self.structure = {}
        self.sections = []

        self.current = None
        self.last_return = None
        self.success = True # setting this calculates 'result'
        self.error = None

        self.directory = dir
        self.options = options
        # setting 'time_exact' calculates 'time_readable'
        self.time_exact = time_exact and time_exact or time.time()
        self.index_path = index_path

        self.base_directory = base_dir

        info = git_info(self.base_directory)
        self.commit = info['commit']
        self.merge = info['merge']
        self.author = info['author']
        self.email = info['email']
        self.commit_date = info['date']

    def __setattr__(self, name, value):
        if name == 'time_exact':
            # 'DoW Mth DD HH:MM:SS YYYY' filled with spaces
            self.time_readable = time.ctime(value)
        elif name == 'success':
            self.result = value and 'pass' or 'fail'

        self.__dict__[name] = value

    def passed(self):
        count = 0
        for section in self.sections:
            if section.passed() == section.total():
                count += 1
        return count

    def total(self):
        return len(self.sections)

    def duration(self):
        # this could be improved to do real-time value, not
        # time-efficient to do so, minimal usage gain there
        sum = 0
        for section in self.sections:
            sum += section.duration()
        return sum

    def archive_name(self):
        return time.strftime("%Y_%02m_%02d_%02H%02M%02S/",\
                             time.localtime(self.time_exact))

    def archive_html(self):
        return \
'''\
<li class="%s"><a class="%s" href="%s">%s</a> - \
<tt>Author: %s &lt;%s&gt;</tt></li>\
''' % (self.result, self.result, self.archive_name(), self.time_readable, \
       self.author, self.email)

    def section(self, name):
        if name == None:
            name = self.default_section
        for section in self.sections:
            if section.name == name:
                self.current = section
                return 'Found'
        self.sections.append(BuildSection(name))
        self.current = self.sections[-1]
        return 'Created'

    def logged_call(self, command, args=None, for_section=None):
        import copy
        command = copy.copy(command)
        if command.cwd == None:
            command.cwd = os.getcwd() + '/'
        if command.logdir == None:
            command.logdir = command.cwd
        if command.logname == None:
            command.logname = command.command.replace(' ','_')

        if command.logdir == False:
            return self.current.logged_call(command, args)
             
        dirs = command.logdir.replace(self.directory,'',1)  # use relative dir
        dirs = dirs.split('/')[:-1]  # drop blank from trailing slash

        # Fill in missing plan directories
        plan = self.structure
        for i in range(len(dirs)):
            dirs[i] += '/'
            if dirs[i] not in plan:
                plan[dirs[i]] = {}
            plan = plan[dirs[i]]

        # Don't override general sectioning
        original = self.current
        if for_section:
            self.section(for_section)
        elif not self.current:
            self.section(None)
        running = self.current
        self.current = original

        plan[command.logname + '.log'] = None
        success = running.logged_call(command, args)
        self.success = success and self.success
        # value isn't used in the plan, perhaps in the future
        plan[command.logname + '.log'] = success
        self.last_return = running.last_return
        return success

#############################

class BuildSection:
    def __init__(self, name):
        self.commands = []
        self.last_return = None

        self.name = name
        self.success = True  # Sets result

    def passed(self):
        count = 0
        for command in self.commands:
            if command.success:
                count += 1
        return count

    def total(self):
        return len(self.commands)

    def duration(self):
        sum = 0
        for command in self.commands:
            sum += command.duration
        return sum

    def logged_call(self, command, args=None):
        self.commands.append(BuildCommand(command, args))
        successful = self.commands[-1].success
        self.success = self.success and successful
        self.last_return = self.commands[-1].returncode
        return successful

    def __setattr__(self, name, value):
        if name == 'success':
            self.result = value and 'pass' or 'fail'

        self.__dict__[name] = value

#############################

# Maintain file-storage bit for now, it is better at dealing with massive
# data overflows in logs than python is
class BuildCommand:
    notary = Notary() # No individual log file
    note = notary.note # This is a function

    def __init__(self, command, args):
        if command.logdir == False:
            self.note("Writing empty log")
            f = open('/dev/null','w')
            p = command.execute(args,stdout=f,stderr=f,\
                                cwd=command.cwd)
            self.success = (p.wait() == 0) and True or False
            self.duration = 0

        else:
            self.note("Writing log " +command.logdir+command.logname + '.log')
            log = open(command.logdir + command.logname + '.log', 'w')
            log.write("Command Directory: %s\n" % command.directory)
            log.write("Command: %s\n" % command.command)
            log.write("Arguments: %s\n" % args)
            log.write("Working Directory: %s\n" % command.cwd)
            log.write("\n")
            log.flush()

            start = time.time()
            p = command.execute(args, stdout=log, stderr=log, cwd=command.cwd)
            self.success = (p.wait() == 0) and True or False
            self.duration = time.time() - start
            log.close()

        self.returncode = p.returncode

        self.command = command.command
        self.cwd = command.cwd
        self.logname = command.logname + '.log'
        self.logdir = command.logdir
        self.name = command.logname.replace('_',' ').title()
        if command.logdir:
            self.log = command.logdir + command.logname + '.log'
        else:
            self.log = False

    def __setattr__(self, name, value):
        if name == 'success':
            self.result = value and 'pass' or 'fail'
        elif name == 'logname':
            if 'logdir' in self.__dict__ and self.logdir:
                self.log = self.logdir + value + '.log'
        elif name == 'logdir':
            if 'logname' in self.__dict__:
                if value:
                    self.log = value + self.logname + '.log'
                else:
                    self.log = False

        self.__dict__[name] = value
