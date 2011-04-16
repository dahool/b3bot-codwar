# BigBrotherBot(B3) (www.bigbrotherbot.com)
# Plugin for following suspicious users
# Copyright (C) 2011 Sergio Gabriel Teves
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
# 03-16-2011 - 1.0.0
# Initial version
# 03-18-2011 - 1.0.1
# If user is online, start slapping
# 03-19-2011 - 1.0.2
# Limit slap time
# Add nuke and temp ban
# 03-29-2011 - 1.0.3
# Mix nuke with slap
# Add mute
# 04-07-2011 - 1.0.4
# Force to team if spec

__version__ = '1.0.5'
__author__  = 'SGT'

import b3, threading, thread
import b3.plugin
from b3 import clients
import time
import datetime
import random

class AutoslapPlugin(b3.plugin.Plugin):
    _adminPlugin = None

    _SELECT_QUERY = "SELECT client_id FROM tb_autoslap WHERE client_id = %s"
    _ADD_QUERY = "INSERT INTO tb_autoslap (client_id, admin_id, time_add, reason) VALUES ('%s','%s',%d,'%s')"
    _DEL_QUERY = "DELETE FROM tb_autoslap WHERE client_id = %s"
    _LIST_QUERY = "SELECT client_id, reason FROM tb_autoslap ORDER BY time_add DESC"
    
    _wait = 1
    _slaptime = 2
    _nuke = True
    _ban = 5 # 5 minutes
    
    def onStartup(self):
        self.registerEvent(b3.events.EVT_CLIENT_AUTH)
        
    def onLoadConfig(self):
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

        level_add = self.config.getint('commands', 'add')
        level_del = self.config.getint('commands', 'del')
        level_list = self.config.getint('commands', 'list')
        
        try:
            self._wait = self.config.getint('settings','wait')
        except:
            pass
        try:
            self._slaptime = self.config.getint('settings', 'slaptime')
        except:
            pass
        try:
            self._nuke = self.config.getboolean('settings', 'nuke')
        except:
            pass
        try:
            self._ban = self.config.getDuration('settings','tempban')
        except:
            pass
        
        self._adminPlugin.registerCommand(self, 'addslap', level_add, self.cmd_addfollow)
        self._adminPlugin.registerCommand(self, 'delslap', level_del, self.cmd_delfollow)
        self._adminPlugin.registerCommand(self, 'listslap', level_list, self.cmd_listfollow)

    def onEvent(self,  event):
        if event.type == b3.events.EVT_CLIENT_AUTH:
            self.process_connect_event(event)
            
    def process_connect_event(self, event):
        self.debug("Client connected")
        if not event.client or event.client.pbid == 'WORLD':
            return            
        
        self.debug("Put on connected queue")
        t = threading.Timer(30, self._client_connected, (event.client,))
        t.start()
    
    def _client_connected(self, client):
        if client.connected:
            if client.maxLevel < self._admin_level:
                if self._is_flagged(client):
                    self.debug("Client %s flagged." % client.name)
		    client.notice("not welcome on this server", None)
                    thread.start_new_thread(self._slap_client, (client,))

    def doslap(self, client):
	self.console.write('slap %s' % (client.cid))

    def donuke(self, client):
	self.console.write('nuke %s' % (client.cid))

    def _slap_client(self, client):
        self.debug('Auto slap waiting')
        time.sleep(self._wait)
        self.debug('Performing auto slap')
        client.message(self.getMessage('not_welcome', {'name': client.name}))
        slapEnd = datetime.datetime.now() + datetime.timedelta(minutes=self._slaptime)
        self.console.write('mute %s' % (client.cid))
        
        while client.connected and datetime.datetime.now() <= slapEnd:
            self.debug('Perform slap')
	    self.doslap(client)
            if self._nuke:
                time.sleep(1)
                self.debug('Nuke player')
		self.donuke(client)
	    else:
		time.sleep(1)
            time.sleep(1)
            client.message(self.getMessage('not_welcome', {'name': client.name}))
            self.moveFromSpec(client)
                
        if client.connected:
            if self._ban:
                self.debug('Ban player')
                client.tempban('Not welcome on this server', '', self._ban, None)
            else:
                self.debug('Kick player')
                client.kick('Not welcome on this server')
        self.debug('Autoslap done.')
    
    def moveFromSpec(self, client):
        if b3.TEAM_SPEC == client.team:
            self.debug('Client moved from spec')
            self.console.write('forceteam %s %s' % (client.cid, random.choice(['blue','red'])))
        
    def _is_flagged(self, client):
        cursor = self.console.storage.query(self._SELECT_QUERY % client.id)
        return cursor.rowcount > 0
        
    def cmd_listfollow(self, data, client, cmd=None):
        """\
        list autoslap users
        """         
        cursor = self.console.storage.query(self._LIST_QUERY)
        if cursor.rowcount == 0:
            client.message("^7The list is empty.")
            return False

        names = []
        while not cursor.EOF:
            r = cursor.getRow()
            c = self.console.storage.getClientsMatching({ 'id' : r['client_id'] })
            if c:
                names.append("^7[^2@%s^7] %s: %s" % (c[0].id,c[0].name, r['reason']))
            else:
                self.error("Not found client matching id %s" % r['client_id'])
            cursor.moveNext()
        client.message(', '.join(names))

    def cmd_addfollow(self, data, client, cmd=None):
        """\
        <name> - add user to the autoslap list
        <reason> - reason
        """        
        m = self._adminPlugin.parseUserCmd(data)
        if not m:
            client.message('^7Invalid parameters')
            return False

        if len(m)==2:
            cid, reason = m
        else:
            client.message('^7Invalid parameters')
            return False
        sclient = self._adminPlugin.findClientPrompt(cid, client)
        
        if not sclient:
            return False
        
        if sclient.maxLevel >= self._admin_level and client.maxLevel < 90:
            client.message('^7Yeah right. Such a n00b')
            return False
                
        cursor = self.console.storage.query(self._SELECT_QUERY % sclient.id)
        if cursor.rowcount == 0:
            cursor2 = self.console.storage.query(self._ADD_QUERY % (sclient.id, client.id, self.console.time(), reason))
            self.debug("User added to autoslap list")
            client.message("^7%s has been added to the autoslap list." % sclient.name)
            if sclient.connected:
                thread.start_new_thread(self._slap_client, (sclient,))
        else:
            self.debug("User already in autoslap list")
            client.message("^%s already exists in autoslap list." % sclient.name)
        
    def cmd_delfollow(self, data, client, cmd=None):
        """\
        <name> - remove user from the autoslap list
        """        
        m = self._adminPlugin.parseUserCmd(data)
        if not m:
            client.message('^7Invalid parameters')
            return False

        sclient = self._adminPlugin.findClientPrompt(m[0], client)
        cursor = self.console.storage.query(self._DEL_QUERY % sclient.id)
        
        if not sclient:
            return
        
        self.debug("User removed from autoslap list")
        client.message("^7%s removed from autoslap list." % sclient.name)


if __name__ == '__main__':
    from b3.fake import fakeConsole
    from b3.fake import superadmin as user
    
    p = AutoslapPlugin(fakeConsole, '/local/codwar/bot/b3/extplugins/conf/autoslap.xml')
    p.onStartup()
    
    user.authed = True
    user.says('!listslap')
    time.sleep(2) 

    p._slap_client(user)
