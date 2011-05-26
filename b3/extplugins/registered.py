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
# 26-05-2011 - 1.0.3 - SGT
# Check connected players in case we missed the event

__version__ = '1.0.3'
__author__  = 'SGT'

import b3, threading, time
import b3.plugin
import b3.events
import b3.cron

#--------------------------------------------------------------------------------------------------
class RegisteredPlugin(b3.plugin.Plugin):
    requiresConfigFile = False
   
    _warn = 5
    _cronTab = None
    
    def onStartup(self):
        self.registerEvent(b3.events.EVT_CLIENT_AUTH)
        if self._cronTab:
            self.console.cron - self._cronTab
        self._cronTab = b3.cron.PluginCronTab(self, self.process_connected, minute='*/1')
        self.console.cron + self._cronTab
        
    def onEvent(self,  event):
        if event.type == b3.events.EVT_CLIENT_AUTH:
            self.onConnect(event)
    
    def onConnect(self, event):
        if not event.client or event.client.pbid == 'WORLD':
            return
        self.process_connect_event(event.client)
        
    def process_connect_event(self, client):
        self.debug("Client connected")
        client.setvar(self, 'regctrl', True)
        if client.maxLevel > 0:
            return
        if client.connections <= 20:
            self.console.write('mute %s' % (client.cid))
            t = threading.Timer(20, self._client_connected, (client,))
            t.start()
        else:
            client.kick('Not registered', silent=True)

    def process_connected(self):
        clients = self.console.clients.getList()
        for client in clients:
            if not client.isvar(self, 'regctrl'):
                self.process_connect_event(client)
                    
    def _client_connected(self, client):
        if client.connected:
            # this requires poweradmin to keep forced
            client.setvar(self, 'paforced', 'spectator')
            self.console.write('forceteam %s %s' % (client.cid, 'spectator'))
            for i in range(0,self._warn):
                client.message("^5%s ^7tu id es ^2%s^7. Pedi tu registro en www.codwar.com.ar" % (client.name, client.id))
                time.sleep(3)
                self.console.write('forceteam %s %s' % (client.cid, 'spectator'))
	    if client.connections < 3:
                client.kick('Not registered', silent=True)
            else:
                client.tempban('Not registered', '', 5, None)

if __name__ == '__main__':
    from b3.fake import fakeConsole
    from b3.fake import FakeClient, superadmin
    import time
    
    # first time user
    user0 = FakeClient(fakeConsole, name="New User", exactName="Joe", guid="1234", groupBits=0, team=b3.TEAM_RED)
    user0.connections = 0
    
    # second time user
    user1 = FakeClient(fakeConsole, name="New User Again", exactName="Joe", guid="12384", groupBits=0, team=b3.TEAM_RED)
    user1.connections = 1
    # registered user
    user2 = FakeClient(fakeConsole, name="Registered User", exactName="Joe", guid="1235", groupBits=1, team=b3.TEAM_RED)
    # regular user
    user3 = FakeClient(fakeConsole, name="Regular User", exactName="Joe", guid="12365", groupBits=2, team=b3.TEAM_RED)
       
    
    p = RegisteredPlugin(fakeConsole)
    p._warn = 1
    p.onStartup()
    time.sleep(2)
    
    superadmin.connects(cid=0)
    time.sleep(5)
    user0.connects(cid=1)
    time.sleep(5)
    user1.connects(cid=2)
    time.sleep(5)
    user2.connects(cid=3)
    time.sleep(5)
    user3.connects(cid=4)
