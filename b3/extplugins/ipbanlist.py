# BigBrotherBot(B3) (www.bigbrotherbot.net)
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
# 2011-01-14 - 1.0.0
# Initial
# 2011-02-11 - 1.0.1 
# Add event. Some code rework.
# 2011-02-19 - 1.0.2 
# Fix error in sql

__version__ = '1.0.2'
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
    _do_lookupall = False
    
    _SELECT_QUERY = "SELECT c.ip FROM penalties p INNER JOIN clients c ON p.client_id = c.id "\
    "WHERE (p.type='Ban' OR p.type='TempBan') AND (p.time_expire=-1 OR p.time_expire > %(now)d) "\
    "AND p.time_add >= %(since)d AND p.inactive=0 AND c.ip = '%(ip)s'"

    _SELECT_QUERY_FULL = "SELECT p.* FROM penalties p WHERE "\
    "(p.time_expire=-1 OR p.time_expire > %(time)d) AND p.inactive = 0 AND "\
    "(p.type = 'TempBan' or p.type = 'Ban') AND p.client_id IN ("\
    "SELECT distinct(c.id) FROM clients c LEFT JOIN aliases a ON c.id = a.client_id "\
    "WHERE c.ip = '%(ip)s' or a.ip = '%(ip)s')"
                        
    def onStartup(self):
        self.registerEvent(b3.events.EVT_CLIENT_AUTH)
        self.registerEvent(b3.events.EVT_CLIENT_BAN)
        self.registerEvent(b3.events.EVT_CLIENT_BAN_TEMP)
        self.createEvent('EVT_BAN_BREAK', 'Ban Break Event')
        
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
        try:
            self._do_lookupall = self.config.getboolean('settings','lookup_all')
        except:
            self.debug('Using default value (%s) for apply_ban', self._do_lookupall)
                                
        self._delta = datetime.timedelta(hours=self._since)

    def onEvent(self,  event):
        if event.type == b3.events.EVT_CLIENT_AUTH:
            self.debug("Queued event [%s]" % event.client.name)
            thread.start_new_thread(self.onClientConnect, (event.client,))
        
    def _lookup_all(self, client):
        self.debug("Full lookup for %s" % client.name)
        cursor = self.console.storage.query(self._SELECT_QUERY_FULL % {'ip': client.ip, 'time': int(time.time())})
        r = (cursor.rowcount > 0)
        return r

    def _lookup_min(self, client):
        self.debug("Min lookup for %s" % client.name)
        now = int(time.mktime(datetime.datetime.now().timetuple()))
        since = int(time.mktime((datetime.datetime.now() - self._delta).timetuple()))
        cursor = self.console.storage.query(self._SELECT_QUERY % {'now': now,
                                                                    'since': since,
                                                                    'ip': client.ip})
        r = (cursor.rowcount > 0)
        return r

    def onClientConnect(self, client):
        if not client or \
            not client.id or \
            client.cid == None or \
            client.pbid == 'WORLD':
            return
        
        if self._lookup_min(client):
            self.debug("Kicked %s (%s)" % (client.name, client.ip))
            client.notice("Suspicion of ban break.", None)
            if self._do_ban:
                client.tempban("Suspicion of ban break.", "99y", silent=True)
            #client.kick(silent=True)
            client.kick(silent=False)
            self.console.queueEvent(self.console.getEvent('EVT_BAN_BREAK', (client,), None))
        elif self._do_lookupall and client.connections == 1 and self._lookup_all(client):
            self.debug("Lookup all was positive")
            self.console.queueEvent(self.console.getEvent('EVT_BAN_BREAK', (client,), None))

if __name__ == '__main__':
    from b3.fake import fakeConsole
    from b3.fake import joe, simon, moderator, superadmin
    
    p = IpbanlistPlugin(fakeConsole, '@b3/extplugins/conf/ipbanlist.xml')
    p.onStartup()
    
    joe.connects(cid=1)
    simon.connects(cid=2)
    moderator.connects(cid=3)
    superadmin.connections=2
    superadmin.connects(cid=4)
