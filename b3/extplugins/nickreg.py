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
# 26/10/09  - SGT
# small change to support b3 web control
# 17/10/09 - SGT
# Add multinick support
# 25/08/09
# Escape player's nicks
# 25/07/09
# Initial version

__version__ = '1.1'
__author__  = 'Ismael'

import b3
import b3.plugin
from b3 import clients
import b3.cron

class NickregPlugin(b3.plugin.Plugin):
    _adminPlugin = None

    _watched = []

    def startup(self):
        """\
        Initialize plugin settings
        """

        # get the plugin so we can register commands
        self._adminPlugin = self.console.getPlugin('admin')
        if not self._adminPlugin:
            # something is wrong, can't start without admin plugin
            self.error('Could not find admin plugin')
            return False
        
        minlevel = self.config.getint('settings', 'min_level_reg')
        self.maxnicks = self.config.getint('settings', 'max_nicks')
        
        self._adminPlugin.registerCommand(self, 'registernick', minlevel, self.cmd_regnick,  'regnick')
        self._adminPlugin.registerCommand(self, 'deletenick', minlevel, self.cmd_delnick,  'delnick')
        self._adminPlugin.registerCommand(self, 'listnick', minlevel, self.cmd_listnick)
        self.registerEvent(b3.events.EVT_CLIENT_NAME_CHANGE)

    def onEvent(self,  event):
        if not event.client:
            return #No client
        if not event.client.authed:
            return #Not authed, don't know its real ID
        client = event.client
        if client.id not in self._watched:
            cursor = self.console.storage.query("""
            SELECT n.clientid
            FROM nicks n 
            WHERE n.name = '%s'
            """ % (self._process_name(client.name))) #Have to escape quotes (')
            if cursor.rowcount > 0: #This nick is registered
                r = cursor.getRow()

                if int(r['clientid']) != int(client.id):
                    self._watched.append(client.id)
                    #This nick isn't yours!
                    name = client.name
                    id = client.id
                    client.message("^2First warn: ^7Please change your ^7nickname, ^7this nick belongs to someone else")
                    
                    #Messy logic ahead! Each defined function adds a cron for the next one, defined inside of them.
                    def warn():
                        client.message("^2Second warn: ^7Please change your ^7nickname, ^7this nick belongs to someone else")
                        def warn2():
                            if  name == client.name:
                                client.message("^1LAST warn: ^7Please change your ^7nickname, ^7this nick belongs to someone else. ^7You will be ^1KICKED!")
                                def kick():
                                    if  name == client.name:
                                        client.kick("This nickname isn't yours!",  None)
                                    self._watched.remove(client.id)
                                self.console.cron + b3.cron.OneTimeCronTab(kick,  "*/4")
                        self.console.cron + b3.cron.OneTimeCronTab(warn2,  "*/3")
                    self.console.cron + b3.cron.OneTimeCronTab(warn,  "*/4")
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
        
    def _process_name(self, data):
        return data.replace("""'""", """''""")
        
    def cmd_regnick(self, data, client, cmd=None):
        """\
        Register current name as yours
        """
        
        #Todo: Strip the colors from the names?
        #Todo: Strip the spaces?
        
        cursor = self.console.storage.query("""
        SELECT n.name
        FROM nicks n 
        WHERE n.name = '%s'
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
