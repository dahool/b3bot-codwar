#  BigBrotherBot(B3) (www.bigbrotherbot.net)
#  This plugin will allow to raise votes only to authorized users
#  Copyright (C) 2011 Sergio Gabriel Teves
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
# 2010-01-10
# This plugins is rewrite of the one written by Ismael Garrido
# Initial version
# 2010-02-05
# Update shuffle votes to add min percent
# add players able to vote
# 2010-06-07
# Minor fix on clear event
# Some flags changes
# Add cyclemap vote
# Change shuffle func
# 2010-06-14 - 1.0.4
# Next map can be issued one time per map
# 2010-08-30 - 1.0.5
# Admins should be allowed to vote again
# Add min positive votes params
# Configurable messages
# 2010-12-21 - 1.0.7
# Updated rate to work with new cron from 1.4.1
# 2011-01-25 - 1.0.8
# Destroy cron on cleanup
# 2011-01-27 - 1.0.9
# Add vote mute
# 2011-02-02 - 1.0.10
# Add option to allow a spec not be kicked
# 2011-02-11 - 1.0.11
# Some reworks
# 2011-03-11 - 1.0.13
# Fix issue with some loggings
# 2011-03-19 - 1.1.0
# Move custom functions to avoid external libs requeriments
# Use shuffe now when scheduller plugin is not available
# 2011-03-21 - 1.1.1
# Fix imports
# 2011-05-24 - 1.2.0
# Use integrated voting system

__version__ = '1.2.0'
__author__  = 'SGT'

import sys
import b3
import b3.plugin
import b3.cron
import b3.events
from b3 import clients
from b3.functions import soundex, levenshteinDistance
import time
import string

class Voting2GPlugin(b3.plugin.Plugin):
    _adminPlugin = None
    _currentVote = None
    
    _caller = None

    _in_progress = False
    _yes = 0
    _no = 0
    _vetoed = 0
    _times = 0

    _votes = {}
    _lastmaps = []
    _lastmap_max = 3
    _current_cron = None
    
    _vote_interval = 600
    
    def onStartup(self):
        self.registerEvent(b3.events.EVT_GAME_WARMUP)
        self.registerEvent(b3.events.EVT_GAME_EXIT)
        self.createEvent('EVT_VOTEMAP_COMMAND', 'Vote Map Command')

    def loadPluginConfig(self):
        try:
            self._level = self.config.getint('settings', 'vote_level')
        except:
            pass
        try:
            self._vote_interval = self.config.getint('settings', 'vote_interval')
        except:
            pass
        
    def onLoadConfig(self):
        """\
        Initialize plugin settings
        """

        # get the plugin so we can register commands
        self._adminPlugin = self.console.getPlugin('admin')
        if not self._adminPlugin:
            # something is wrong, can't start without admin plugin
            self.error('Could not find admin plugin')
            return False

        self._admin_level = self._adminPlugin.config.getint('settings','admins_level')
        
        self.loadPluginConfig()
        
        self._adminPlugin.registerCommand(self, 'maplist', self._minLevel_vote, self.cmd_maplist,  'mapl')

        for cmd in self.config.options('votes'):
            claz = self.config.get('votes', cmd)
            sp = cmd.split('-')
            alias = None
            if len(sp) == 2:
                cmd, alias = sp
            try:
                self.debug("Registering vote %s" % cmd)
                self._votes[cmd] = self.load_instance(claz)()
                self._votes[cmd].startup(self, self._adminPlugin,  self.console, cmd)
                self._adminPlugin.registerCommand(self, cmd, level, self._votes[cmd].run_vote, alias)
            except Exception, e:
                self.error("Unable to load vote for %s" % cmd)
                raise
                
    def onEvent(self, event):
        if event.type == b3.events.EVT_GAME_EXIT:
            if len(self._lastmaps) == self._lastmap_max:
                self._lastmaps.pop(0)
            self._lastmaps.append(self.console.game.mapName)
            
    def load_instance(self, claz):
        modname = globals()['__name__']
        mod = sys.modules[modname]
        return getattr(mod,claz)
        
    def getMapList(self):
        try:
            from b3 import maplist
        except:
            self.debug("Using alternative map list method")
            maps = self.console.getMaps()
        else:
            maps = maplist.listCycleMaps(self.console)
        return maps
        
    def cmd_maplist(self,  data,  client,  cmd=None):
        """\
        list maps available to vote
        """
        if not self._adminPlugin.aquireCmdLock(cmd, client, 60, True):
            client.message('^7Do not spam commands')
            return
        maps = self.getMapList()
        cmd.sayLoudOrPM(client, "Maps: " + ", ".join(maps))
    
    def pre_vote(self,  client):
        if self._in_progress <= self.console.time():
            client.message(self.getMessage('vote_in_progress'))
            return False
        
        hv = client.var(self, 'holding_vote').value
        if hv and hv > self.console.time():
            self.debug("Client cannot call a vote right now")
            client.message(self.getMessage('wait_vote'))
            return False
        return True

    def go_vote(self,  client, vote):
        self._caller = client
        self._in_progress = self.console.time() + 40
        self.bot("Calling a vote %s" % vote)
        self.console.write('callvote %s' % vote)
        self.console.say(self.getMessage('call_vote', self._currentVote.vote_reason()))
        self.hold_vote()

    def hold_vote(self):
        if self._caller.maxLevel < self._admin_level:
            self._caller.var(self, 'holding_vote').value = self.console.time() + self._vote_interval

class Vote(object):
    _adminPlugin = None
    _parent = None
    console = None
    _vote = None
    _reason = None
    _caller = None
    
    def startup(self, parent, adminPlugin,  console,  cmd):
        """\
        Initialize plugin settings
        """
        self._parent = parent
        self._adminPlugin = adminPlugin
        self.console = console
    
    def run_vote(self, data, client, cmd=None):
        """
        call a vote
        """
        if not self._parent.pre_vote(client):
            return False
        
        self._parent._currentVote = self
        self.client = client

        if not self.start_vote(data,  client):
            return False
        
        self._parent.go_vote(client, self.vote_cmd())
    
    def start_vote(self,  data,  client):
        return True
        
    def vote_cmd(self):
        return None
        
    def vote_reason(self):
        return False
             
class KickVote(Vote):

    _victim = None
    _allow_spec = 0

    def run_vote(self, data, client, cmd=None):
        """\
        <name> <reason> - call a votekick on 'player' for 'reason'
        """
        super(KickVote, self).run_vote(data, client, cmd)
        
    def start_vote(self,  data,  client):
        m = self._adminPlugin.parseUserCmd(data)
        if not m:
            client.message(self._parent.getMessage('param_invalid'))
            return False
        if not m[1]:
            client.message(self._parent.getMessage('param_invalid_reason'))
            return False            
        if len(m[1]) < 2:
            client.message(self._parent.getMessage('param_invalid_reason2'))
            return False
            
        cid = m[0]
        sclient = self._adminPlugin.findClientPrompt(cid, client)
        if not sclient:
            return False
            
        if sclient.maxLevel >= self._parent._admin_level:
            client.message(self._parent.getMessage('cant_kick'))
            return False

        if self._allow_spec > 0:
            if sclient.team == b3.TEAM_SPEC:
                c = self.console.clients.getList()
                if len(c) < self._allow_spec:
                    client.message(self._parent.getMessage('cant_kick_spec'))
                    return False

        self._caller = client
        self._reason = self._parent.getMessage('reason_kick', self.sclient.exactName, m[1])
        self._victim = sclient
        return True

    def vote_cmd(self):
        return 'kick %d' % self._victim.cid

    def vote_reason(self):
        return self._reason
        
class MapVote(Vote):

    _map = None
    
    def getMapsSoundingLike(self, mapname, client=None):
        maplist = self._parent.getMapList()
                
        data = mapname.strip()

        soundex1 = soundex(string.replace(string.replace(data, 'ut4_',''), 'ut_',''))

        match = []
        if data in maplist:
            match = [data]
        else:
            for m in maplist:
                s = soundex(string.replace(string.replace(m, 'ut4_',''), 'ut_',''))
                if s == soundex1:
                    match.append(m)

        if len(match) == 0:
        # suggest closest spellings
            shortmaplist = []
            for m in maplist:
                if m.find(data) != -1:
                    shortmaplist.append(m)
            if len(shortmaplist) > 0:
                shortmaplist.sort(key=lambda map: levenshteinDistance(data, string.replace(string.replace(map.strip(), 'ut4_',''), 'ut_','')))
                self._parent.debug("shortmaplist sorted by distance : %s" % shortmaplist)
                match = shortmaplist[:3]
            else:
                maplist.sort(key=lambda map: levenshteinDistance(data, string.replace(string.replace(map.strip(), 'ut4_',''), 'ut_','')))
                self._parent.debug("maplist sorted by distance : %s" % maplist)
                match = maplist[:3]
            # we have the list sorted by distance. check if the first one match
            if len(match)>1:
                if string.replace(string.replace(match[0].lower(), 'ut4_',''), 'ut_','') == data.lower():
                    return match[0]
        
        return match
        
    def start_vote(self,  data,  client):
        m = self._adminPlugin.parseUserCmd(data)
        if not m:
            client.message(self._parent.getMessage('param_invalid'))
            return False
        if not m[0]:
            client.message(self._parent.getMessage('param_invalid_map'))
            return False
        s = m[0]
        try:
            match = self.getMapsSoundingLike(data, client)
            if len(match) > 1:
                client.message('quiso decir: %s' % string.join(match,', '))
                return False
            _map = match[0]
            if _map in self._parent._lastmaps:
                self._parent.bot("Map %s already played" % _map)
                client.message(self._parent.getMessage('map_played', _map))
                return False
            
            self._map = _map
            return True
        except Exception, e:
            client.message('^7%s' % str(e))
            return False
    
    def vote_cmd(self):
        return 'map %s' % self._map
            
    def vote_reason(self):
        return self._parent.getMessage('reason_map', _map)
            
class NextMapVote(MapVote):

    _voted = None
    
    def run_vote(self, data, client, cmd=None):
        """\
        <map> - call a vote to change next map
        """
        if self._voted:
            client.message(self._parent.getMessage('nx_map_done'))
            return False

        super(NextMapVote, self).run_vote(data, client, cmd)
    
    def vote_cmd(self):
        return 'g_nextmap %s' % self._map
        
    def vote_reason(self):
        return self._parent.getMessage('reason_nx_map', self._map)

class ShuffleVote(Vote):

    def run_vote(self, data, client, cmd=None):
        """\
        call a vote to shuffle teams on next round
        """
        super(ShuffleVote, self).run_vote(data, client, cmd)

    def vote_cmd(self):
        return 'shuffleteams'

    def vote_reason(self):
        return self._parent.getMessage('reason_shuffle_now')

class CycleMapVote(Vote):

    def run_vote(self, data, client, cmd=None):
        """\
        call a vote to cycle maps
        """
        super(CycleMapVote, self).run_vote(data, client, cmd)

    def vote_cmd(self):
        return 'cyclemap'

    def vote_reason(self):
        return self._parent.getMessage('reason_cycle')

class MuteVote(Vote):
    _victim = None
    
    def start_vote(self,  data,  client):
        m = self._adminPlugin.parseUserCmd(data)
        if not m:
            client.message(self._parent.getMessage('param_invalid'))
            return False
            
        cid = m[0]
        sclient = self._adminPlugin.findClientPrompt(cid, client)
        if not sclient:
            return False
            
        if sclient.maxLevel >= self._parent._admin_level:
            client.message(self._parent.getMessage('cant_mute'))
            return False
        
        self._caller = client
        self._victim = sclient
        return True

    def vote_cmd(self):
        return "mute %d ''" % self._victim.cid

if __name__ == '__main__':
    from b3.fake import fakeConsole
    from b3.fake import superadmin, reg, admin
 
    fakeConsole.setCvar('g_mapcycle','mapcycle.txt')
    setattr(fakeConsole.game,'fs_basepath','/home/gabriel/.q3a')
    setattr(fakeConsole.game,'fs_game','q3ut4')

    p = Voting2GPlugin(fakeConsole, '@b3/extplugins/conf/urtvote.xml')
    p.onStartup()
    
    superadmin.connects(cid=1)
    reg.connects(cid=2)
    admin.connects(cid=3)
    time.sleep(2)
    superadmin.says("!maplist")
    time.sleep(2)
    admin.says("!votemap ut4_turnpike")
    time.sleep(1)
    reg.says("!vy")
