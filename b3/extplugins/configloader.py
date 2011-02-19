#
# Plugin for BigBrotherBot(B3) (www.bigbrotherbot.com)
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
__version__ = '1.0.0'
__author__  = 'SGT'

import b3, re, threading, time, os
import b3.events
import b3.plugin
import os.path

class ConfigloaderPlugin(b3.plugin.Plugin):
    _mainconfpath = ''
    _confpath = ''
    _modpath = ''
    _gameName = ''

    def onStartup(self):

        self._adminPlugin = self.console.getPlugin('admin')        
        if not self._adminPlugin:
            # something is wrong, can't start without admin plugin
            self.error('Could not find admin plugin')
            return False
                    
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
        self.bot('Store your config file here:')
        self.bot('GameConfigPath: %s for game: %s' %(self._confpath, self._gameName))

        self._adminPlugin.registerCommand(self, 'loadconfig', self._min_level, self.cmd_loadconfig,'cload') 

    def onLoadConfig(self):
        try:
            self._min_level = self.config.getint('settings', 'min_level')
        except:
            self._min_level = 80
        
    def cmd_loadconfig(self, data, client, cmd=None):
        if not data:
            client.message('^7Invalid or missing data.')
        filename = os.path.join(self._confpath,"%s.cfg" % data)
        if os.path.isfile(filename):
            self.debug('Executing %s' %(filename))            
            self.console.write('exec %s.cfg' % data)
            client.message("^7Loaded: ^2%s.cfg" % data)
        else:
            self.debug('Config file %s not found' % filename)
            client.message('^7Config file not found')

if __name__ == '__main__':
    from b3.fake import fakeConsole
    
    setattr(fakeConsole.game,'fs_homepath','.q3a')
    setattr(fakeConsole.game,'fs_game','q3ut4')
    setattr(fakeConsole,'gameName','iourt')
    fakeConsole.setCvar('fs_homepath','.q3a')
    fakeConsole.setCvar('fs_game','q3ut4')

    p = ConfigloaderPlugin(fakeConsole, '@b3/extplugins/conf/configloader.xml')
    p.onStartup()
