#
# BigBrotherBot(B3) (www.bigbrotherbot.net)
# Copyright (C) 2011 Sergio Gabriel Teves
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.    See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA    02110-1301    USA
#
# CHANGELOG
# 04/09/2011 - 1.0.0 - SGT
# Initial

__author__    = 'SGT'
__version__ = '1.0.0'

import b3, time, os, StringIO
import b3.plugin
import b3.cron
from cgi import escape
from ftplib import FTP
from b3 import functions
from b3.functions import sanitizeMe

#--------------------------------------------------------------------------------------------------
class ConfigdumpPlugin(b3.plugin.Plugin):
    _ftpstatus = False
    _ftpinfo = None
    _cvars = []
    _crontab = None

    def onLoadConfig(self):
        if self.config.get('settings','output_file')[0:6] == 'ftp://':
            self._ftpinfo = functions.splitDSN(self.config.get('settings','output_file'))
            self._ftpstatus = True
        else:        
            self._outputFile = os.path.expanduser(self.config.get('settings', 'output_file'))
        
        self._cvars = [var.strip() for var in self.config.get('settings', 'cvars').split(',')]
	
	dump = self.config.get('settings','time').split(':')

        if self._crontab:
	    self.console.cron - self._crontab
	self._crontab = b3.cron.PluginCronTab(self, self.update, 0, dump[1], dump[0])
        self.console.cron + self._crontab

    def onEvent(self, event):
        if event.type == b3.events.EVT_STOP:
            self.info('B3 stop/exit.. dumping config')
            self.update()

    def update(self):
	self.bot("Dump config")
        out = StringIO.StringIO()
        for var in self._cvars:
            value = self.console.getCvar(var)
            if value:
                out.write('set %s "%s"\n' % (var, value.getString()))

	out.seek(0)
        self.write(out)

    def write(self, out):
        if self._ftpstatus == True:
            self.debug('Uploading CONFIG to FTP server')
            ftp=FTP(self._ftpinfo['host'],self._ftpinfo['user'],passwd=self._ftpinfo['password'])
            ftp.cwd(os.path.dirname(self._ftpinfo['path']))
            ftp.storbinary('STOR '+os.path.basename(self._ftpinfo['path']), out)
        else:
            self.debug('Writing CONFIG to %s', self._outputFile)
            f = file(self._outputFile, 'w')
            f.write(out.getvalue())
            f.close()
            
if __name__ == '__main__':
    from b3.fake import fakeConsole
    from b3.fake import joe
    from b3.fake import simon
    
    p = ConfigdumpPlugin(fakeConsole, "/local/codwar/j4f/bot/b3/extplugins/conf/configdump.xml")
    p.onStartup()
    
    while True: pass
