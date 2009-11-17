#!/usr/bin/python
#
# 3/4/08 TARP
# Attempting to disintegrate archival process from builder.py
#
# 3/7/08
# Completed disintegration of archive and archive index page, using
# pickle to store archive data between runs.  Pulling out result.py from
# this as well as in builder.py
#
#

import os
import sys
import shutil
import time
import platform
import pickle

from utilities import *

#-------------#
###############
# Nox Archive #
###############
#-------------#
class NoxArchive:
    index = 'index.html'
    file_base = '/var/www/'
    web_base = "http://%s.nicira.com/" % platform.uname()[1]
    data = 'archive.pkl'

    notary = Notary() # No output file for this
    note = notary.note # This is a function

    def __init__(self, directory, css, load_old=True):
        self.files = []
        self.most_recent = None  # './../results.html'
        self.last = None

        self.page = NoxArchiveIndex(css)
        self.directory = directory    # '/var/www/buildtest/[user]/archive/'

        if load_old:
            self.load_archive()

##########################
# Create or Load Archive #
##########################
    def load_archive(self):
        try:
            f_in = open(self.directory + self.data,'r')
            load = pickle.load(f_in)
            self.__dict__ = load.__dict__
            f_in.close()
        except:
            pass

#################
# Store Archive #
#################
    def save_archive(self):
        f_out = open(self.directory + self.data, 'w')
        pickle.dump(self, f_out)
        f_out.close()

#################
# Set Attribute #
#################
    def __setattr__(self, name, value):
        if name == 'self.directory':
            self.url = self.directory.replace(self.file_base, self.web_base,1)
        self.__dict__[name] = value

#####################
# Create Index Page #
#####################
    def create_index(self):
        assert self.page
        assert self.directory

        #! don't like this most_recent nonsense
        self.page.create(self.files, self.directory + self.index, \
              self.most_recent and self.most_recent or './../../recent/')

##########################
# Add a File to Archives #
##########################
    def add_archive(self, archive_file, source_dir):
        plan = archive_file.structure
        path = self.directory + archive_file.archive_name() + self.index

        self.files.append(archive_file)
        self._store_archive(archive_file, source_dir, plan=plan)
        self.last = archive_file
        self.last.path = path
        self.last.url = path.replace(self.file_base, self.web_base,1)
        try:
            shutil.copyfile(archive_file.index_path, path)
        except IOError, msg:
            self.note("Unable to copy archive index:", 'error')
            self.note("  %s  -->\n  %s"%(archive_file.index_path,path),'error')
            self.note(msg,'error')

##########################
# Store File Recursively #
##########################
    def _store_archive(self,archive_file,source_dir,dest_subdir=None,plan=None):
        # source always absolute, dest always relative
        assert self.directory
        assert archive_file.directory

        dest_dir = self.directory + archive_file.archive_name() + \
                   (dest_subdir and str(dest_subdir) or '')

        # Will only create one more than existing
        if not os.access(dest_dir,os.F_OK):
            try:
                os.mkdir(dest_dir)
            except OSError, msg:
                self.note("Failed to create directory %s" % dest_dir, 'error')
                self.note(msg, 'error')
                sys.exit(2)

        for item in plan:
            assert type(item) == str
            assert type(plan[item]) in (dict, bool, type(None))

            # Directory
            if type(plan[item]) == dict:
                self._store_archive(archive_file, source_dir + item, \
                                    item, plan[item])
            # File
            else:
                try:
                    shutil.copyfile(source_dir + item, dest_dir + item)
                except IOError, msg:
                    self.note("Unable to copy structure-implied file:", 'error')
                    self.note("  %s  -->\n  %s" % \
                         (source_dir+item, dest_dir+item), 'error')
                    self.note(msg, 'error')


#--------------------#
######################
# Archive Index Page #
######################
#--------------------#
class NoxArchiveIndex:
    bg_img = "bgimage.jpg"

    # javascript / refresh
    reveal_func = "reveal"
    collapse_img = "collapsed.jpg"
    collapsed_class = "collapsed"
    ellipsis_class = "ellipsis"
    collapse_delay = .1   # seconds
    refresh = 30    # seconds

    def __init__(self,css):
        # stylesheeting
        self.css = css   # 'http://[host].nicira.com/[webdir]/results.css'
                         # could go with relative path here?
                         # This will likely be changed to not ^^^^^^^

    def create(self, files, path, recent):
        page = []
        page.append('<html>\n')
        page.append(self._head())
        page.append(self._body(files, relative_path(path,recent)))
        page.append('</html>')

        index = open(path,'w')
        index.write("\n".join(page))

    def _head(self):
        section = []
        section.append('<head>')
        section.append(self._head_style())
        section.append(self._javascripts())
        section.append('</head>\n')
        return "\n".join(section)

    def _javascripts(self):
        js = []
        js.append('<script type="text/javascript">')
        js.append(self._collapse_js())
        js.append('//-->\n</script>')
        js.append(self._no_js())
        return "\n".join(js)

    def _body(self, files, recent):
        section = []
        section.append('<body background="%s">' % (self.bg_img))
        section.append(self.header_link(recent, 'Most Recent'))
        section.append(self._archive_list(files))
        section.append('</body>\n')
        return "\n".join(section)

    def _archive_list(self, files):
        listing = []
        listing.append('<h1>Build Archive</h1>')
        listing.append('<ol>')

        consecutive_fails = 0
        for file in files:
            if file.success == False:
                consecutive_fails += 1
            else:
            # Pass after repeated fails
                if consecutive_fails > 1:
                    listing.append(self._collapse_end())
                consecutive_fails = 0

            if consecutive_fails == 2:
            # First of repeated fails
                listing.append(self._collapse_begin(file))
            listing.append(file.archive_html())

        # Close ellipsis if ending in fail
        if consecutive_fails > 1:
            listing.append(self._collapse_end())

        listing.append('</ol>')
        return "\n".join(listing)


#####################
#### Texty Stuff ####
#####################

    def _head_style(self):
        return \
'''\
<title>Build Archive Index</title>
<link rel="stylesheet" type="text/css" href="%s">
<meta http-equiv="Pragma" content="no-cache">
<meta http-equiv="Expires" content="-1">
''' % (self.css)

    def _collapse_js(self):
        return \
'''\
if (window.setTimeout)
{
var iTimeout = window.setTimeout(\
'if (location.reload) location.reload();', %d);
window.on_load = init();
}

function init()
{
setTimeout('collapse()',%d)
}

function collapse()
{
var all = document.getElementsByTagName('div')
for (var i=0; i<all.length; i++)
{
    if(all[i].className == "ellipsis")
    {
        all[i].style.display='block'
    }
    else if(all[i].className == "collapsed")
    {
        all[i].style.display='none'
    }
}
}

function reveal(self,element)
{
document.getElementById(element).style.display='block';
self.style.display='none';
if (window.clearTimeout) window.clearTimeout(iTimeout);
if (window.setTimeout) window.setTimeout(\
'if (location.reload) location.reload();', %d);
return true;
}
''' % (self.refresh*1000, self.collapse_delay*1000, self.refresh*1000)

    def _no_js(self):
        return \
'''\
<noscript><meta http-equiv="Refresh" content="%d></noscript>
''' % (self.refresh)

    def header_link(self, relative_href, text):
        return \
'''\
<center><table><tr>
<td><marquee direction="right" loop=2 behavior="slide" scrolldelay=100\
 scrollamount=2>----&gt;&nbsp;</marquee></td>
<td><a href="%s"><tt>%s</tt></a></td>
<td><marquee direction="left" loop=2 behavior="slide" scrolldelay=100\
 scrollamount=2>&nbsp;&lt;----</marquee></td>
</table></center>
<hr>
''' % (relative_href, text)

    def _collapse_begin(self, first_hidden):
        return \
'''\
<div class="%s"><li class="%s" onclick="%s(this,'%s')"><img src="%s"></li></div>
<div class="%s" id="%s">\
'''%(self.ellipsis_class, "fail", self.reveal_func, \
     first_hidden.archive_name()[:-1], self.collapse_img, \
     self.collapsed_class, first_hidden.archive_name()[:-1])

    def _collapse_end(self):
        return \
'''\
</div>
'''
