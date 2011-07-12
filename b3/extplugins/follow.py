# BigBrotherBot(B3) (www.bigbrotherbot.com)
# Plugin for following suspicious users
# Copyright (C) 2010-2011 Sergio Gabriel Teves
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
# 01-16-2010 - 1.0.0 - SGT
# Initial version
# 03-09-2010 - 1.1.0 - SGT
# Add followinfo command
# Add optional reason field
# Removed name change event. Now the full client object is stored
# 04-22-2010 - 1.1.1 - SGT
# Changed notification message and show admin name
# message can be changed through conf file
# 07-26-2010 - 1.1.2 - SGT
# Do sync on a thread
# 07-31-2010 - 1.1.3 - SGT
# Add option to disable remove record when banned
# 01-25-2011 - 1.1.4 - SGT
# Add option to use twitter
# Fix minor error in followinfo
# 05-04-2011 - 1.1.5 - SGT
# Fix error in show message when no admin is set (added through web interface)
# 07-11-2011 - 1.1.6 - Freelander
# Slightly refactored the code
# Added more debug lines
# Fixed false notification messages sent to followed players
# Suspected players properly added into/removed from '_following' list when connected/disconnected.
# Banned players properly removed from plugin's database table
# Better integration with aimbotdetector plugin when used together
# Fixed some bugs
# 07-12-2011 - 1.1.7 - SGT
# Do not remove user when ban is done by B3

__version__ = '1.1.7'
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
        
        self.createEvent('EVT_FOLLOW_CONNECTED', 'Suspicious User Connected.')

        self._twitter = self.console.getPlugin('twity')
        if not self._twitter:
            self.warning("Twitter plugin not avaiable.")
            
    def onLoadConfig(self):
        """\
        Initialize plugin settings
        """
        # get the plugin so we can register commands
        self._adminPlugin = self.console.getPlugin('admin')
        if not self._adminPlugin:
            # something is wrong, can't start without admin plugin
            self.error('Could not find admin plugin')
            self.disable()
            return False
            
        try:
            self._twit_event = self.config.getboolen('settings','twit_connect')
        except:
            self._twit_event = False
            
        # register our commands
        self._registerCommands()

        try:
            self._NOTIFY_LEVEL = self.config.getint('settings', 'notify_level')
        except:
            self._NOTIFY_LEVEL = 20
        try:
            self._NOTIFY_MSG = self.config.get('settings','message')
        except:
            self.debug("Using default message")
        try:
            self._REMOVE_BAN = self.config.getboolean('settings', 'remove_banned')
        except:
            self._REMOVE_BAN = True
        try:
            self._REMOVE_B3_BAN = self.config.getboolean('settings', 'remove_on_b3ban')
        except:
            self._REMOVE_B3_BAN = False
        try:
            self._MIN_PENALTY_DURATION = self.config.getint('settings', 'remove_ban_minduration')
        except:
            self._MIN_PENALTY_DURATION = 43829
            
    def getCmd(self, cmd):
        cmd = 'cmd_%s' % cmd
        if hasattr(self, cmd):
            func = getattr(self, cmd)
            return func
        return None

    def _registerCommands(self):
        # register our commands
        if 'commands' in self.config.sections():
            for cmd in self.config.options('commands'):
                level = self.config.get('commands', cmd)
                sp = cmd.split('-')
                alias = None
                if len(sp) == 2:
                    cmd, alias = sp
                func = self.getCmd(cmd)
                if func:
                    self._adminPlugin.registerCommand(self, cmd, level, func, alias)
            
    def onEvent(self,  event):
        if event.type == b3.events.EVT_CLIENT_AUTH:
            if  not event.client or \
                not event.client.id or \
                event.client.cid == None or \
                not event.client.connected or \
                event.client.pbid == 'WORLD' or \
                event.client.hide:
                return
            self.process_connect_event(event.client)
        elif event.type == b3.events.EVT_CLIENT_DISCONNECT:
            self.process_disconnect_event(event.data)
        elif event.type == b3.events.EVT_CLIENT_BAN or event.type == b3.events.EVT_CLIENT_BAN_TEMP:
            if self._REMOVE_BAN:
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
        
    def process_connect_event(self, client):
        self.debug("Client connected, processing connect event")
        self.debug("Client %s put on connected queue" % client.name)
        t = threading.Timer(30, self._client_connected, (client,))
        t.start()
    
    def _client_connected(self, client):
        if client.connected:
            if client.maxLevel < self._NOTIFY_LEVEL:
                if self._add_list(client):
                    self.console.queueEvent(self.console.getEvent('EVT_FOLLOW_CONNECTED', (client.var(self, 'follow_data').value,), client))
                    self.debug("Notifying online admins")
                    self.notify_online_admins(client)
                    self._event_notify(client)
            else:
                if len(self._following) > 0:
                    self.debug('Notifying connecting admin (admin: %s cid: %s)' % (client.name, client.cid))
                    self.notify_connecting_admin(client)
                else:
                    self.debug('No suspicious players online')

    def _event_notify(self, client):
        if self._twit_event and self._twitter:
            message = "WARNING: Suspicious user is playing."
            self._twitter.post_update(message)
        
    def notify_online_admins(self, suspect):
        clients = self.console.clients.getList()
        for player in clients:
            if player.maxLevel >= self._NOTIFY_LEVEL:
                self._show_message(player, suspect)
                time.sleep(1)

    def _show_message(self, admin, suspect):
        #prevent faulty messages to non-admin just in case
        if admin.maxLevel < self._NOTIFY_LEVEL:
            self.warning('WARNING: Oooops! Something wrong? %s shouldn\'t receive a message!' % admin.name)
            return False

        data = {'client_name': suspect.name,
                'client_id': suspect.id,
                'admin_name': suspect.var(self, 'follow_admin').value,
                'admin_id': suspect.var(self, 'follow_admin_id').value,
                'reason': suspect.var(self, 'follow_reason').value}

        admin.message(self._NOTIFY_MSG % data)
    
    def process_ban(self, event):
        client = event.client
        #check if banned client is in follow list
        self.debug('Client ban detected. Checking follow list DB table for %s' % client.name)
        cursor = self.console.storage.query(self._SELECT_QUERY % client.id)
        if cursor.rowcount > 0:
            # check if the ban is from an admin and is greater than 30 minutes (if not, it should be removed)
            penalty = client.lastBan
            if (penalty and (penalty.duration < 0 or penalty.duration > self._MIN_PENALTY_DURATION)
                and (penalty.adminId != None or self._REMOVE_B3_BAN)):
                self.debug('Banned client (%s) found in follow list DB table. Removing...' % client.name)
                cursor2 = self.console.storage.query(self._DEL_QUERY % client.id)
                cursor2.close()
            else:
                self.debug('Client (%s) was banned by B3 or ban duration is too short' % client.name)
        cursor.close()

    def process_disconnect_event(self, client_cid):
        self.debug("Processing disconnect event")
        self.debug('Disconnected client\'s cid = %s, followlist = %s' % (client_cid, self._following))
        if self._following.has_key(client_cid):
            self.debug("Client %s disconnected, removing from online suspect list" % (self._following[client_cid]))
            del self._following[client_cid]
            if len(self._following) > 0:
                self.verbose('Online suspects: %s' % self._following)
            else:
                self.verbose('All suspected players disconnected')

    def notify_connecting_admin(self, client):
        for suspect in self._following.values():
            self._show_message(client, suspect)
            time.sleep(1)
        
    def _add_list(self, client):
        if not self._following.has_key(client.id):
            self.verbose('online follow list: %s' % self._following)
            self.debug("Checking database for %s [@%s]" % (client.name, client.id))
            cursor = self.console.storage.query(self._SELECT_QUERY % client.id)
            if cursor.rowcount > 0:
                r = cursor.getRow()
                self.debug("Client %s [@%s] found in follow list." % (client.name, client.id))
                if r['reason'] and r['reason'] != '' and r['reason'] != 'None':
                    reason = r['reason']
                else:
                    reason = self._DEFAULT_REASON
                admin = self._adminPlugin.findClientPrompt("@%s" % r['admin_id'])
                if admin:
                    admin_name = admin.name
                    admin_id = admin.id
                else:
                    admin_name = 'B3'
                    admin_id = '0'
                client.setvar(self, 'follow_reason', reason)
                self.verbose('follow_reason: %s' % reason)
                client.setvar(self, 'follow_admin', admin_name)
                self.verbose('follow_admin: %s' % admin_name)
                client.setvar(self, 'follow_admin_id', admin_id)
                self.verbose('follow_admin_id: %s' % admin_id)
                client.setvar(self, 'follow_data', {'reason': reason, 'admin': admin_name, 'admin_id': admin_id})
                self._following[client.cid] = client
                self.verbose('online follow list: %s' % self._following)
                return True
            cursor.close()
        return False
        
    def cmd_checkfollow(self, data, client, cmd=None):
        """\
        list connected users being followed
        """        
        if len(self._following) > 0:
            client.message("^7Checking...")
            self.notify_connecting_admin(client)
            client.message("^7Check complete.")
        else:
            client.message('Currently there are no players online in follow list')

    def cmd_syncfollow(self, data, client, cmd=None):
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

    def cmd_follow(self, data, client, cmd=None):
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
            self.debug("%s added to watch list" % sclient.name)
            client.message("^7%s has been added to the watch list." % sclient.name)
        else:
            self.debug("%s already in watch list" % sclient.name)
            client.message("^7%s already exists in watch list." % sclient.name)
        cursor.close()
        self.sync_list(None)
        
    def cmd_unfollow(self, data, client, cmd=None):
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
        if cursor.rowcount == 0:
            self.debug('%s is not in watchlist, giving up...' % sclient.name)
            client.message('%s is not in watchlist, giving up...' % sclient.name)
            return False

        self.debug("%s removed from watch list" % sclient.name)
        client.message("^7%s removed from the watch list." % sclient.name)
        self.sync_list(None)

    def cmd_followinfo(self, data, client, cmd=None):
        """\
        <name> - show more details
        """
        m = self._adminPlugin.parseUserCmd(data)
        if not m:
            client.message('^7Invalid parameters')
            return False
        
        sclient = self._adminPlugin.findClientPrompt(m[0], client)
        cursor = self.console.storage.query(self._SELECT_QUERY % sclient.id)
        
        if cursor.rowcount > 0:
            r = cursor.getRow()
            admin = self._adminPlugin.findClientPrompt("@%s" % r['admin_id'], client)
            if r['reason'] and r['reason'] != '' and r['reason'] != 'None':
                reason = r['reason']
            else:
                reason = self._DEFAULT_REASON
            client.message('%s was added by %s for %s' % (sclient.name, admin.name, reason))
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
