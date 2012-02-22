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
# 08-01-2012 - 1.0.6
# Use multi inserts
# 14-01-2012 - 1.0.7
# Update on shutdown
# 14-01-2012 - 1.0.8
# Make table compatible with chatlogger by Courgette (as of 1.1.3)
# 22-02-2012 - 1.0.9
# Remove color tags

__version__ = '1.0.9'
__author__  = 'SGT'

import b3
import b3.plugin
import b3, time, thread, threading
import re
import b3.cron

class ChatloggerPlugin(b3.plugin.Plugin):
    '''
    CREATE TABLE `chatlog` (
      `id` int(11) unsigned NOT NULL auto_increment,
      `msg_time` int(10) unsigned NOT NULL,
      `msg_type` enum('ALL','TEAM','PM') NOT NULL,
      `client_id` int(11) unsigned NOT NULL,
      `client_name` varchar(32) NOT NULL,
      `client_team` tinyint(1) NOT NULL,
      `msg` varchar(528) NOT NULL,
      `target_id` int(11) unsigned default NULL,
      `target_name` varchar(32) default NULL,
      `target_team` tinyint(1) default NULL,
      PRIMARY KEY  (`id`),
      KEY `client` (`client_id`),
      KEY `target` (`target_id`),
      KEY `time_add` (`msg_time`)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8;
    '''
    
    requiresConfigFile = False
    
    _TABLE = 'chatlog'
    
    _TEAM_NAME = {-1: 'UNKNOWN',
                 1: 'SPEC',
                 2: 'RED',
                 3: 'BLUE'}
    
    _MAX_DUMP_LINES = 150
    
    _crontab = None
    _interval = 15
    
    def onStartup(self):
        self.registerEvent(b3.events.EVT_STOP)
        self.registerEvent(b3.events.EVT_CLIENT_SAY)
        self.registerEvent(b3.events.EVT_CLIENT_TEAM_SAY)
        self.registerEvent(b3.events.EVT_CLIENT_PRIVATE_SAY)
        
        self._chatdata = ChatData(self)
        
        if self._crontab:
            self.console.cron - self._crontab
        self._crontab = b3.cron.PluginCronTab(self, self._chatdata.save, minute='*/%d' % self._interval)
        self.console.cron + self._crontab
        
    def onEvent(self,  event):
        if event.type == b3.events.EVT_STOP:
            self.info('B3 stop/exit.. force dump')
            self._chatdata.save()
        elif event.type == b3.events.EVT_CLIENT_SAY:
            self._chatdata.addMessage(ChatMessage(event))
        elif event.type == b3.events.EVT_CLIENT_TEAM_SAY:
            self._chatdata.addMessage(TeamChatMessage(event))
        elif event.type == b3.events.EVT_CLIENT_PRIVATE_SAY:
            self._chatdata.addMessage(PrivateChatMessage(event))

class ChatData:
    
    _INSERT_QUERY_M_HEAD = "INSERT INTO {table_name} (msg_time, msg_type, client_id, client_name, client_team, msg, target_id, target_name, target_team) VALUES "
    _chat_list = []
    
    def __init__(self, plugin):
        self.plugin = plugin
        self._insert_query = self._INSERT_QUERY_M_HEAD.format(table_name=self.plugin._TABLE)
        
    def addMessage(self, chat_message):
        self._chat_list.append(str(chat_message))

    def save(self):
        if len(self._chat_list) > 0:
            lista = self._chat_list[:]
            del self._chat_list[0:len(lista)]
            self.plugin.debug("Saving %d chat lines" % len(lista))
            while len(lista) > 0:
                tmplst = lista[:self.plugin._MAX_DUMP_LINES]
                del lista[:self.plugin._MAX_DUMP_LINES]
                insertsql = """%s""" % (self._insert_query + ",".join(tmplst))
                self.plugin.verbose(insertsql)
                if self.plugin.console.__class__.__name__ == 'FakeConsole': continue
                try:
                    cursor = self.plugin.console.storage.query(insertsql)
                except Exception, e:
                    self.plugin.warning("Could not save to database: [%s]" % str(e))
    
class ChatMessage:
    
    _ALLOW_CHARS = re.compile('[^\w\?\+\*\.,:=_\(\)\$\#!><-]')
    _COLOR = re.compile(r'\^[0-9]')
    _INSERT_QUERY_M_TAIL = "(%(time)s, \"%(type)s\", %(client_id)s, \"%(client_name)s\",%(client_team)s, \"%(msg)s\", %(target_id)s, \"%(target_name)s\", %(target_team)s)"
    
    msg_type = 'ALL' # ALL, TEAM or PM
    client_id = None
    client_name = None
    client_team = None
    msg = None
    
    def __init__(self, event):
        self.client_id = event.client.id
        self.client_name = event.client.name
        self.client_team = event.client.team
        self.msg = self._sanitize(event.data) 
        self.target_id = None
        self.target_name = None
        self.target_team = None
        
    def _sanitize(self, text):
        return self._ALLOW_CHARS.sub(' ',self._COLOR.sub('',text)).strip()
                
    def __str__(self):
        data = {'time': int(time.time()), 
         'type': self.msg_type, 
         'client_id': self.client_id, 
         'client_name': self.client_name, 
         'client_team': self.client_team,
         'msg': self.msg,
         'target_id': self.target_id, 
         'target_name': self.target_name, 
         'target_team': self.target_team
         }
        return (self._INSERT_QUERY_M_TAIL % data).replace("\"None\"","null").replace("None","null")

class TeamChatMessage(ChatMessage):
    msg_type = 'TEAM'
    
class PrivateChatMessage(ChatMessage):
    msg_type = 'PM'
    
    def __init__(self, event):
        ChatMessage.__init__(self, event)
        self.target_id = event.target.id
        self.target_name = event.target.name
        self.target_team = event.target.team
        
if __name__ == '__main__':
    from b3.fake import FakeClient, fakeConsole, joe, simon
    import time
    
    def sendsPM(self, msg, target):
        print "\n%s PM to %s : \"%s\"" % (self.name, msg, target)
        self.console.queueEvent(b3.events.Event(b3.events.EVT_CLIENT_PRIVATE_SAY, msg, self, target))
    FakeClient.sendsPM = sendsPM    

    p = ChatloggerPlugin(fakeConsole)
    p.onStartup()
    
    time.sleep(2)
    
    joe.connects(1)
    simon.connects(3)
    
    joe.says("sql injec;tion ' test")
    joe.sendsPM("sql; injection ' test", simon)
    joe.says("!help sql injection ' test;")

    joe.name = "j'oe"
    simon.name = "s;m'n"

    joe.says("sql injection test2")
    joe.sendsPM("sql injection test2", simon)
    joe.says("!help sql injection test2")
    joe.says("holas \" como va")
    
    joe.name = "Joe"
    simon.name = "Simon"
    
    joe.says("hello")
    simon.says2team("team test")
    joe.sendsPM("PM test", simon)
    
    time.sleep(5)
    
    p._chatdata.save()
    
    time.sleep(30)

