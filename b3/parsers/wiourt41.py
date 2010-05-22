#
# BigBrotherBot(B3) (www.bigbrotherbot.com)
# iourt parser extend for survivor winner catch
# Copyright (C) 2010 Sergio Gabriel Teves
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
# 2010-05-12 - Initial version

__author__  = 'SGT'
__version__ = '1.0.0'

import b3
import b3.events
import b3.parsers.iourt41

class Wiourt41Parser(b3.parsers.iourt41.Iourt41Parser):
    
    def OnSurvivorWinner(self, action, data, match=None):
        return b3.events.Event(b3.events.EVT_SURVIVOR_WIN, data)  
