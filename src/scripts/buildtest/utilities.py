#!/usr/bin/python
#
# 3/14/08 TARP
# Removing general functions embedded in specific classes
# 3/15/08 TARP
# More commenting and generalization
# 3/21/08 TARP
# Including functions from performance.py
#

import os
import subprocess
import pwd
import time
import stat
import random

default_test_subdir = 'default/'

###########################
# Greatest Common Divisor #
###########################
def gcd(a,b):
    while b:
        a, b = b, a%b
    return a

#########################
# Least Common Mulitple #
#########################
def lcm(a,b):
    return a*b/gcd(a,b)


###################
# Color Generator #
###################
def color_generator(min=.1, max=.8, cycle=1, offset=.3, length=3):
    # Could make these auto-fixes if user input ever becomes
    # involved, but for now these asserts failing would indicate
    # something wrong
    assert min >= 0, "Minimum color value too small (%.2f < 0)" % min
    assert max <= 1, "Maximum color value too large (%.2f > 1)" % max
    assert min <= max, "Min color (%.2f) larger than Max color (.2f)" \
                       % (min, max)
    assert length >= 1, "Must have at least one color value"

    value = []
    for i in range(length):
       value.append(random.random())

    mod = max - min
    shift = min

    # This generates lcm(mod/(gcd(offset,mod),length/gcd(cycle,length)))
    # colors before cycling (using non-decimal helps with rounding errors)
    # Assuming none of the inital random numbers are identical
    # in (mod, shift, length) format
    # for (1,.2,.7) this means 21 colors
    # for (1,.15,.7) this also means 21 colors

    while True:
        temp = value[:]
        for i in range(length):
            temp[i] = (value[(i+cycle)%length]+offset-shift)%mod+shift
        value = temp[:]
        yield value


####################
# Sort By Category #
####################
def sort_by(class_list, *categories):
    # Sorts a list of class instances by a list of attributes,
    # where the attributes are ordered by importance left to right
    # Preserves existing order (by necessity)
    categories = list(categories)
    categories.reverse()
    length = len(class_list)
    sorted = range(length) # Permutation of indices

    for item in categories:
        considered = {}
        for i in range(length):
            value = class_list[sorted[i]].__dict__[item]
            if value in considered:
                considered[value].append(sorted[i])
            else:
                considered[value] = [sorted[i]]

        values = considered.keys()
        values.sort()
        sorting = []
        for value in values:
            for index in considered[value]:
                sorting.append(index)
        assert len(sorting) == length
        sorted = sorting

    ordered = []
    for index in sorted:
        ordered.append(class_list[index])
    return ordered


###################
# Create Powerset #
###################
def powerset(items):
    '''
    Returns a list of all possible combinations of 'items', neglecting
    order and including duplicate entries, contains the null-list
    'items' may be any iterable, dictionaries preserve dictionaryness
    '''
    if type(items) == dict:
        pset = [ {} ]
        for key in items:
            for subdict in pset[:]:
                tempdict = subdict.copy()
                tempdict[key] = items[key]
                pset.append(tempdict)
    else:
        pset = [ [] ]
        for item in items:
            for subset in pset[:]:
                pset.append(subset + [item])
    return pset


############################
# Simplify Directory Name #
############################
def simple_dir(value):
    return os.path.abspath(value) + '/' # meh


#################
# Too Much Info #
#################
def dump(thing, indent=0):
    vars = thing.__dict__.keys()
    vars.sort()
    print "%s [%s]" % (indent*' '+'/', thing.__class__)
    print "%s %s" % (indent*' '+'|', (len(str(thing.__class__))+2)*'-')
    for item in vars:
        if type(thing.__dict__[item]) == type(thing): # that is, instance
            print "%s %20s -" % (indent*' '+'|',item,)
            dump(thing.__dict__[item], indent+5)
            print "%s (%s)" % (indent*' '+'|', thing.__class__)
        else:
            print "%s %20s - %s" % (indent*' '+'|',item,thing.__dict__[item])


##############
# Web-Splode #
##############
def subrahmanyan(thing, filename, name='(Base)'):
    '''
    This presents whatever is passed it in a reasonably logical manner.
    Data is the main focus, thus functions are not extracted from classes.
    Does not handle recursion.
    Sorts dicts/classes by type and name.
    Bound functions are represented with the name and struck-out '()'.

    Passed:
      thing (python anything) - The string/class/file/list/whatever to view
      filename (string) - The name of the file to dump to, should end in '.html'
      name (string) ['(Base)'] - (optional) The name of the object being dumped
    Returns:
      (None)
    '''
    # First
    file = open(filename,'w')
    file.write(_super_begin())
    _chandrasekhar(thing, file, name)
    file.write('<body>\n</html>\n')
    file.close()

def _chandrasekhar(thing, file, name, route=['1']):
    '''
    thing = any python-mabob
    file = open file to write to
    route = array of integers, showing current location in tree
    '''
    # Completely unprotected from recursive structures

    indent = ' '*2*len(route)
    ## Naive infinite avoidance
    #if len(route) > max_depth:
    #   file.write('%s<li><b><tt>Too deep, halting</tt></b></li>' % indent)
    #   return

    file.write('%s<li>' % indent)

    # str() thing is dumb, but otherwise have to import to determine
    # none and instance types
    if str(type(thing)) == "<type 'instance'>":
        file.write(_expander(route + ['1'], '%s &lt;%s&gt;' % \
                                            (name, thing.__class__)))
        _write_instance_items(thing.__dict__, file, route+['1'])
        route[-1] = str(int(route[-1]) + 1)

    elif str(type(thing)) == "<type 'dict'>":
        file.write(_expander(route+['1'], '{%s}'%(name)))
        _write_keyed_items(thing, file, route+['1'])
        route[-1] = str(int(route[-1]) + 1)

    elif str(type(thing)) == "<type 'list'>":
        file.write(_expander(route+['1'], '[%s]'%(name)))
        _write_indexed_items(thing, file, route+['1'])
        route[-1] = str(int(route[-1]) + 1)

    elif str(type(thing)) == "<type 'tuple'>":
        file.write(_expander(route+['1'], '(%s)'%(name)))
        _write_indexed_items(thing, file, route+['1'])
        route[-1] = str(int(route[-1]) + 1)

    elif str(type(thing)) == "<type 'str'>":
        file.write('%s = "%s"' % (name, thing))

    elif str(type(thing)) in ("<type 'bool'>","<type 'NoneType'>"):
        file.write('%s = <i>%s</i>' % (name, thing))

    elif str(type(thing)) == "<type 'instancemethod'>":
        file.write('%s = %s.%s<strike>()</strike>' % (name, thing.im_class, \
                                                       thing.__name__))

    elif str(type(thing)) == "<type 'function'>":
        file.write('%s = %s.%s<strike>()</strike>' % (name, thing.__module__, \
                                                       thing.__name__))
    else:
        file.write('%s = %s' % (name, thing))

    file.write('</li>\n')


def _write_instance_items(items, file, route):
    sorting = {}
    for key in items:
        sorting[str(type(items[key]))+'\1'+key] = key
    sorted = sorting.keys()
    sorted.sort()

    for sort_key in sorted:
        _chandrasekhar(items[sorting[sort_key]], file, \
                       "%s" % sorting[sort_key], route)
    file.write('%s</ul>' % (' '*2*len(route)))

def _write_keyed_items(items, file, route):
    sorting = {}
    for key in items:
        # dicts don't necessarily have     VVV strings as keys
        sorting[str(type(items[key]))+'\1'+str(key)] = key
    sorted = sorting.keys()
    sorted.sort()

    for sort_key in sorted:
        _chandrasekhar(items[sorting[sort_key]], file, \
        # dicts don't necessarily VVV have strings as keys
                       "['%s']" % str(sorting[sort_key]), route)
    file.write('%s</ul>' % (' '*2*len(route)))

def _write_indexed_items(items, file, route):
    for index in range(len(items)):
        _chandrasekhar(items[index], file, '[%s]' % index, route)
    file.write('%s</ul>' % (' '*2*len(route)))


def _expander(route, wrapped):
    indent = ' '*2*len(route)
    route_name = '_'.join(route)
    return \
'''\
%s<a onclick="toggle(this,'%s'); return true">%s</a>
%s<ul name='%s'>
''' % (indent, route_name, wrapped, indent, route_name)


def _super_begin():
    return \
'''\
<html>
<head>
<title>Supernova</title>
<style type="text/css">
ul.hidden {display: none;}
ul.shown {display: block; list-style-image:none;}
li {display: block; list-style-image:none;}
a.hidden {text-decoration: underline; color:blue; font-weight: bold}
a.shown {text-decoration: overline; color:green; font-weight: bold}
</style>
<script type="text/javascript">
function init() {setTimeout('collapse()',100)}
function collapse()
{
    var all_ul = document.getElementsByTagName('ul')
    for (var i=0; i<all_ul.length; i++)
    {
        all_ul[i].className='hidden'
    }

    var all_a = document.getElementsByTagName('a')
    for (var i=0; i<all_a.length; i++)
    {
        all_a[i].className='hidden'
    }
}
function toggle(self, element)
{
    var all = document.getElementsByName(element)
    if (all.length == 0) {return}

    var change = ''
    if (all[0].className == 'hidden'){change = 'shown'}
    else if (all[0].className == 'shown'){change = 'hidden'}

    self.className = change
    for (var i=0; i<all.length; i++){all[i].className = change}
}
//-->
</script>
</head>

<body onload=init()>
<center><table><tr>
<td width=30%><h1>Sic</h1><h4>(Reid '08)</h4></td>
<td width=70%>Full explosion of python data.<br><br>
Click on <b style="text-decoration:underline; color:blue">Blue/Underlined</b> elements to expand them<br><br>
Click on <b style="text-decoration:overline; color:green">Green/Overlined</b> elements to collapse them</td>
</tr></table></center>
<hr>
'''

############
# Git Info #
############
def git_info(repository_directory, git_log_command='git-log -n 1'):
    '''
    Parses git-log to pull information about the current branch of a
    directory's git repository
    Passed:
      repository_directory (string): directory to look for git
      git_log_command (string) ['git-log -n 1']: command to execute
    Returns:
      (None): Attempt failed, usually if non-git directory passed
      (dictionary): with the following key-value pairs
         'commit' (string): 40 character commit number
         'merge' (string): If merged, that unprocessed line, otherwise None
         'author' (string): Author of the last commit
         'email' (string): Email of the last commit's author
         'date' (string): Date of the last commit
    '''

    info = {}
    p = subprocess.Popen(git_log_command, stdout=subprocess.PIPE, \
                         shell=True, cwd=repository_directory)

    notary = Notary()
    if p.wait() != 0:
        notary.note("Unable to git info from directory %s" % \
                    repository_directory, 'error')
        return None

    raw = p.stdout.readlines()
    line = 0
    # 'commit [40 characters]\n'
    info['commit'] = raw[line][len('commit '):-len('\n')]
    line += 1

    # 'Merge: [7 characters]... [7 characters]...\n'
    if raw[line].startswith('Merge:'):
        info['merge'] = raw[line][len('Merge: '):-len('\n')]
        line += 1
    else:
        info['merge'] = None

    # 'Author: [name] <[email]>\n'
    info['author'] = raw[line][len('Author: '):raw[line].find(' <')]
    info['email'] = raw[line][raw[line].find('<')+1:raw[line].find('>')]
    line += 1

    # 'Date:   DoW Mth DD HH:MM:SS YYYY -Diff\n'
    info['date'] = raw[line][len('Date:   '):-len(' -HHHH\n')]
    return info


#################
# Relative Path #
#################
def relative_path(src, dst, base='', match='#'):
    '''
    Calculates relative path from a directory to a file
    Originally intended for relative links in html
    Passed:
      src (string): source directory (can be file, only used if src=dst)
      dst (string): destination file
      base (string) ['']: error if both paths do not begin with this
      match (string) ['#']: return value when strings are identical
    Returns:
      (string): representation of relative path, or 'match' if they are equal
    '''
    # Assume both files start with identical 'base' when relevant
    # For example, '/var/www/'
    assert src.startswith(base)
    assert dst.startswith(base)

    if src == dst:
        return match

    # Break paths into directories
    src_dirs = src.split('/')[:-1] # drop file or trailing slash
    dst_dirs = dst.split('/')
    dst_dirs,dst = dst_dirs[:-1], dst_dirs[-1]

    most = min(len(src_dirs), len(dst_dirs))
    for i in range(most):
        if src_dirs[0] == dst_dirs[0]:
            del src_dirs[0]
            del dst_dirs[0]
        else:
            break

    for i in range(len(src_dirs)):
        src_dirs[i] = '..'

    return '/'.join(src_dirs + dst_dirs + [dst])


############################
# Create Subdirectory Name #
############################
def name_test(tests):
    if not tests:
        global default_test_subdir
        return default_test_subdir
    else:
        tests.sort()
        return "_".join(tests) + '/'


#---------#
###########
# Command #
###########
#---------#
class Command:
    def __init__(self, cmd, dir=None, lname=None):
        self.logdir = None
        self.cwd = None

        self.command = cmd
        self.directory = dir
        self.logname = lname

    def __str__(self):
        return "(%s) %s%s" % (self.logname, self.directory, self.command)

    def path(self):
        return self.directory + self.command

    def execute(self, args, **kwargs):
        if args == None:
            args = []
        command = " ".join([self.path()] + list(args))
        if 'cwd' not in kwargs:    kwargs['cwd'] = self.cwd
        return subprocess.Popen(command, shell=True, **kwargs)


#--------#
##########
# Notary #
##########
#--------#
class Notary:
    notes = []  # This is deliberately shared
    depth = None

    def __init__(self, file=None, min=0, max=100):
        self.file = file
        self.min_depth = min
        self.max_depth = max
        if Notary.depth == None:
            Notary.depth = min

        self.depth_name =\
        {
            'error':   self.min_depth - 1,
            'print':   self.min_depth,
            'shallow': self.min_depth + (self.max_depth - self.min_depth)*.25,
            'default': self.min_depth + (self.max_depth - self.min_depth)*.50,
            'deep':    self.min_depth + (self.max_depth - self.min_depth)*.75,
            'debug':   self.max_depth + 1
        }


############################
# (Modified) Get Attribute #
############################
    def __getattr__(self, attribute):
        '''
        Allows user to set display threshold with ___.error(), ___.debug(),
        or any other string contained as a key in the depth_name dictionary
        '''
        if attribute in self.depth_name:
            def foo():
                self.set_depth(attribute)
            return foo
        else:
            raise AttributeError, attribute

    def __str__(self):
        return "%d Notes in %s - Depth at %d (%d-%d)" % \
          (len(self.notes),self.file,self.depth,self.min_depth,self.max_depth)

    def note(self, text, depth=None):
        if depth == None:  depth = self.depth_name['default']
        if depth in self.depth_name:
            depth = self.depth_name[depth]
        depth = max(self.min_depth, depth)
        depth = min(self.max_depth, depth)

        if depth <= self.depth:
            print text
        Notary.notes.append((text,depth))

    def set_depth(self, value):
        if value in self.depth_name:
            # String
            Notary.depth = self.depth_name[value]
        else:
            try:
                # Number
                Notary.depth = int(value)
            except:
                note('Bad argument passed to set depth', 'error')

    def epic_fail(self):
        info = []
        for (text, depth) in Notary.notes:
            significance= (self.max_depth-depth)/(self.max_depth-self.min_depth)
            info.append('%3d %10s "%s"'%(depth,'*'*int(10.*significance),text))
        info = "\n".join(info) + "\n"

        if self.file:
            print "Transcript of process notes can be found at %s" % self.file
            f = open(self.file,'w')
            f.write(info)
            f.close()
        else:
            print "Transcript of the process follows:"
            print info


#------#
########
# Lock #
########
#------#
class Lock:
    user = pwd.getpwuid(os.getuid())[0]
    notary = Notary() # No log file
    note = notary.note # This is a function

    def __init__(self, directory, file='.lock'):
        self.locked = False
        self.directory = directory
        self.file = file

    def __str__(self):
        if self.locked:
            return '%s is locked with %s [%s]' % \
                   (self.directory, self.file, self.user)
        else:
            return '%s is not locked [%s]' %  (self.directory, self.user)

    def lock(self):
        if os.access(self.directory + self.file, os.F_OK):
            if self.override_approve():
                return self.lock()
            else:
                return False
        f = open(self.directory + self.file, "w")
        f.write(self.user)
        f.close()
        self.locked = True
        return True

    def unlock(self):
        if not os.access(self.directory + self.file, os.F_OK):
            return False
        os.remove(self.directory + self.file)
        self.locked = False
        return True

    def override_approve(self):
        yes = 'y'.lower()
        no = 'n'.lower()

        began = time.ctime(os.stat(self.directory + self.file)[stat.ST_CTIME])
        log = open(self.directory + self.file)
        lock_user = log.read()
        log.close()

        force = ""
        n = self.note
        n("--------------------------------------------------",'error')
        n("It appears that this directory is already locked",'error')
        n("A lock by user         %s" % lock_user, 'error')
        n("Was placed at          %s" % began, 'error')
        n("The current time is    %s" % time.ctime(), 'error')
        while force not in (yes,no):
            try:
                force = raw_input("Force removal of build lock (%s/%s)? "\
                                  % (yes, no.upper())) # not force is default
                force = force.lower()
                if force == '':  force = no
            except:
                force = no
        if force == yes:
            n("Unlocking ...",'error')
            self.unlock()
        n("--------------------------------------------------",'error')
        return force == yes


#--------#
##########
# Mailer #
##########
#--------#
class Mailer:
    command = "/usr/sbin/sendmail -oi -t"

    def __init__(self, recipient, sender, subject=None, reply=None):
        self.msg = []

        self.recipient = recipient
        self.sender = sender
        self.reply = reply and reply or sender
        self.subject = subject and subject or 'No Subject'

    def __str__(self):
        return '%s --> %s: "%s" [...]x%d' % \
              (self.sender, self.recipient, self.subject, len(self.msg))

    def header(self):
        head = []
        head.append('To: %s' % self.recipient)
        head.append('From: %s' % self.sender)
        head.append('Reply-to: %s' % self.reply)
        head.append('Subject: %s' % self.subject)
        head.append('')
        return head

    def write(self, msg):
        self.msg.append(msg)

    def send(self):
        mail = subprocess.Popen(self.command, stdout=subprocess.PIPE, \
                                stdin=subprocess.PIPE, shell=True)
        mail.stdin.write("\n".join(self.header() + self.msg))
        mail.stdin.write("\n\0")
        mail.stdin.close()
