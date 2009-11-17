#!/usr/bin/python
#
# 3/8/08 TARP
# Begin extracting webpage creation from builder.py
# Finished extraction, minor tweaks for reintegration
#

###########
# Imports #
###########

import sys
import os
import pwd
import subprocess
import time
import platform

from utilities import *


class Summary:
    bg_img = "bgimage.jpg"
    gitweb_base="http://repo.nicira.com/cgi-bin/gitweb.cgi?p=noxcore/.git;a=commit;h="
    refresh = 30
    rev_len = 10  # size of revision-displaying box in html
    file_base = '/var/www/'
    web_base = "http://%s.nicira.com/" % platform.uname()[1]

    def __init__(self, archive, result, logs, css):
        self.archive = archive
        self.result = result
        self.logs = logs
        self.css = css


    def create(self, path, archiving=False, incomplete=False):
        page = []
        page.append('<html>\n')
        page.append(self._head(archiving, incomplete))
        page.append(self._body(path, archiving, incomplete))
        page.append('</html>')

        # Make directory if not existing?
        index = open(path,'w')
        index.write("\n".join(page))

    def _head(self, archiving, incomplete):
        section = []
        section.append('<head>')
        section.append(\
'''\
<title>Build Result: %s</title>
<meta http-equiv="Refresh" content="%d">
<link rel="stylesheet" type="text/css" href="%s">\
''' % (self.result.result.title() + (incomplete and "ing..." or "ed"), \
       self.refresh, (archiving and "../" or "") + self.css))
        section.append('</head>\n')
        return "\n".join(section)

    def _body(self, path, archiving, incomplete):
        if self.archive:
            ar_link = self.archive.page.header_link
            ar_path = relative_path(path, self.archive.directory)
                

        section = []
        section.append('<body background="../%s">' % (self.bg_img))
        if self.archive and self.archive.files:
            if archiving:
                ar_path += "../" # fna
            section.append(ar_link(ar_path,'Archives'))
        section.append(self._body_title(incomplete))
        section.append(self._settings())
        section.append(self._sections(archiving, incomplete))
        section.append('</body>\n')
        return "\n".join(section)

    def _body_title(self, incomplete):
        return '<h1>Check-In Results: <b class="%s">%s</b></h1>' \
               % (self.result.result, self.result.result.upper() + \
                  (incomplete and "ING..." or "ED"))

    def _sections(self, archiving, incomplete):
        tests = []

        tests.append(self._sections_title(incomplete))
        tests.append('<ol>')
        for s in self.result.sections:
            tests.append(\
'<li class="%s"><b class="%s">%s (%d/%d)</b>:<tt>(%.2fs)</tt><ul>' \
    % (s.result, s.result, s.name, s.passed(), s.total(), s.duration()))
            tests.append(self._commands(s, archiving))
            tests.append('</ul></li>\n')
        tests.append('</ol>')
        return "\n".join(tests)

    def _sections_title(self, incomplete):
        r = self.result
        return \
'''\
<h2>Summary: <b class="%s"><small>(%d/%d Sections)</small></b><tt>\
(%.2fs</tt><small>%s</small><tt>)</tt></h2>\
''' %(r.result, r.passed(), r.total(), r.duration(), incomplete and '...' or '')


    def _commands(self, section, archiving):
        orders = []
        for c in section.commands:
            log = c.log
            if log:
                # Logged Command
                for prefix in self.logs:
                    log = log.replace(prefix,'',1)
                orders.append(\
'<li class="%s">%s <a class="%s" href="%s">%s</a> <tt>(%.2fs)</tt></li>' \
    % (c.result, c.name, c.result, log, log, c.duration))
            else:
                # Unlogged Command
                orders.append(\
'<li class="%s">%s</li>' \
    % (c.result, c.name))
        return "\n".join(orders)

    def _settings(self):
        r = self.result
        if r.error:
            error = r.error.replace("\n","<br>")
            error = \
'''\
</tr>
<tr><td colspan=2>
<h3>Error: <tt><b class="fail">%s</b></tt></h3>
''' % error
        else:
            error = ''
        return \
'''\
<table>
<tr><td colspan=2><h3>Author: <tt>%s &lt;%s&gt;</tt></h3></td></tr>
<tr><td><h3>User: <tt>%s on %s</tt></h3>
<h3>Revision: <tt><input type="text" size="%d" value="%s"readonly onClick=select()></tt></h3>
<h3>Time: <tt>%s</tt></h3>
<h3>Options: <tt>%s</tt></h3></td>
<td><h3>Nox: <tt>%s</tt></h3>
<h3>Git-Web: <tt><a href=%s>git-web commit</a></tt></h3>
<h3>Build: <tt>%s</tt></h3>
<h3>Commands: <tt>%s</tt></h3></td>%s
</tr></table>
''' % (r.author, r.email, r.user, r.machine, self.rev_len, r.commit, \
     r.time_readable, ", ".join(r.options), r.base_directory, \
     self.gitweb_base+r.commit, r.directory, ", ".join(r.commands), error)
