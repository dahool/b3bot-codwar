#
# Objectives Plugin
# Copyright (C) 2011 Sergio Gabriel Teves
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
# 2011-02-18 - 1.0.0 - SGT
# Initial version

__version__ = '1.0.0'
__author__  = 'SGT'

import b3, threading, time
import b3.events
import b3.plugin
import b3.cron
import glob
import os
import re

#--------------------------------------------------------------------------------------------------
class ObjectivePlugin(b3.plugin.Plugin):

    _default = None
    _configs = {}
    _current = None
    _gameType = None
    _teamName = {'red': 'Red', 'blue': 'Blue'}
    _variable = None
    
    def onStartup(self):
        self.registerEvent(b3.events.EVT_GAME_WARMUP)
        self.registerEvent(b3.events.EVT_GAME_EXIT)

        self._adminPlugin = self.console.getPlugin('admin')
        if not self._adminPlugin:
            self.error('Could not find admin plugin')
            return False

        self._adminPlugin.registerCommand(self, 'objective', 0, self.cmd_displayobjetives, 'ob')
        
        self.console.cron + b3.cron.OneTimeCronTab(self.loadConfigs, '*/30')
        
    def loadConfigs(self):
        self.debug('Loading configs')
        self._configs = {}
        c = self.console.game
        
        if c.gameType == None:
            self.debug('Unable to determine current gametype')
            self.console.cron + b3.cron.OneTimeCronTab(self.loadConfigs, '*/15')
            return
            
        self._gameType = c.gameType
        try:
            self._default = self.config.getint('default',self._gameType)
            self._variable = self.config.get('settings',self._gameType)
        except:
            self.debug("Objectives disabled for %s" % self._gameType)
            self._default = None
        else:
            self.debug("Loading objectives for %s" % self._gameType)
            if self._gameType in self.config.sections():
                for map in self.config.options(self._gameType):
                    value = self.config.getint(self._gameType, map)
                    self._configs[map]=value
                    self.debug("Found config for map %s" % map)
            try:
                name = self.console.getCvar('g_teamnameblue').getString()
                self._teamName['blue']=name
            except:
                pass
            try:
                name = self.console.getCvar('g_teamnamered').getString()
                self._teamName['red']=name
            except:
                pass
        
    def onEvent(self, event):
        if self._default:
            if event.type == b3.events.EVT_GAME_WARMUP:
                self.setCurrentMapObjective()
                t1 = threading.Timer(10, self.showMapObjective)
                t1.start()            
            elif event.type == b3.events.EVT_GAME_EXIT:
                self.showMapEnd()
               
    def cmd_displayobjetives(self, data, client, cmd=None):
        """\
        Display current map objective
        """         
        if self._default and self._current:
            cmd.sayLoudOrPM(client, self.getMessage(self._gameType, self._current))
        else:
            client.message(self.getMessage('disabled'))
    
    def findObjective(self, map):
        self.debug("findObjective")
        if map in self._configs:
            self._current = self._configs[map]
        else:
            self._current = self._default
        self.console.setCvar(self._variable,self._current)
    
    def setNextMapObjective(self):
		try:
			m = self.console.getNextMap()
			self.findObjective(m)
		except:
			self.error("Couldn't get next map")
        
    def setCurrentMapObjective(self):
        c = self.console.game
        self.findObjective(c.mapName)
        
    def showMapEnd(self):
        self.debug("showMapEnd")
        if self._current:
            scores = self.console.getCvar('g_teamScores')
            if scores:
                red, blue = scores.getString().split(":")
                if int(red) == self._current:
                    t = 'red'
                elif int(blue) == self._current:
                    t = 'blue'
                else:
                    t = None
                if t:
                    self.console.say(self.getMessage('done', self._teamName[t]))
                else:
                    self.console.say(self.getMessage('failed'))
            self.setNextMapObjective()
            
    def showMapObjective(self):
        self.debug("showMapObjective")
        self.console.say(self.getMessage(self._gameType, self._current))
