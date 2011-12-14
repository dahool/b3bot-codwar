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
# 20-10-2010 - 1.0.2
# Escape texts 
# 09-05-2011 - 1.0.3
# Espace backslash
# 28-05-2011 - 1.0.4
# Sanitize string
# 14-12-2011 - 1.0.5
# Dump logs to db on intervals

__version__ = '1.0.5'
__author__  = 'SGT'

import b3
import b3.plugin
import b3, time, thread, threading
import re
import b3.cron

class ChatloggerPlugin(b3.plugin.Plugin):
    '''
    CREATE TABLE chatlog (
        id INT NOT NULL AUTO_INCREMENT PRIMARY KEY ,
        data VARCHAR( 100 ) NULL ,
        info VARCHAR( 255 ) NULL ,
        target VARCHAR( 50 ) NULL ,
        client_id INT( 11 ) UNSIGNED NOT NULL ,
        time_add INT( 11 ) UNSIGNED NOT NULL
    ) ENGINE = MYISAM;
    ALTER TABLE chatlog ADD INDEX (client_id);
    ALTER TABLE chatlog ADD INDEX (time_add);
    ALTER TABLE chatlog ADD INDEX (data);
    '''
    requiresConfigFile = False
    
    _INSERT_QUERY = "INSERT INTO chatlog (data, client_id, time_add, target, info) VALUES ('%s', %d, %d, '%s', '%s')"
    
    _TEAM_NAME = {-1: 'UNKNOWN',
                 1: 'SPEC',
                 2: 'RED',
                 3: 'BLUE'}
    
    _ALLOW_CHARS = re.compile('[^\w\?\+\*\.,:;=_\(\)\$\#!><-]')
    
    _CACHE = []
    
    _crontab = None
    
    _interval = 15
    
    def onStartup(self):
        self.registerEvent(b3.events.EVT_CLIENT_SAY)
        self.registerEvent(b3.events.EVT_CLIENT_TEAM_SAY)
        self.registerEvent(b3.events.EVT_CLIENT_PRIVATE_SAY)
        
        if self._cronTab:
            self.console.cron - self._cronTab
        self._cronTab = b3.cron.PluginCronTab(self, self.dump_logs, minute='*/%d' % self._interval)
        self.console.cron + self._cronTab
        
    def onEvent(self,  event):
        target = None
        if event.type == b3.events.EVT_CLIENT_SAY:
            target = "ALL"
        elif event.type == b3.events.EVT_CLIENT_TEAM_SAY:
            target = "TEAM: %s" % self._TEAM_NAME.get(event.target)
        elif event.type == b3.events.EVT_CLIENT_PRIVATE_SAY:
            target = "CLIENT: [%s] - %s" % (event.target.id,event.target.name)
        if target:
            #thread.start_new_thread(self.log, (event.data, event.client, target))
            self.log(event.data, event.client, target)
    
    def _sanitize(self, text):
        return self._ALLOW_CHARS.sub(' ', text).strip()
        
    def log(self, text, client, target=None):
        try:
            info = self.console.game.mapName
        except:
            info = ''
        text = self._sanitize(text)
        sql = self._INSERT_QUERY % (text, client.id, self.console.time(), target, info)
        self.verbose(sql)
        self._CACHE.append(sql)
        
    def dump_logs(self):
        if len(self._CACHE) > 0:
            lista = self._CACHE[:]
            del self._CACHE[0:len(lista)]
            self.debug("Dumping %d chat lines" % len(lista))
            for sql in lista:
                try:
                    cursor = self.console.storage.query(sql)
                except Exception, e:
                    self.warning("Could not save to database: [%s] %s" % (e[0],e[1]))

if __name__ == '__main__':
    from b3.fake import fakeConsole
    from b3.fake import joe
    import time
    
    p = ChatloggerPlugin(fakeConsole)
    p.onStartup()
    
    time.sleep(2)
    
    joe.connects(cid=1)
    
    joe.says('hola')
    joe.says('se van por >>>>>')
    joe.says('ayuda!!!')
    joe.says('que haces???')
    joe.says('hola hola \\')
    joe.says('a donde vas. epa?')
    joe.says('==> ->><=+??!')
