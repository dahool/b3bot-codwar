#
# BigBrotherBot(B3) (www.bigbrotherbot.com)
# Copyright (C) 2010 Lake
# Copyright (C) 2011 SGT
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
# 19-03-2011 SGT - 1.0.4
# Use SHA1 instead of MD5 to hash guids
# Use server key as seed for hashing
# Send ban info

__author__  = 'Lake'
__version__ = '1.0.4'

import b3, time, thread, xmlrpclib, re
import b3.events
import b3.plugin
import b3.cron
from b3.functions import minutesStr
import random, datetime

try:
    import hashlib
    hash = hashlib.sha1
except ImportError:
    import md5
    hash = md5.new
    
#--------------------------------------------------------------------------------------------------
class IpdbPlugin(b3.plugin.Plugin):
    _url = 'http://ipdbs.appspot.com/xmlrpc'
    _cronTab    = None
    _banCronTab = None
    _rpc_proxy  = None
    _interval   = None
    _key        = None
    _hostname   = None
    _last       = None
    _always_update = False
    _banInfoInterval = 2
    _delta = None
    
    _BAN_QUERY = "SELECT c.guid as guid,p.duration as duration,p.reason as reason FROM penalties p INNER JOIN clients c ON p.client_id = c.id "\
    "WHERE (p.type='Ban' OR p.type='TempBan') AND (p.time_expire=-1 OR p.time_expire > %(now)d) "\
    "AND p.time_add >= %(since)d AND p.inactive=0"
        
    def onStartup(self):
        if self._cronTab:
            self.console.cron - self._cronTab
        self._rpc_proxy = xmlrpclib.ServerProxy(self._url)
        self.debug('Update server name')
        try:
            self._rpc_proxy.server.updateName(self._key, self._hostname)
        except Exception, e:
            self.error("Error updating server name. %s" % str(e))
        else:
            # activate only if the remote server is working
            self._delta = datetime.timedelta(hours=self._banInfoInterval, minutes=15)
            
            self._cronTab = b3.cron.PluginCronTab(self, self.update, minute='*/%s' % self._interval)
            self.console.cron + self._cronTab

            rmin = random.randint(0,59)
            self._banCronTab = b3.cron.PluginCronTab(self, self.updateBanInfo, 0, rmin, '*/%s' % self._banInfoInterval, '*', '*', '*')
            self.console.cron + self._banCronTab
            
    def onLoadConfig(self):
        self._interval = self.config.getint('settings', 'interval')
        self._key = self.config.get('settings', 'key')
        self._always_update = self.config.getboolean('settings','always_update')
        self._hostname = self.console.getCvar('sv_hostname').getString()

    def _hash(self, text):
        return hash('%s%s' % (text, self._key)).hexdigest()
    
    def update(self):       
        if self.isEnabled():
            clients = self.console.clients.getList()
            if not self._always_update and (len(clients) == 0 and self._last == 0):
                self.debug('ipdb update aborted')
                return
            self.debug('Updating ipdb')
            self._last = len(clients)
            status  = []
            for c in clients:
                guid = self._hash(c.guid)
                status.append( ( c.name, c.ip, guid ) )
            try:
                self._rpc_proxy.server.insertLog (self._key, status)
            except Exception, e:
                self.error("Error updating ipdb. %s" % str(e))

    def updateBanInfo(self):
        if self.isEnabled():
            self.debug('Collect ban info')
            now = int(time.mktime(datetime.datetime.now().timetuple()))
            since = int(time.mktime((datetime.datetime.now() - self._delta).timetuple()))
            cursor = self.console.storage.query(self._BAN_QUERY % {'now': now,
                                                                      'since': since})

            if cursor.rowcount == 0:
                self.debug('No ban info to send')
                return
            
            list = []
            while not cursor.EOF:
                r = cursor.getRow()
                if r['duration'] == -1 or r['duration'==0]:
                    reason = 'Permanent banned. Reason: %s' % r['reason']
                else:
                    reason = 'Temp banned for %s. Reason: %s' % (minutesStr(r['duration']), r['reason'])
                list.append((self._hash(r['guid']),reason))
                cursor.moveNext()
            
            self.debug('Update ban info')
            try:
                self._rpc_proxy.server.updateBanInfo(self._key, list)
            except Exception, e:
                self.error("Error updating ipdb. %s" % str(e))
            
            cursor.close()            
            
if __name__ == '__main__':
    from b3.fake import fakeConsole
    from b3.fake import joe, simon, moderator, superadmin
    import time
    
    fakeConsole.setCvar('sv_hostname','IPDB Test Server')    
    
    p = IpdbPlugin(fakeConsole,'conf/plugin_ipdb1.xml')
    p._url = 'http://localhost:8888/xmlrpc'
    p.onStartup()
    
    joe.connects(cid=1)
    simon.connects(cid=2)
    moderator.connects(cid=3)
    superadmin.connects(cid=4)
    
    time.sleep(2)
    p.update()
    time.sleep(2)
    p.updateBanInfo()
