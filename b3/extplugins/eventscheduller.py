# BigBrotherBot(B3) (www.bigbrotherbot.com)
# Plugin for schedulling events
# Copyright (C) 2010 Sergio Gabriel Teves
# 
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
# 01/28/2010
# Initial version

__version__ = '1.0.0'
__author__  = 'SGT'

import b3, threading
import b3.plugin
from b3 import clients
import b3.cron
import time

class EventschedullerPlugin(b3.plugin.Plugin):
    _adminPlugin = None
    _events = {}
    
    def startup(self):
        """\
        Initialize plugin settings
        """
        # get the plugin so we can register commands
        self._adminPlugin = self.console.getPlugin('admin')
        if not self._adminPlugin:
            # something is wrong, can't start without admin plugin
            self.error('Could not find admin plugin')
            return False
        
        self._admin_level = self.config.getint('settings', 'admin_level')

        self._adminPlugin.registerCommand(self, 'listevents', self._admin_level, self.cmd_listevents,None)
        self._adminPlugin.registerCommand(self, 'clearevents', self._admin_level,self.cmd_clearevents,None)
        self.registerEvent(b3.events.EVT_GAME_ROUND_START)
        self.registerEvent(b3.events.EVT_GAME_ROUND_END)
        self.registerEvent(b3.events.EVT_GAME_WARMUP)
        self.registerEvent(b3.events.EVT_GAME_EXIT)
        self.registerEvent(b3.events.EVT_CLIENT_PUBLIC)

    def onEvent(self,  event):
        if self._events.has_key(event.type):
            self.debug("Processing event %s" % event.type)
            process_event(event)
            
    def process_event(self, event):
        events = self._events[event.type]
        for ev in events:
            #self.console.write(ev)
            ev()
            time.sleep(1)
        del self._events[event.type]

    def add_event(self, type, cmd):
        if not self._events.has_key(type):
            self._events[type] = []
        self._events[type].append(cmd)
    
    def cmd_clearevents(self, data, client, cmd=None):
        self._events = {}
        client.message("Events cleared")
        
    def cmd_listevents(self, data, client, cmd=None):
        """\
        list pending events
        """ 
        client.message("^7Registered events...")
        for k,v in self._events.items():
            client.message("^7%s: %s" % (k,";".join(v.__doc__.strip())))
            time.sleep(1)
