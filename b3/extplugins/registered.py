# Registered Users Only Plugin
# Copyright (C) 2011 Sergio Gabriel Teves
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
# 05-05-2011 - 1.0.0 - SGT
# Initial version

__version__ = '1.0.0'
__author__  = 'SGT'

import b3, threading, time
import b3.plugin
import b3.events

#--------------------------------------------------------------------------------------------------
class RegisteredPlugin(b3.plugin.Plugin):
    requiresConfigFile = False
    
    def onStartup(self):
        self.registerEvent(b3.events.EVT_CLIENT_AUTH)
        
    def onEvent(self,  event):
        if event.type == b3.events.EVT_CLIENT_AUTH:
            self.process_connect_event(event)
            
    def process_connect_event(self, event):
        self.debug("Client connected")
        if not event.client or event.client.pbid == 'WORLD':
            return
        
        client = event.client
        if client.maxLevel > 0:
            return
        if client.connections == 1:
            t = threading.Timer(30, self._client_connected, (client,))
            t.start()
        else:
            client.kick('Not registered')
    
    def _client_connected(self, client):
        if client.connected:
            # this requires poweradmin to keep forced
            client.setvar(self, 'paforced', 'spectator')
            self.console.write('forceteam %s %s' % (client.cid, 'spectator'))
            for i in range(0,15):
                client.message("^5%s ^7tu id es ^2%s^7. Pedi tu registro en www.codwar.com.ar" % (client.name, client.id))
                time.sleep(1)
                self.console.write('forceteam %s %s' % (client.cid, 'spectator'))
            client.kick('Not registered')

if __name__ == '__main__':
    from b3.fake import fakeConsole
    from b3.fake import FakeClient, superadmin
    import time
    
    # first time user
    user0 = FakeClient(fakeConsole, name="Joe0", exactName="Joe", guid="1234", groupBits=0, team=b3.TEAM_RED)
    user0.connections = 0
    
    # second time user
    user1 = FakeClient(fakeConsole, name="Joe1", exactName="Joe", guid="12384", groupBits=0, team=b3.TEAM_RED)
    user1.connections = 1
    # registered user
    user2 = FakeClient(fakeConsole, name="Joe2", exactName="Joe", guid="1235", groupBits=1, team=b3.TEAM_RED)
    # regular user
    user2 = FakeClient(fakeConsole, name="Joe2", exactName="Joe", guid="1235", groupBits=4, team=b3.TEAM_RED)
       
    
    p = RegisteredPlugin(fakeConsole)
    p.onStartup()
    time.sleep(2)
    
    superadmin.connects(cid=0)
    time.sleep(2)
    user0.connects(cid=1)
    time.sleep(2)
    user1.connects(cid=2)
    time.sleep(2)
    user2.connects(cid=3)
    time.sleep(2)
