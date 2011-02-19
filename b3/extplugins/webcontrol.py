#
# BigBrotherBot(B3) (www.bigbrotherbot.com)
# Plugin for extra webcontrol of privileged users
# Copyright (C) 2009 Sergio Gabriel Teves (info@sgtdev.com.ar)
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

__author__  = 'SGT'
__version__ = '1.0.0'

import md5, string

import b3
import b3.events
import b3.plugin
from b3.querybuilder import QueryBuilder

class WebcontrolPlugin(b3.plugin.Plugin):

    _pmcomm = ''
    
    def onLoadConfig(self):
        try:
            self.level = self.config.getint('settings', 'level')
        except:
            self.level = 80
            self.debug('Using default value (%i) for settings::level', self.level)

    def onStartup(self):
        self._adminPlugin = self.console.getPlugin('admin')

        if self._adminPlugin:
            self._adminPlugin.registerCommand(self, 'auth', self.level, self.cmd_auth)
            self._adminPlugin.registerCommand(self, 'setpassword', self.level, self.cmd_setpassword, secretLevel=1)
        else:
            self.error('No admin plugin.')
            
    # Whats the command to send a private message?
        if self.console.gameName[:5] == 'etpro':
            self._pmcomm = '/m'
        else:
            self._pmcomm = '/tell'
        self.debug('Using "%s" as the private messaging command' %self._pmcomm)

    def cmd_setpassword(self, data, client, cmd=None):
        """\
        <password> [<name>] - set a password for a client
        """
        data = string.split(data)
        if len(data) > 1:
            sclient = self._adminPlugin.findClientPrompt(data[1], client)
            if not sclient: return
            if client.maxLevel <= sclient.maxLevel and client.maxLevel < 100:
                client.message('You can only change passwords of yourself or lower level players.')
            return
        else:
            sclient = client

        sclient.password = md5.new(data[0]).hexdigest()
        self.console.storage.query(QueryBuilder(self.console.storage.db).UpdateQuery( { 'password' : sclient.password }, 'clients', { 'id' : sclient.id } ))
        client.message('Password set successfully')
        return

    def cmd_auth(self, data, client, cmd=None):
        """\
        <auth> [<name>] - set a login name for a client
        """
        if data:
            cursor = self.console.storage.query(QueryBuilder(self.console.storage.db).SelectQuery('*','clients', {'login': data}))
            if cursor.rowcount:
                while not cursor.EOF:
                    g = cursor.getRow()
                    if not g['id'] == client.id:
                        client.message('Username already registered. Choose another one.')
                        return
            self.console.storage.query(QueryBuilder(self.console.storage.db).UpdateQuery({'login': data}, 'clients', {'id': client.id} ))
            client.message('Your login name has been set.')
	    client.message('Open the console and type: \'%s %s !setpassword yourpassword\' to set your password' %(self._pmcomm, client.cid))
        else:
            client.message('Enter a login name. Type !help auth for more info.')

        return
