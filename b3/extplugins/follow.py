# BigBrotherBot(B3) (www.bigbrotherbot.com)
# Plugin for following suspicious users
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
# 01-16-2010 - 1.0.0
# Initial version
# 03-09-2010 - 1.1.0
# Add followinfo command
# Add optional reason field
# Removed name change event. Now the full client object is stored
# 04-22-2010 - 1.1.1
# Changed notification message and show admin name
# message can be changed through conf file
# 07-26-2010 - 1.1.2
# Do sync on a thread

__version__ = '1.1.2'
__author__  = 'SGT'

import b3, threading
import b3.plugin
from b3 import clients
import b3.cron
import time

class FollowPlugin(b3.plugin.Plugin):
    _adminPlugin = None
    _following = {}

    _SELECT_QUERY = "SELECT client_id, reason, admin_id FROM following WHERE client_id = %s"
    _ADD_QUERY = "INSERT INTO following (client_id, admin_id, time_add, reason) VALUES ('%s','%s',%d,'%s')"
    _DEL_QUERY = "DELETE FROM following WHERE client_id = %s"
    _LIST_QUERY = "SELECT client_id FROM following"
    _NOTIFY_MSG = "^1WARNING: ^1%(client_name)s ^7[^2@%(client_id)s^7] ^7has been placed under watch by ^4%(admin_name)s ^7[^2@%(admin_id)s^7] ^7for: ^5%(reason)s"
    _DEFAULT_REASON = "cheating"
    
    def onStartup(self):
        self.registerEvent(b3.events.EVT_CLIENT_AUTH)
        self.registerEvent(b3.events.EVT_CLIENT_DISCONNECT)
        self.registerEvent(b3.events.EVT_CLIENT_BAN)
        self.registerEvent(b3.events.EVT_CLIENT_BAN_TEMP)
        self.registerEvent(b3.events.EVT_GAME_ROUND_START)

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

        self._twitter = self.console.getPlugin('twity')
        if not self._twitter:
            self.warning("Twitter plugin not avaiable.")
            
        self._mod_level = self.config.getint('settings', 'mod_level')
        self._admin_level = self.config.getint('settings', 'admin_level')
        try:
            self._twit_event = self.config.getboolen('settings','twit_connect')
        except:
            self._twit_event = False
            
        self.createEvent('EVT_FOLLOW_CONNECTED', 'Suspicious User Connected.')
        
        self._adminPlugin.registerCommand(self, 'follow', self._admin_level, self.cmd_addfollow,'ff')
        self._adminPlugin.registerCommand(self, 'unfollow', self._admin_level, self.cmd_delfollow,'uf')
        self._adminPlugin.registerCommand(self, 'listfollow', self._mod_level, self.cmd_listfollow,'lif')
        self._adminPlugin.registerCommand(self, 'checkfollow', self._mod_level, self.cmd_checkfollow,'ckf')
        self._adminPlugin.registerCommand(self, 'syncfollow', self._admin_level, self.cmd_sync, None)
        self._adminPlugin.registerCommand(self, 'followinfo', self._mod_level, self.cmd_followinfo, 'fi')

        try:
            self._NOTIFY_MSG = self.config.get('settings','message')
        except:
            self.debug("Using default message")
            
    def onEvent(self,  event):
        if event.type == b3.events.EVT_CLIENT_AUTH:
            self.process_connect_event(event)
        elif event.type == b3.events.EVT_CLIENT_DISCONNECT:
            self.process_disconnect_event(event)
        elif event.type == b3.events.EVT_CLIENT_BAN or event.type == b3.events.EVT_CLIENT_BAN_TEMP:
            self.process_ban(event)
        elif event.type == b3.events.EVT_GAME_ROUND_START:
            b = threading.Timer(10, self.sync_list, (event,))
            b.start()
            
    def sync_list(self, event):
        self._following = {}
        self.debug("Syncing list")
        clients = self.console.clients.getList()
        for c in clients:
            self._add_list(c)
        
    def process_connect_event(self, event):
        self.debug("Client connected")
        if not event.client or event.client.pbid == 'WORLD':
            return            
        
        self.debug("Put on connected queue")
        t = threading.Timer(30, self._client_connected, (event.client,))
        t.start()
    
    def _client_connected(self, client):
        if client.connected:
            if client.maxLevel < self._mod_level:
                if self._add_list(client):
                    self.console.queueEvent(self.console.getEvent('EVT_FOLLOW_CONNECTED', (client.var(self, 'follow_data').value,), self.client))
                    self.notify_admins(client)
                    self._event_notify(client)
            else:
                self.warn_user(client)

    def _event_notify(self, client):
        if self._twit_event and self._twitter:
            message = "WARNING: Suspicious user is playing."
            self._twitter.post_update(message)
        
    def notify_admins(self, client):
        self.debug("Notify connected admins")
        clients = self.console.clients.getList()
        for c in clients:
            if c.maxLevel >= self._mod_level:
                self._show_message(client, c)
                time.sleep(0.5)
    
    def _show_message(self, client, player):
        data = {'client_name': player.name,
                'client_id': player.id,
                'admin_name': player.var(self, 'follow_admin').value.name,
                'admin_id': player.var(self, 'follow_admin').value.id,
                'reason': player.var(self, 'follow_reason').value}
        client.message(self._NOTIFY_MSG % data)
        
    def process_ban(self, event):
        if event.data.find("banned by") <> -1:
            self.debug("Cleaning follow database")
            cursor = self.console.storage.query(self._DEL_QUERY % event.client.id)
            cursor.close()
            
    def process_disconnect_event(self, event):
        self.debug("Process disconnect event")
        cid = event.data
        if self._following.has_key(cid):
            self.debug("Client %s disconnected" % (self._following[cid]))
            del self._following[cid]
            
    def warn_user(self, client):
        self.debug("Notify watched users")
        for c in self._following.values():
            self._show_message(client, c)
            time.sleep(0.5)
        
    def _add_list(self, client):
        if not self._following.has_key(client.id):
            self.debug("Lookup for %s" % client.name)
            cursor = self.console.storage.query(self._SELECT_QUERY % client.id)
            if cursor.rowcount > 0:
                r = cursor.getRow()
                self.debug("Client %s found in list." % client.name)
                if r['reason']:
                    reason = r['reason']
                else:
                    reason = self._DEFAULT_REASON
                admin = self._adminPlugin.findClientPrompt("@%s" % r['admin_id'], client)
                client.setvar(self, 'follow_reason', reason)
                client.setvar(self, 'follow_admin', admin)
                client.setvar(self, 'follow_data', {'reason': reason, 'admin': admin})
                self._following[client.id] = client
                return True
            cursor.close()
        return False
        
    def cmd_checkfollow(self, data, client, cmd=None):
        """\
        list connected users being followed
        """        
        client.message("^7Checking...")
        self.warn_user(client)
        client.message("^7Check complete.")

    def cmd_sync(self, data, client, cmd=None):
        """\
        sync connected players
        """        
        client.message("^7Syncing...")
        self.sync_list(None)
        client.message("^7Synced.")
        
    def cmd_listfollow(self, data, client, cmd=None):
        """\
        list followed users
        """         
        cursor = self.console.storage.query(self._LIST_QUERY)
        if cursor.rowcount == 0:
            client.message("^7The list is empty.")
            cursor.close()
            return False

        names = []
        while not cursor.EOF:
            r = cursor.getRow()
            c = self.console.storage.getClientsMatching({ 'id' : r['client_id'] })
            if c:
                names.append("^7[^2@%s^7] %s" % (c[0].id,c[0].name))
            else:
                self.error("Not found client matching id %s" % r['client_id'])
            cursor.moveNext()
        cursor.close()
        client.message(', '.join(names))

    def cmd_addfollow(self, data, client, cmd=None):
        """\
        <name> - add user to the follow list
        <reason> - optional
        """        
        m = self._adminPlugin.parseUserCmd(data)
        if not m:
            client.message('^7Invalid parameters')
            return False

        if len(m)==2:
            cid, reason = m
        elif len(m)==1:
            cid = m[0]
            reason = ''
        else:
            client.message('^7Invalid parameters')
            return False
        sclient = self._adminPlugin.findClientPrompt(cid, client)
        
        if not sclient:
            return False
            
        cursor = self.console.storage.query(self._SELECT_QUERY % sclient.id)
        if cursor.rowcount == 0:
            cursor2 = self.console.storage.query(self._ADD_QUERY % (sclient.id, client.id, self.console.time(), reason))
            cursor2.close()
            self.debug("User added to watch list")
            client.message("^7The user has been added to the watch list.")
        else:
            self.debug("User already in watch list")
            client.message("^7User already exists in watch list.")
        cursor.close()
        self.sync_list(None)
        
    def cmd_delfollow(self, data, client, cmd=None):
        """\
        <name> - remove user from the follow list
        """        
        m = self._adminPlugin.parseUserCmd(data)
        if not m:
            client.message('^7Invalid parameters')
            return False

        sclient = self._adminPlugin.findClientPrompt(m[0], client)
        cursor = self.console.storage.query(self._DEL_QUERY % sclient.id)
        cursor.close()
        self.debug("User removed from watch list")
        client.message("^7User removed from the watch list.")
        self.sync_list(None)

    def cmd_followinfo(self, data, client, cmd=None):
        """\
        <name> - remove user from the follow list
        """
        m = self._adminPlugin.parseUserCmd(data)
        if not m:
            client.message('^7Invalid parameters')
            return False
        
        sclient = self._adminPlugin.findClientPrompt(m[0], client)
        cursor = self.console.storage.query(self._SELECT_QUERY % sclient.id)
        
        if cursor.rowcount > 0:
            r = cursor.getRow()
            admin = self._adminPlugin.findClientPrompt("@" % r['admin_id'], client)
            client.message('%s was added by %s for %s' % (sclient.name, admin.name, r['reason']))
        else:
            client.message('No follow info for %s' % sclient.name)
        cursor.close()

if __name__ == '__main__':
    from b3.fake import fakeConsole
    from b3.fake import superadmin as user
    
    p = FollowPlugin(fakeConsole, '@b3/extplugins/conf/follow.xml')
    p.onStartup()
    
    user.authed = True
    user.says('!listfollow')
    time.sleep(2)
