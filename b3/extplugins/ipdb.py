#
# BigBrotherBot(B3) (www.bigbrotherbot.com)
# Copyright (C) 2005 Michael "ThorN" Thornton
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

__author__  = 'Lake'
__version__ = '1.0.2'

import b3, time, thread, xmlrpclib, re
import b3.events
import b3.plugin
import b3.cron

try:
    import hashlib
    md5_c = hashlib.md5
except ImportError:
    import md5
    md5_c = md5.new
    
#--------------------------------------------------------------------------------------------------
class IpdbPlugin(b3.plugin.Plugin):
    _cronTab    = None
    _rpc_proxy  = None
    _interval   = None
    _key        = None
    _hostname   = None
    _last       = None
    _always_update = False
    
    def onStartup(self):
        if self._cronTab:
            self.console.cron - self._cronTab
        self._cronTab = b3.cron.PluginCronTab(self, self.update, minute='*/%s' % self._interval)
        self.console.cron + self._cronTab
        self._rpc_proxy = xmlrpclib.ServerProxy("http://ipdbs.com.ar/api/")
        self.debug('Update server name')
        try:
            self._rpc_proxy.server.updateName(self._key, self._hostname)
        except Exception, e:
            self.error("Error updating server name. %s" % str(e))
            
    def onLoadConfig(self):
        self._interval = self.config.getint('settings', 'interval')
        self._key = self.config.get('settings', 'key')
        self._always_update = self.config.getboolean('settings','always_update')
        self._hostname = self.console.getCvar('sv_hostname').getString()

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
                guid = md5_c(c.guid).hexdigest()
                status.append( ( c.name, c.ip, guid ) )
            try:
                self._rpc_proxy.server.insertLog (self._key, status)
            except Exception, e:
                self.error("Error updating ipdb. %s" % str(e))