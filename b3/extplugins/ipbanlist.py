# BigBrotherBot(B3) (www.bigbrotherbot.com)
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
# 14-01-2011 - 1.0.0 - Initial

__version__ = '1.0.0'
__author__  = 'SGT'

import b3
import b3.plugin
import b3.cron
import b3, time, thread, threading
import datetime

class IpbanlistPlugin(b3.plugin.Plugin):

    _cronTab = None
    _since = 24
    _refresh_rate = 12
    _cache = set()
    _do_ban = False
    _SELECT_QUERY = "SELECT distinct(c.ip) FROM penalties p INNER JOIN clients c ON p.client_id = c.id "\
                    "WHERE (p.type='Ban' OR p.type='TempBan') AND (p.time_expire=-1 OR p.time_expire > %(now)d) "\
                    "AND p.time_add >= %(since)d AND p.inactive=0"
                    
    _SELECT_QUERY_V = "SELECT c.ip FROM penalties p INNER JOIN clients c ON p.client_id = c.id "\
                    "WHERE (p.type='Ban' OR p.type='TempBan') AND (p.time_expire=-1 OR p.time_expire > %(now)d) "\
                    "AND p.time_add >= %(since)d AND p.inactive=0 AND c.ip = %(ip)s"
                        
    def onStartup(self):
        self.registerEvent(b3.events.EVT_CLIENT_AUTH)
        self.registerEvent(b3.events.EVT_CLIENT_BAN)
        self.registerEvent(b3.events.EVT_CLIENT_BAN_TEMP)
        
        self.load_penalties()
        
        if self._cronTab:
            # remove existing crontab
            self.console.cron - self._cronTab

        if self._refresh_rate > 0:
            self._cronTab = b3.cron.PluginCronTab(self, self.load_penalties, hour="*/%s" % self._refresh_rate)
            self.console.cron + self._cronTab
        
    def onLoadConfig(self):
        try:
            self._since = self.config.getint('settings', 'penalties_since')
        except:
            self.debug('Using default value (%s) for penalties_since', self._since)
        try:
            self._refresh_rate = self.config.getint('settings','refresh_rate')
        except:
            self.debug('Using default value (%s) for refresh_rate', self._refresh_rate)
        try:
            self._do_ban = self.config.getboolean('settings','apply_ban')
        except:
            self.debug('Using default value (%s) for apply_ban', self._do_ban)
                    
        self._delta = datetime.timedelta(hours=self._since)
        
    def onEvent(self,  event):
        if event.type == b3.events.EVT_CLIENT_AUTH:
            self.onClientConnect(event.client)
        elif event.type == b3.events.EVT_CLIENT_BAN or event.type == b3.events.EVT_CLIENT_BAN_TEMP:
            thread.start_new_thread(self.load_penalties, ())

    def onClientConnect(self, client):
        if not client or \
            not client.id or \
            client.cid == None or \
            client.pbid == 'WORLD':
            return
        
        thread.start_new_thread(self.load_penalties, ())
        
        if client.ip in self._cache:
            # ip is in cache. we need to be sure if the ban is still valid.
            if self.is_still_banned(client.ip):
                self.debug("Kicked %s (%s)" % (client.name, client.ip))
                client.notice("Suspicion of ban break.", None)
                if self._do_ban:
                    client.tempban("Suspicion of ban break.", "99y", silent=True)
                client.kick(silent=True)
            else:
                # cache is outdated, reload
                thread.start_new_thread(self.load_penalties, ())
    
    def is_still_banned(self, ip):
        self._cache = set()
        now = int(time.mktime(datetime.datetime.now().timetuple()))
        since = int(time.mktime((datetime.datetime.now() - self._delta).timetuple()))
        cursor = self.console.storage.query(self._SELECT_QUERY_V % {'now': now,
                                                                    'since': since,
                                                                    'ip': ip})
        if cursor.EOF:
            r = False
        else:
            r = True
        cursor.close()
        return r
                            
    def load_penalties(self):
        self.debug("Load penalties")
        self._cache = set()
        now = int(time.mktime(datetime.datetime.now().timetuple()))
        since = int(time.mktime((datetime.datetime.now() - self._delta).timetuple()))
        cursor = self.console.storage.query(self._SELECT_QUERY % {'now': now, 'since': since})
        while not cursor.EOF:
            r = cursor.getRow()
            self._cache.add(r['ip'])
            cursor.moveNext()
        cursor.close()
        self.debug("Loaded %d ips" % len(self._cache))
