#
# Mirror Plugin for BigBrotherBot(B3) (www.bigbrotherbot.com)
# Copyright (C) 2010 Sergio Gabriel Teves
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

__version__ = '1.0.0'
__author__  = 'SGT'

import b3, time, thread, threading, re
import b3.events
import b3.plugin
import b3.cron
from b3.functions import soundex, levenshteinDistance

import os
import random
import string
import traceback

class MirrorPlugin(b3.plugin.Plugin):
    '''/
    This plugin will mirror any listed command to the user who call it
    when it is done against an upper level user
    '''

    _adminPlugin = None

    def onStartup(self):
        self._adminPlugin = self.console.getPlugin('admin')

        if not self._adminPlugin:
            self.warning('Could not find admin plugin')
        else:
            self.registerEvent(b3.events.EVT_ADMIN_COMMAND)
        
    def onLoadConfig(self):
        try:
            self._cmd_list = self.config.get('settings', 'commands').split(',')
        except:
            self._cmd_list = []

        if len(self._cmd_list)==0:
            self.error("Command list is empty")

    def onEvent(self,  event):
        if event.type == b3.events.EVT_ADMIN_COMMAND:
            command, data, res = event.data
            if command.command in self._cmd_list:
                if self._adminPlugin and data:
                    cid, params = self._adminPlugin.parseUserCmd(data)
                    cli = self._adminPlugin.findClientPrompt(cid)
                    if cli and cli.maxLevel > event.client.maxLevel:
                        world = self._adminPlugin.findClientPrompt("@1")
                        event.client.message("^7You've been mirrored n00b")
                        if len(params)>0:
                            data = "%s %s" % (event.client.cid, params)
                        else:
                            data = event.client.cid
                        command.execute(data, world)
                        self.bot("Mirrored %s to %s against %s" % (command.command, event.client.name, cli.name))
                        
if __name__ == '__main__':
    print '\nThis is version '+__version__+' by '+__author__+' for BigBrotherBot.\n'
