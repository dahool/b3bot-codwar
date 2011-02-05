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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
# CHANGELOG
#     2011/02/05 - 1.0 - SGT
#    * Initial version

__author__  = 'SGT'
__version__ = '1.0'


import b3
import b3.events
import b3.plugin

class MessengerPlugin(b3.plugin.Plugin):
    requiresConfigFile = False
    _adminPlugin = None
    _admin_level = 20
    _limit_to_spec = True
    
    def onStartup(self):
        
        self._adminPlugin = self.console.getPlugin('admin')
        if not self._adminPlugin:
            return False

        self._adminPlugin.registerCommand(self, 'telladmin', 1, self.cmd_telladmin)
        self._adminPlugin.registerCommand(self, 'tell', 1, self.cmd_tell)

    def _can_use(self, client):
        if self._limit_to_spec and client.team == b3.TEAM_SPEC:
            client.message('^7You have to be spectator to use this command')
            return False
        return True
        
    def cmd_tell(self, data, client, cmd=None):
        """\
        <name> <message> - send a private message to a player
        """
        if not self._can_use(client):
            return False
            
        input = self._adminPlugin.parseUserCmd(data)
        if not input or len(input) <> 2:
            client.message('^7Invalid data, try !help tell')
            return False
        
        sclient = self._adminPlugin.findClientPrompt(input[0], client)
        sclient.message('^5[PM] ^2%s^7: %s' % (client.name, input[1]))
        
        return True 
        
    def cmd_telladmin(self, data, client, cmd=None):
        """\
        <message> - send a private message to all connected admins
        """
        if not self._can_use(client):
            return False
            
        input = self._adminPlugin.parseUserCmd(data)
        if not input:
            client.message('^7Invalid data, try !help tell')
            return False
        
        clients = self.console.clients.getList()
        for c in clients:
            if c.maxLevel >= self._admin_level:
                c.message('^5[PM] ^2%s^7: %s' % (client.name, input[0]))

        return True 
           
if __name__ == '__main__':
    from b3.fake import fakeConsole
    from b3.fake import joe, simon, moderator, superadmin
    import time
    
    p = MessengerPlugin(fakeConsole)
    p.onStartup()
    
    joe.connects(cid=1)
    simon.connects(cid=2)
    moderator.connects(cid=3)
    superadmin.connects(cid=4)
    
    joe.says('!tell 2 hola')
    print "-------------------------"
    joe.says('!telladmin ayuda')
    print "-------------------------"
    
