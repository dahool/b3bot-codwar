# BigBrotherBot(B3) (www.bigbrotherbot.com)
# Plugin for registering nicknames
# Copyright (C) 2009 Ismael Garrido
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
# CHANGELOG
# 01/30/12 - SGT
# Make comparision case insensitive
# 01/06/11 - SGT
# Handle event in new thread
# Improve code
# 03/03/11 - SGT
# Case insensitive filter
# 26/10/09  - SGT
# small change to support b3 web control
# 17/10/09 - SGT
# Add multinick support
# 25/08/09
# Escape player's nicks
# 25/07/09
# Initial version

__version__ = '1.4'
__author__  = 'Ismael, SGT'

import b3
import b3.plugin
from b3 import clients
import b3.cron
import thread

class NickregPlugin(b3.plugin.Plugin):
    _adminPlugin = None
    _color_re = re.compile(r'\^[0-9]')
    _watched = []

    def onStartup(self):
        """\
        Initialize plugin settings
        """
        # get the plugin so we can register commands
        self._adminPlugin = self.console.getPlugin('admin')
        if not self._adminPlugin:
            # something is wrong, can't start without admin plugin
            self.error('Could not find admin plugin')
            return False
        
        self._adminPlugin.registerCommand(self, 'registernick', self.level, self.cmd_regnick,  'regnick')
        self._adminPlugin.registerCommand(self, 'deletenick', self.level, self.cmd_delnick,  'delnick')
        self._adminPlugin.registerCommand(self, 'listnick', self.level, self.cmd_listnick)
        
        self.registerEvent(b3.events.EVT_CLIENT_NAME_CHANGE)

    def onLoadConfig(self):
        self.level = self.config.getint('settings', 'min_level_reg')
        self.maxnicks = self.config.getint('settings', 'max_nicks')
        
    def onEvent(self,  event):
        if event.type == b3.events.EVT_CLIENT_NAME_CHANGE:
            thread.start_new_thread(self.onNameChange, (event.client,))
        
    def onNameChange(self, client):
        if not client or \
            not client.id or \
            client.cid == None or \
            client.pbid == 'WORLD':
            return

        if client.id not in self._watched:
            cursor = self.console.storage.query("""
            SELECT n.clientid
            FROM nicks n 
            WHERE n.name like '%s'
            """ % (self._process_name(client.name))) #Have to escape quotes (')
            
            if cursor.rowcount > 0: #This nick is registered
                r = cursor.getRow()

                if int(r['clientid']) != int(client.id):
                    self._watched.append(client.id)
                    #This nick isn't yours!
                    name = client.name
                    id = client.id
                    client.message("^2Primer aviso: ^7El nombre ^7%s pertenece a otro usuario." % name)
                    
                    #Messy logic ahead! Each defined function adds a cron for the next one, defined inside of them.
                    def warn():
                        client.message("^2Segundo aviso: ^7Cambia tu nombre, pertenece a otro usuario.")
                        def warn2():
                            if self._normalize(name) == self._normalize(client.name):
                                client.message("^1ULTIMO Aviso: ^7Cambia tu nombre. ^7Seras ^1expulsado!")
                                def kick():
                                    if self._normalize(name) == self._normalize(client.name):
                                        client.kick("This nickname isn't yours!",  data=name)
                                    self._watched.remove(client.id)
                                self.console.cron + b3.cron.OneTimeCronTab(kick,  "*/5")
                        self.console.cron + b3.cron.OneTimeCronTab(warn2,  "*/5")
                    self.console.cron + b3.cron.OneTimeCronTab(warn,  "*/5")
            cursor.close()
                            
    def cmd_listnick(self, data, client, cmd=None):
        """\
        <name> - list registered nicknames
        """
        cursor = self.console.storage.query("""
            SELECT n.nickid,n.name
            FROM nicks n
            WHERE n.clientid = %s
            """ % (client.id))
        
        if cursor.rowcount == 0:
            client.message('^7You don\'t have any registered nick name')
            return False
        
        names = []
        while not cursor.EOF:
            g = cursor.getRow()
            names.append("[%s] %s" % (g['nickid'],g['name']))
            cursor.moveNext()
        cursor.close()
        
        client.message('^7Registered nick names: %s' % ', '.join(names))
        
    def _normalize(self, text):
        return self._color_re.sub('',text).lower()
        
    def _process_name(self, data):
        return self._color_re.sub(data.replace("""'""", """''"""))
        
    def cmd_regnick(self, data, client, cmd=None):
        """\
        Register current name as yours
        """
        
        #Todo: Strip the colors from the names?
        #Todo: Strip the spaces?
        
        cursor = self.console.storage.query("""
        SELECT n.name
        FROM nicks n 
        WHERE n.name like '%s'
        """ % (self._process_name(client.name))) #Have to escape quotes (')
        
        if cursor.rowcount > 0:
            client.message('^7Nick %s is already registered' % client.name)
            return False
        cursor.close()

        cursor = self.console.storage.query("""
        SELECT n.nickid
        FROM nicks n 
        WHERE n.clientid = %s
        """ % (client.id))
        
        if cursor.rowcount > self.maxnicks:
            client.message('^7You already have %d registered nicks' % self.maxnicks)
            return False
        cursor.close()

        cursor = self.console.storage.query("""
        SELECT max(n.nickid) as maxid FROM nicks n
        WHERE n.clientid = %s
        """ % (client.id))
        max = cursor.getRow()['maxid']
        cursor.close()
        if max is None:
           max = 1
        else:
           max = long(max)+1

        query = "INSERT INTO nicks (nickid, clientid, name, time_add) VALUES ('%d', '%d', '%s',  '%d')" % (max, client.id, self._process_name(client.name), self.console.time())
        self.debug(query)
        cursor = self.console.storage.query(query)

        cursor.close()
        client.message('^7Your nick is now registered')
    
    def cmd_delnick(self,  data,  client,  cmd=None):
        '''\
        <nickid> - delete selected nick
        '''
        
        if not data or not data.isdigit():
            if client:
                client.message('^7Invalid or missing data, try !help delnick')
            else:
                self.debug('No data sent to cmd_delnick')
            return False
              
        cursor = self.console.storage.query("""
        SELECT n.name
        FROM nicks n 
        WHERE n.clientid = %s AND n.nickid = %s
        """ % (client.id,data))
        
        if cursor.rowcount == 0:
            client.message("^7The nick %s doesn't belongs to you" % data)
            return False
        else:
            name = cursor.getRow()['name']

        cursor.close()
        
        cursor = self.console.storage.query("""
        DELETE FROM nicks
        WHERE nickid = %s AND clientid = %s
        """ % (data, client.id))
        cursor.close()
        client.message("^7Deleted nick %s" % name)
