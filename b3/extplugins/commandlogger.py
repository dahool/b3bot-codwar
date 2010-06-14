# BigBrotherBot(B3) (www.bigbrotherbot.com)
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

__version__ = '1.0.0'
__author__  = 'SGT'

import b3
import b3.plugin

class CommandloggerPlugin(b3.plugin.Plugin):
    '''
    CREATE TABLE auditlog (
        id INT NOT NULL AUTO_INCREMENT PRIMARY KEY ,
        command VARCHAR( 20 ) NOT NULL ,
        data VARCHAR( 50 ) NULL ,
        client_id INT( 11 ) UNSIGNED NOT NULL ,
        time_add INT( 11 ) UNSIGNED NOT NULL ,
    ) ENGINE = MYISAM;
    ALTER TABLE auditlog ADD INDEX (client_id);
    ALTER TABLE auditlog ADD INDEX (time_add);
    ALTER TABLE auditlog ADD INDEX (command);
    '''
    
    _INSERT_QUERY = "INSERT INTO auditlog (command, data, client_id, time_add) VALUES ('%s', '%s', %d, %d)"
    
    def onStartup(self):
        self._adminPlugin = self.console.getPlugin('admin')
        if not self._adminPlugin:
            self.warning('Could not find admin plugin')
          
        self.registerEvent(b3.events.EVT_ADMIN_COMMAND)
        
    def onLoadConfig(self):
        self._min_level = self.config.getint('settings', 'min_level')
        
    def onEvent(self,  event):
        if event.type == b3.events.EVT_ADMIN_COMMAND:
            if event.client.maxLevel >= self._min_level:
                data = event.data[1]
                if self._adminPlugin:
                    cid, params = self._adminPlugin.parseUserCmd(data)
                    cli = self._adminPlugin.findClientPrompt(cid)
                    if cli:
                        data = "%s [%s - %s]" % (data,cli.id,cli.name)
                self.log(event.data[0],event.client, data)
            
    def log(self, command, client, data=None):
        cursor = self.console.storage.query(self._INSERT_QUERY % (command.command, data, client.id, self.console.time()))
        cursor.close()
