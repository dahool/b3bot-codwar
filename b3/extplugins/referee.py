#
# BigBrotherBot(B3) (www.bigbrotherbot.com)
# Copyright (C) 2010 Sergio Gabriel Teves
# Referee plugin for b3 bot
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
# CHANGELOG
# 02/17/2010 - 1.0.0 - SGT
# Initial

__author__  = 'SGT'
__version__ = '1.0.0'

import b3, os, time
import b3.plugin
import b3.events

class RefereePlugin(b3.plugin.Plugin):
    '''
    CREATE TABLE IF NOT EXISTS `referee` (
      `id` int(11) NOT NULL auto_increment,
      `client_id` int(11) NOT NULL,
      `admin_id` int(11) NOT NULL,
      `time_add` int(11) NOT NULL,
      PRIMARY KEY  (`id`),
      KEY `following_client_id` (`client_id`),
      KEY `following_admin_id` (`admin_id`)
    ) ENGINE=MyISAM  DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci AUTO_INCREMENT=1;
    '''
    _adminPlugin = None
    _commands = []
    _min_level = 1
    _min_level_add = 80
    _confpath = None
    
    _SELECT_QUERY = "SELECT client_id FROM referee WHERE client_id = %s"
    _DEL_QUERY = "DELETE FROM referee WHERE client_id = %s"
    _ADD_QUERY = "INSERT INTO referee (client_id, admin_id, time_add) VALUES ('%s','%s',%d)"
    _LIST_QUERY = "SELECT client_id FROM referee"
    
    def onStartup(self):
        if self._adminPlugin:
            self._adminPlugin.registerCommand(self, 'ref', self._min_level, self.cmd_ref)
            self._adminPlugin.registerCommand(self, 'loadconf', self._min_level_add, self.cmd_loadconf)
            self._adminPlugin.registerCommand(self, 'addref', self._min_level_add, self.cmd_addref)
            self._adminPlugin.registerCommand(self, 'delref', self._min_level_add, self.cmd_delref)
            self._adminPlugin.registerCommand(self, 'listref', self._min_level_add, self.cmd_listref)

    def onLoadConfig(self):
        self._adminPlugin = self.console.getPlugin('admin')
        self._commands = self.config.get('settings', 'commands').split(',')
        self._min_level = self.config.getint('settings', 'min_level')
        self._min_level_add = self.config.getint('settings', 'min_level_add')
        self._confpath = self.config.get('settings', 'config_path')

    def isreferee(self, client):
        cursor = self.console.storage.query(self._SELECT_QUERY % client.id)
        if cursor.rowcount > 0:
            cursor.close()
            return True
        cursor.close()
        return False
        
    def cmd_listref(self, data, client, cmd=None):
        """\
        list referees
        """         
        cursor = self.console.storage.query(self._LIST_QUERY)
        if cursor.rowcount == 0:
            client.message("^7The list is empty.")
            cursor.close()
            return False

        names = []
        while not cursor.EOF:
            r = cursor.getRow()
            c = self.console.storage.getClientsMatching({ 'id' : r['client_id'] })
            if c:
                names.append("^7[^2@%s^7] %s" % (c[0].id,c[0].name))
            else:
                self.error("Not found client matching id %s" % r['client_id'])
            cursor.moveNext()
        cursor.close()
        client.message(', '.join(names))

    def cmd_addref(self, data, client, cmd=None):
        """\
        <name> - add user to the referee list
        """        
        m = self._adminPlugin.parseUserCmd(data)
        if not m:
            client.message('^7Invalid parameters')
            return False

        sclient = self._adminPlugin.findClientPrompt(m[0], client)
        
        if not sclient:
            return False
            
        cursor = self.console.storage.query(self._SELECT_QUERY % sclient.id)
        if cursor.rowcount == 0:
            cursor2 = self.console.storage.query(self._ADD_QUERY % (sclient.id, client.id, self.console.time()))
            cursor2.close()
            self.debug("User added to database")
            client.message("^7The user has been added to the referee list.")
        else:
            self.debug("User already in database")
            client.message("^7User already exists in referee list.")
        cursor.close() 
        
    def cmd_delref(self, data, client, cmd=None):
        """\
        <name> - remove user from the referee list
        """        
        m = self._adminPlugin.parseUserCmd(data)
        if not m:
            client.message('^7Invalid parameters')
            return False

        sclient = self._adminPlugin.findClientPrompt(m[0], client)
        cursor = self.console.storage.query(self._DEL_QUERY % sclient.id)
        cursor.close()
        self.debug("User removed from database")
        client.message("^7User removed from the referee list.")

    def cmd_loadconf(self, data, client=None, cmd=None):
        '''loadconf
        '''
        if not data:
            client.message('^7Invalid or missing data')
            return False
        if os.path.exists(os.path.join(self._confpath,data + '.cfg')):
            f = open(os.path.join(self._confpath,data + '.cfg'),'r')
            while f:
                line = f.readline().strip()
                self.console.write('%s' % line)
            f.close()
            client.message('^%s loaded.' % data)
        else:
            client.message('^Invalid config name.')
        
    def cmd_ref(self, data, client=None, cmd=None):
        '''referee
        '''
        if self.console.getCvar('g_matchmode').getInt() <> 1:
            client.message('^7Only available in match mode.')
            return
            
        self.debug('Referee %s wants to run "%s"' % (client.name,data))
        if self.isreferee(client):
            try:
                dat = data.split(' ')
                cmd = dat[0]
                data = ' '.join(dat[1:])
                func = self._commands[cmd.lower()]
                func(data, client)
            except Exception, e:
                self.error(e)
                client.message('^7Invalid command.')
        else:
            client.message('^7You cannot use this command.')
