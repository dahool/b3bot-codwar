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
import b3, time, thread, threading

class ChatloggerPlugin(b3.plugin.Plugin):
    '''
    CREATE TABLE chatlog (
        id INT NOT NULL AUTO_INCREMENT PRIMARY KEY ,
        data VARCHAR( 100 ) NULL ,
        target VARCHAR( 50 ) NULL ,
        client_id INT( 11 ) UNSIGNED NOT NULL ,
        time_add INT( 11 ) UNSIGNED NOT NULL
    ) ENGINE = MYISAM;
    ALTER TABLE chatlog ADD INDEX (client_id);
    ALTER TABLE chatlog ADD INDEX (time_add);
    '''
    
    _INSERT_QUERY = "INSERT INTO chatlog (data, client_id, time_add, target) VALUES ('%s', %d, %d, '%s')"
    
    _TEAM_NAME = {-1: 'UNKNOWN',
                 1: 'SPEC',
                 2: 'RED',
                 3: 'BLUE'}
                 
    def onStartup(self):
        self.registerEvent(b3.events.EVT_CLIENT_SAY)
        self.registerEvent(b3.events.EVT_CLIENT_TEAM_SAY)
        self.registerEvent(b3.events.EVT_CLIENT_PRIVATE_SAY)
        
    def onEvent(self,  event):
        target = None
        if event.type == b3.events.EVT_CLIENT_SAY:
            target = "ALL"
        elif event.type == b3.events.EVT_CLIENT_TEAM_SAY:
            target = "TEAM: %s" % self._TEAM_NAME.get(event.target)
        elif event.type == b3.events.EVT_CLIENT_PRIVATE_SAY:
            target = "CLIENT: [%s] - %s" % (event.target.id,event.target.name)
        if target:
            thread.start_new_thread(self.log, (event.data, event.client, target))
            
    def log(self, text, client, target=None):
        cursor = self.console.storage.query(self._INSERT_QUERY % (text, client.id, self.console.time(), target))
        cursor.close()
