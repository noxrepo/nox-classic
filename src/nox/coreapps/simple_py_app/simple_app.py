# Copyright 2011 (C) Stanford University
# 
# This file is part of NOX.
# 
# NOX is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# NOX is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with NOX.  If not, see <http://www.gnu.org/licenses/>.
#

from nox.lib.core     import *
import logging

logger = logging.getLogger('nox.coreapps.simple_py_app.simple_app')

class simple_app(Component):
    """ \brief simple_app
    \ingroup noxcomponents
    
    @author
    @date 
    """
    def __init__(self, ctxt):
        """\brief Initialize
        @param ctxt context
        """
        Component.__init__(self, ctxt)
        logger.debug("Initialized")
        
    def install(self):
        """\brief Install
        """
        logger.debug("Installed")

    def getInterface(self):
        """\brief Get interface
        """
        return str(simple_app)

def getFactory():
    class Factory:
        def instance(self, ctxt):
            return simple_app(ctxt)

    return Factory()
