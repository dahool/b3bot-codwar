#
# TwityPlugin
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
# 01/18/2010 - SGT
# remove format mark
# 01/16/2010 - SGT
# add unban event
# 01/15/2010 - 1.0.0 - SGT

__version__ = '1.0.3'
__author__  = 'SGT'

import twitter as tw
import re
import time

import b3, threading, time
import b3.events
import b3.plugin
import poweradminurt as padmin

#--------------------------------------------------------------------------------------------------
class TwityPlugin(b3.plugin.Plugin): 
    
    def onStartup(self):
        self.submark = re.compile('(\^\d)')
        self._adminPlugin = self.console.getPlugin('admin')
        self.servername = self.console.getCvar("sv_hostname").getString()
        self.api = None

        self.registerEvent(b3.events.EVT_CLIENT_BAN)
        self.registerEvent(b3.events.EVT_CLIENT_BAN_TEMP)
        self.registerEvent(b3.events.EVT_CLIENT_UNBAN)
        self.registerEvent(b3.events.EVT_CLIENT_PUBLIC)

        self.post_update("Started")

    def onLoadConfig(self):
        self._username = self.config.get('settings','username')
        self._password = self.config.get('settings','password')
      
    def onEvent(self, event):
        if (event.type == b3.events.EVT_CLIENT_BAN or
            event.type == b3.events.EVT_CLIENT_BAN_TEMP):
            self._ban_event(event)
        elif event.type == b3.events.EVT_CLIENT_PUBLIC:
            self._public_event(event)
        elif event.type == b3.events.EVT_CLIENT_UNBAN:
            self._unban_event(event)
        return
      
    def post_update(self, message):
        message = "(%s) %s" % (self.servername,message)
        message = self.submark.sub('',message)
        self.debug(message)
        p = threading.Thread(target=self._twitthis, args=(message,))
        p.start()
        
    def _get_connection(self):
        # try to connect two times before raise error
        for i in range(0,2):
            try:
                self.debug("Get Twitter connection [%d]" % i)
                self.api = tw.Api(self._username, self._password)
            except:
                time.sleep(1)
                self.error(e)
            else:
                return True
        return False
        
    def _twitthis(self, message):
        if not self.api:
            if not self._get_connection():
                return
        for i in range(0,2):
            try:
                self.debug("Post update [%d]" % i)
                self.api.PostUpdate(message)
                self.debug("Message posted!")
                return
            except Exception, e:
                time.sleep(2)
                self.error(e)

    def _unban_event(self, event):
        message = "%s [%s] was unbanned by %s [%s]" % (event.client.name, event.client.id,event.data.name, event.data.id)
        self.post_update(message)
    
    def _ban_event(self, event):
        if event.data.find("banned by") <> -1:
            self.post_update(event.data)

    def _public_event(self, event):
        if event.data == "":
            msg = "Server set to PUBLIC by %s" % event.client.name
        else:
            msg = "Server going to PRIVATE by %s [%s]" % (event.client.name,event.data)
        self.post_update(msg)
