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
# 2011-02-20 - 1.0.1 - SGT
# Add bigtext before complete
# 2011-02-21 - 1.0.2 - SGT
# Reload config command
# 2011-05-04 - 1.0.3 - SGT
# fix issue when no objetive is set
# 2012-05-27 - 1.0.4 - SGT
# on game exit and warmup sometimes takes to long

__version__ = '1.0.4'
__author__  = 'SGT'

import b3, threading, time, thread
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
    _teamName = {'red': '^1Red', 'blue': '^4Blue'}
    _variable = None
    _announced = False
    _cronTab = None
    
    def onStartup(self):
        self.registerEvent(b3.events.EVT_CLIENT_ACTION)
        self.registerEvent(b3.events.EVT_GAME_WARMUP)
        self.registerEvent(b3.events.EVT_GAME_EXIT)

        self._adminPlugin = self.console.getPlugin('admin')
        if not self._adminPlugin:
            self.error('Could not find admin plugin')
            return False

        admin_level = self._adminPlugin.config.getint('settings', 'admins_level')
        
        self._adminPlugin.registerCommand(self, 'objective', 0, self.cmd_displayobjectives, 'ob')
        self._adminPlugin.registerCommand(self, 'obreload', admin_level, self.cmd_reloadobjectives, None)
        
        self.console.cron + b3.cron.OneTimeCronTab(self.loadConfigs, '*/30')
        
    def loadConfigs(self):
        self.debug('Loading configs')
        c = self.console.game
        
        if c.gameType == None:
            self.debug('Unable to determine current gametype')
            self.console.cron + b3.cron.OneTimeCronTab(self.loadConfigs, '*/15')
            return
            
        self._gameType = c.gameType
        self._configs = {}
        try:
            self._default = self.config.getint('default',self._gameType)
            self._variable = self.config.get('settings',self._gameType)
            self._current = self._default
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
                self._teamName['blue']="^4%s" % name
            except:
                pass
            try:
                name = self.console.getCvar('g_teamnamered').getString()
                self._teamName['red']="^1%s" % name
            except:
                pass
            # set objetives for current map
            self.setCurrentMapObjective()
        
    def onEvent(self, event):
        if self._default:
            if (self.console.game.gameType == 'ctf' and
                event.type == b3.events.EVT_CLIENT_ACTION):
                thread.start_new_thread(self.ctfAction, (event.data,))
            if event.type == b3.events.EVT_GAME_WARMUP:
                self._announced = False
                thread.start_new_thread(self.onGameWarmup, (event, ))
            elif event.type == b3.events.EVT_GAME_EXIT and not event.data:
                thread.start_new_thread(self.showMapEnd, ())
             
    def onGameWarmup(self, event):
        self.setCurrentMapObjective()
        t1 = threading.Timer(20, self.showMapObjective)
        t1.start()        
        
    def bigtext(self, msg):
        self.console.write('bigtext "%s"' % (msg))
        
    def ctfAction(self, data):
        if data == 'flag_captured':
            red, blue = self.get_scores()
            if self._announced:
                if red == blue:
                    time.sleep(1)
                    self.bigtext(self.getMessage('tie'))
            else:
                if (self._current - red) == 1:
                    t = 'red'
                elif (self._current - blue) == 1:
                    t = 'blue'
                else:
                    t = None
                if t:
                    time.sleep(1)
                    self.bigtext(self.getMessage('announce', self._teamName[t]))
                    self._announced = True
    
    def cmd_reloadobjectives(self, data, client, cmd=None):
        self.loadConfigs()
        client.message("^7%d objectives" % len(self._configs))
                        
    def cmd_displayobjectives(self, data, client, cmd=None):
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
        
    def get_scores(self):
        scores = self.console.getCvar('g_teamScores')
        if scores:
            red, blue = scores.getString().split(":")
        else:
            red, blue = (0,0)
        return int(red), int(blue)
        
    def showMapEnd(self):
        self.debug("showMapEnd")
        if self._current:
            red, blue = self.get_scores()
            if red == self._current:
                t = 'red'
            elif blue == self._current:
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

################################ TESTS #############################
if __name__ == '__main__':
    
    ############# setup test environment ##################
    from b3.fake import FakeConsole, FakeClient
    from b3.parsers.iourt41 import Iourt41Parser
   
    ## inherits from both FakeConsole and Iourt41Parser
    class FakeUrtConsole(FakeConsole, Iourt41Parser):
        pass
   
    class UrtClient():
        def takesFlag(self):
            if self.team == b3.TEAM_BLUE:
                print "\n%s takes red flag" % self.name
                self.doAction('team_CTF_redflag')
            elif self.team == b3.TEAM_RED:
                print "\n%s takes blue flag" % self.name
                self.doAction('team_CTF_blueflag')
        def returnsFlag(self):
            print "\n%s returns flag" % self.name
            self.doAction('flag_returned')
        def capturesFlag(self):
            print "\n%s captures flag" % self.name
            self.doAction('flag_captured')
       
    ## use mixins to add methods to FakeClient
    FakeClient.__bases__ += (UrtClient,)
  
    fakeConsole = FakeUrtConsole('/local/codwar/io2/b3.xml')
    fakeConsole.startup()

    fakeConsole.game.gameType = 'ctf'
    fakeConsole.game.mapName = 'ut4_turnpike'
    fakeConsole.setCvar("g_teamScores","0:0")
    
    p = ObjectivePlugin(fakeConsole, '/local/codwar/bot/b3/extplugins/conf/objective.xml')
    p.onStartup()
    p.loadConfigs()
    
    from b3.fake import joe, simon
    joe.team = b3.TEAM_BLUE
    simon.team = b3.TEAM_RED
    joe.console = fakeConsole
    simon.console = fakeConsole
    ############# END setup test environment ##################

    joe.connects(cid=1)
    simon.connects(cid=2)
    
    print "================= ROUND 1 ==================="
    
    time.sleep(1)
    fakeConsole.queueEvent(b3.events.Event(b3.events.EVT_GAME_WARMUP, None))
    time.sleep(10)
    p._current = 4
    joe.says('!ob')
    
    fakeConsole.setCvar("g_teamScores","1:0")
    simon.capturesFlag()
    time.sleep(0.5)
    print fakeConsole.getCvar("g_teamScores")
    
    fakeConsole.setCvar("g_teamScores","1:1")
    joe.capturesFlag()
    time.sleep(0.5)
    print fakeConsole.getCvar("g_teamScores")

    fakeConsole.setCvar("g_teamScores","2:1")    
    simon.capturesFlag()
    time.sleep(0.5)
    print fakeConsole.getCvar("g_teamScores")

    fakeConsole.setCvar("g_teamScores","3:1")    
    simon.capturesFlag()
    time.sleep(0.5)
    print fakeConsole.getCvar("g_teamScores")

    fakeConsole.setCvar("g_teamScores","3:2")    
    joe.capturesFlag()
    time.sleep(0.5)
    print fakeConsole.getCvar("g_teamScores")

    fakeConsole.setCvar("g_teamScores","3:3")    
    joe.capturesFlag()
    time.sleep(0.5)
    print fakeConsole.getCvar("g_teamScores")

    fakeConsole.setCvar("g_teamScores","4:3")    
    simon.capturesFlag()
    time.sleep(0.5)
    print fakeConsole.getCvar("g_teamScores")
    
    fakeConsole.queueEvent(b3.events.Event(b3.events.EVT_GAME_EXIT, None))
    time.sleep(1)
