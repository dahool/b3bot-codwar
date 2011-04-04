#
# BigBrotherBot(B3) (www.bigbrotherbot.com)
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

__author__  = 'SGT'
__version__ = '1.0.4b'

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
    import sha
    hash = sha.new
    
#--------------------------------------------------------------------------------------------------
class Ipdb2Plugin(b3.plugin.Plugin):
    _url = 'http://ipdburt.appspot.com/xmlrpc'
    _cronTab    = []
    _banCronTab = None
    _rpc_proxy  = None
    _interval   = 2
    _key        = None
    _hostname   = None
    _last       = None
    _always_update = False
    _banInfoInterval = 2
    _delta = None
    _failureCount = 0
    _failureMax = 20
    _inqueue = []
    _outqueue = []
    _banInfoDumpTime = 7
    _clientInfoDumpTime = 7
    _color_re = re.compile(r'\^[0-9]')
    
    _BAN_QUERY = "SELECT p.id as id, c.guid as guid,c.name as name, c.ip as ip, p.duration as duration,p.reason as reason,p.time_add as time_add, c.time_edit as time_edit "\
    "FROM penalties p INNER JOIN clients c ON p.client_id = c.id "\
    "WHERE (p.type='Ban' OR p.type='TempBan') AND (p.time_expire=-1 OR p.time_expire > %(now)d) "\
    "AND p.time_add >= %(since)d AND p.inactive=0 AND keyword <> 'ipdb'"
        
    _ALL_C_QUERY = "SELECT id, guid, name, ip, time_edit FROM clients WHERE auto_login = 1 and time_edit BETWEEN %(fromdate)d AND %(todate)d LIMIT 30"
    
    def onStartup(self):
        self._rpc_proxy = xmlrpclib.ServerProxy(self._url)
        
        self._inqueue = []
        self._outqueue = []
            
        self.registerEvent(b3.events.EVT_CLIENT_AUTH)
        self.registerEvent(b3.events.EVT_CLIENT_DISCONNECT)
        self.registerEvent(b3.events.EVT_CLIENT_NAME_CHANGE)
            
        rmin = random.randint(5,59)
    
        self._cronTab.append(b3.cron.PluginCronTab(self, self.update, minute='*/%s' % self._interval))
        if self._banInfoInterval > 0:
            self._delta = datetime.timedelta(hours=self._banInfoInterval, minutes=15)
            self._cronTab.append(b3.cron.PluginCronTab(self, self.updateBanInfo, 0, rmin, '*/%s' % self._banInfoInterval, '*', '*', '*'))
        if self._clientInfoDumpTime >= 0:
            self._cronTab.append(b3.cron.PluginCronTab(self, self.dumpClientInfo, 0, rmin - 5, self._clientInfoDumpTime, '*', '*', '*'))
        if self._banInfoDumpTime >= 0:
            self._cronTab.append(b3.cron.PluginCronTab(self, self.dumpBanInfo, 0, rmin, self._banInfoDumpTime, '*', '*', '*'))
        self.updateName()
            
    def onLoadConfig(self):
        self._hostname = self._color_re.sub('',self.console.getCvar('sv_hostname').getString())
        try:
            self._key = self.config.get('settings', 'key')
        except:
            raise Exception("Invalid key")
        try:
            self._interval = self.config.getint('settings', 'interval')
        except:
            pass
        try:
            self._banInfoDumpTime = self.config.getint('settings', 'baninfodump')
        except:
            pass
        try:
            self._clientInfoDumpTime = self.config.getint('settings', 'clientinfodump')
        except:
            pass
        try:
            self._banInfoInterval = self.config.getint('settings', 'baninfointerval')
        except:
            pass

    def _hash(self, text):
        return hash('%s%s' % (text, self._key)).hexdigest()
    
    def onEvent(self, event):
        if event.type == b3.events.EVT_CLIENT_AUTH or event.type == b3.events.EVT_CLIENT_NAME_CHANGE:
            self.onClientConnect(event.client)
        elif event.type == b3.events.EVT_CLIENT_DISCONNECT:
            self.onClientDisconnect(event.data)
            
    def onClientConnect(self, client):
        if not client or \
            not client.id or \
            client.cid == None or \
            client.pbid == 'WORLD':
            return
        
        if client in self._outqueue:
            self._outqueue.remove(client)
        elif client not in self._inqueue:
            self._inqueue.append(client)
        
    def onClientDisconnect(self, cid):
        client = self.console.clients.getByCID(cid)
        if client and client not in self._outqueue:
            self._outqueue.append(client)

    def updateName(self):
        try:
            self.debug('Update server name')
            self._rpc_proxy.server.updateName(self._key, self._hostname)
        except Exception, e:
            self.error("Error updating server name. %s" % str(e))
            if self.increaseFail():
                self.console.cron + b3.cron.OneTimeCronTab(self.updateName, '*/30')
        else:
            self.enable()
            
    def update(self):
        self.updateConnect()
        self.updateDisconnect()
        
    def updateConnect(self):
        status = []
        for i in range(0,len(self._inqueue)):
            c = self._inqueue.pop()
            if c.connected:
                guid = self._hash(c.guid)
                status.append( ( c.name, c.ip, guid ) )
        if len(status) > 0:
            try:
                self.debug("Updating connected")
                self._rpc_proxy.server.updateConnect(self._key, status)
            except Exception, e:
                self.error("Error updating ipdb. %s" % str(e))
                self.increaseFail()

    def updateDisconnect(self):
        status = []
        for i in range(0,len(self._outqueue)):
            c = self._outqueue.pop()
            guid = self._hash(c.guid)
            status.append( ( c.name, c.ip, guid ) )                
        if len(status) > 0:
            try:
                self.debug("Updating disconnected")
                self._rpc_proxy.server.updateDisconnect(self._key, status)
            except Exception, e:
                self.error("Error updating ipdb. %s" % str(e))
                self.increaseFail()
                    
    def enable(self):
        self._failureCount = 0
        self._enabled = True
        for ct in self._cronTab:
            self.console.cron + ct
            
    def disable(self):
        self._enabled = False
        for ct in self._cronTab:
            self.console.cron - ct
        
    def increaseFail(self):
        self._failureCount += 1
        if self._failureCount >= self._failureMax:
            self.disable()
            next = (datetime.datetime.now() + datetime.timedelta(hours=4)).hour
            self.console.cron + b3.cron.OneTimeCronTab(self.updateName, second=0, minute=0, hour=next)
            self._failureCount = 0
            return False
        return True
            
    def updateBanInfo(self, sendAll = False):
        self.debug('Collect ban info')
        now = int(time.time())
        if sendAll:
            since = 1262314800
            q = self._BAN_QUERY + " LIMIT 30"
        else:
            since = int(time.mktime((datetime.datetime.now() - self._delta).timetuple()))
            q = self._BAN_QUERY
        cursor = self.console.storage.query(q % {'now': now,
                                                'since': since})
                                                                  
        list = []
        keys = []
        while not cursor.EOF:
            r = cursor.getRow()
            keys.append(str(r['id']))
            timeAdd = datetime.datetime.fromtimestamp(r['time_add']).strftime("%d/%m/%Y")
            timeEdit = datetime.datetime.fromtimestamp(r['time_edit'])
            if r['duration'] == -1 or r['duration'] == 0:
                reason = 'Permanent banned since %s. Reason: %s' % (timeAdd, r['reason'])
            else:
                reason = 'Temp banned since %s for %s. Reason: %s' % (timeAdd, minutesStr(r['duration']), r['reason'])
            list.append((self._hash(r['guid']),reason, r['name'], r['ip'], timeEdit))
            cursor.moveNext()
        
        if len(list) > 0:
            self.debug('Update ban info')
            try:
                self._rpc_proxy.server.updateBanInfo(self._key, list)
            except Exception, e:
                self.error("Error updating ipdb. %s" % str(e))
                self.increaseFail()
            else:
                cursor = self.console.storage.query("UPDATE penalties SET keyword = 'ipdb' WHERE id IN (%s)" % ",".join(keys))
        else:
            self.debug('No ban info to send')
                
    def dumpBanInfo(self):
        self.debug('Collect all ban info')
        self.updateBanInfo(True)
    
    def dumpClientInfo(self):
        self.debug('Collect client info')
        todate = 1301626800
        fromdate = 1285902000 # oct 2010
        cursor = self.console.storage.query(self._ALL_C_QUERY % {'fromdate': fromdate,
                                                                  'todate': todate})

        if cursor.rowcount == 0:
            self.debug('All clients synced.')
            return
        
        list = []
        keys = []
        while not cursor.EOF:
            row = cursor.getRow()
            keys.append(str(row['id']))
            guid = self._hash(row['guid'])
            timeEdit = datetime.datetime.fromtimestamp(row['time_edit'])
            status.append( ( row['name'], row['ip'], guid, timeEdit ) )     
            cursor.moveNext()
        
        self.debug('Send clients')
        try:
            self._rpc_proxy.server.updateConnect(self._key, list)
        except Exception, e:
            self.error("Error updating ipdb. %s" % str(e))
            self.increaseFail()
        else:
            cursor = self.console.storage.query("UPDATE clients SET auto_login = 0 WHERE id IN (%s)" % ",".join(keys))
                    
if __name__ == '__main__':
    from b3.fake import fakeConsole
    from b3.fake import joe, simon, moderator, superadmin
    import time
    
    fakeConsole.setCvar('sv_hostname','IPDB Test Server')    
    
    p = Ipdb2Plugin(fakeConsole,'conf/ipdb.xml')
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
