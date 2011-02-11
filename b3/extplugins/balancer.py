#
# Load Balancer Plugin
# Run certain commands according the number of players
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
# 2009-02-08 - 1.0.0 - SGT
# Initial version

__version__ = '1.0.0'
__author__  = 'SGT'

import b3, threading, time
import b3.events
import b3.plugin
import b3.cron
import glob
import os
import re

#--------------------------------------------------------------------------------------------------
class BalancerPlugin(b3.plugin.Plugin):

    _cronTab1 = None
    _cronTab2 = None
    _configs = {}
    _last_run = None
    _prefix = 'b3_config'
    _enqueue = False
    
    def onStartup(self):
        self.registerEvent(b3.events.EVT_CLIENT_AUTH)
        self.registerEvent(b3.events.EVT_CLIENT_DISCONNECT)
        self.registerEvent(b3.events.EVT_GAME_WARMUP)

    def onLoadConfig(self):
        # load our settings
        self.verbose('Loading config')

        try:
            self._prefix = self.config.getint('settings', 'file_prefix')
        except:
            pass
        try:
            self._action_delay = self.config.getint('settings', 'action_delay')
        except:
            self._action_delay = 30
        try:
            self._auto_run_rate = self.config.getint('settings', 'auto_run_rate')
        except:
            self._auto_run_rate = 5
        try:
            self._update_cfg_rate = self.config.getint('settings', 'update_cfg_rate')
        except:
            self._update_cfg_rate = 30
            
        # the name of the running parser
        self._gameName = self.console.gameName

        self._confpath = self.console.getCvar('fs_homepath')
        if self._confpath != None:
            self._confpath = self._confpath.getString()
    
        self._modpath = self.console.getCvar('fs_game')
        if self._modpath != None:
            self._modpath = self._modpath.getString()
        elif self._gameName[:3] == 'cod':
            self._modpath = 'main'
        elif self._gameName[:3] == 'iou':
            self._modpath = 'q3ut4'
        elif self._gameName[:3] == 'wop':
            self._modpath = 'wop'
            
        self._confpath += '/' + self._modpath + '/'
        
        self.bot('Store your %s_<num>.cfg here:' % self._prefix)
        self.bot('GameConfigPath: %s' % self._confpath)
            
        self.doUpdateFiles()
        
        if self._cronTab1:
            self.console.cron - self._cronTab1
        if self._cronTab2:
            self.console.cron - self._cronTab2
            
        self._cronTab1 = b3.cron.PluginCronTab(self, self.doAction, minute="*/%d" % self._auto_run_rate)
        self.console.cron + self._cronTab1

        self._cronTab2 = b3.cron.PluginCronTab(self, self.doUpdateFiles, minute="*/%d" % self._update_cfg_rate)
        self.console.cron + self._cronTab2
                    
    def onEvent(self, event):
        if (event.type == b3.events.EVT_CLIENT_AUTH or 
                event.type == b3.events.EVT_CLIENT_DISCONNECT or
                event.type == b3.events.EVT_GAME_WARMUP):
            self.onClientAction()

    def onClientAction(self):
        if not self._enqueue:
            self._enqueue = True
            t = threading.Timer(self._action_delay, self.doAction)
            t.start()

    def doUpdateFiles(self):
        self.debug('Listing files')
        pat = re.compile('(%s_)(\d+)(\.cfg)' % self._prefix)
        self._configs = {}
        for f in glob.glob(os.path.join(self._confpath,'%s_*.cfg' % self._prefix)):
            filename = os.path.basename(f)
            m = pat.match(filename)
            if m:
                v = int(m.group(2))
                self._configs[v] = filename
        self.debug('%d config files loaded' % len(self._configs))

    def doAction(self):
        self._enqueue = False
        
        if len(self._configs) == 0:
            self.debug('Aborting. No configs')
            return
            
        clients = self.console.clients.getList()

        if len(clients) == 0:
            self.debug('Aborting. No clients')
            return
            
        num = None
        for c in sorted(self._configs):
            if c <= len(clients):
                num = c
            else:
                break
                
        if num is not None:
            if self._last_run and self._last_run == num:
                return            
                
            if os.path.isfile(os.path.join(self._confpath,self._configs[num])):
                self.console.write('exec %s' % self._configs[num])
                self.debug('Executing %s' %(os.path.join(self._confpath,self._configs[num])))
                self._last_run = num
            else:
                self.error('File %s do not exists' %(os.path.join(self._confpath,self._configs[num])))
        else:
            self.debug('No config found for %d' % len(clients))

if __name__ == '__main__':
    from b3.fake import fakeConsole
    from b3.fake import joe, simon, moderator, superadmin
    import time
    
    fakeConsole.setCvar('g_mapcycle','mapcycle.txt')
    fakeConsole.setCvar('fs_homepath','/local/codwar/q3a')
    setattr(fakeConsole,'gameName','iou')
        
    p = BalancerPlugin(fakeConsole, '@b3/extplugins/conf/balancer.xml')
    p.onStartup()
    
    joe.connects(cid=1)
    simon.connects(cid=2)
    moderator.connects(cid=3)
    superadmin.connects(cid=4)
    
    print "-------------------------"
