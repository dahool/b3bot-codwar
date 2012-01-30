#  BigBrotherBot(B3) (www.bigbrotherbot.net)
#  Plugin for allowing registered users to vote
#  Copyright (C) 2010 Sergio Gabriel Teves
#  Originaly developed by Ismal Garrido
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
# 2011-06-14 - 1.1.3
# Remove scheduller dependency
# 2011-06-25 - 1.1.4
# Fix issue with shuffle now
# 2011-06-29 - 1.1.5
# Fix shuffle message
# 2012-01-30 - 1.1.7
# Shuffle all players, even specs

__version__ = '1.1.7'
__author__  = 'SGT'

import sys
import b3
import b3.plugin
import b3.cron
import b3.events
from b3 import clients
from b3.functions import soundex, levenshteinDistance
import time, threading
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
    _lastmap_max = 5
    _current_cron = None
    
    # config
    _vote_times = 3
    _vote_interval = 600
    _minLevel_vote = 2
    _min_votes = 1
    _veto_level = 20
    _cancel_level = 40
    _rate = "*/15"
    
    _eventQueue = []
    
    def onStartup(self):
        self._eventQueue = []
        
        self.registerEvent(b3.events.EVT_GAME_WARMUP)
        self.registerEvent(b3.events.EVT_GAME_EXIT)
        self.createEvent('EVT_VOTEMAP_COMMAND', 'Vote Map Command')
    
    def addEvent(self, func):
        self._eventQueue.append(func)
        
    def loadPluginConfig(self):
        try:
            self._vote_times = self.config.getint('settings', 'vote_times')
        except:
            pass
        try:
            self._rate = "*/%d" % self.config.getint('settings', 'rate')
        except:
            pass
        try:
            self._vote_interval = self.config.getint('settings', 'vote_interval')
        except:
            pass
        try:
            self._minLevel_vote = self.config.getint('settings', 'min_level_vote')
        except:
            pass
        try:
            self._veto_level = self.config.getint('settings', 'veto_level')
        except:
            pass
        try:
            self._cancel_level = self.config.getint('settings', 'cancel_level')
        except:
            pass
        try:
            self._min_votes = self.config.getint('settings', 'min_votes')
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
        
        self._adminPlugin.registerCommand(self, 'voteyes', self._minLevel_vote,  self.cmd_voteyes,  'vy')
        self._adminPlugin.registerCommand(self, 'voteno', self._minLevel_vote, self.cmd_voteno,  'vn')
        self._adminPlugin.registerCommand(self, 'voteveto', self._veto_level, self.cmd_veto,  'vveto')
        self._adminPlugin.registerCommand(self, 'votecancel', self._cancel_level, self.cmd_cancel, 'vcancel')
        self._adminPlugin.registerCommand(self, 'maplist', self._minLevel_vote, self.cmd_maplist,  'mapl')

        for cmd in self.config.options('votes'):
            claz = self.config.get('votes', cmd)
            sp = cmd.split('-')
            alias = None
            if len(sp) == 2:
                cmd, alias = sp
            try:
                level = self.config.getint(cmd,'min_level_vote')
            except:
                level = self._minLevel_vote
            try:
                self.debug("Registering vote %s" % cmd)
                self._votes[cmd] = self.load_instance(claz)()
                self._votes[cmd].startup(self, self._adminPlugin,  self.console,  self.config, cmd)
                self._adminPlugin.registerCommand(self, cmd, level, self._votes[cmd].run_vote, alias)
            except Exception, e:
                self.error("Unable to load vote for %s" % cmd)
                raise
                
    def onEvent(self, event):
        if event.type == b3.events.EVT_GAME_WARMUP:
            self._cleanup(True)
            while len(self._eventQueue) > 0:
                func = self._eventQueue.pop()
                func()
        elif event.type == b3.events.EVT_GAME_EXIT:
            if len(self._lastmaps) == self._lastmap_max:
                self._lastmaps.pop(0)
            self._lastmaps.append(self.console.game.mapName)
            
    def _cleanup(self, init=False):
        if self._current_cron:
            self.console.cron - self._current_cron
        self.debug("Cleanning votes")
        self._in_progress = False
        self._currentVote = None
        self._current_cron = None
        if init:
            for vote in self._votes.values():
                vote.cleanup()
    
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
        if self._in_progress:
            client.message(self.getMessage('vote_in_progress'))
            return False
        
        hv = client.var(self, 'holding_vote').value
        if hv and hv > self.console.time():
            self.debug("Client cannot call a vote right now")
            client.message(self.getMessage('wait_vote'))
            return False
        return True

    def go_vote(self,  client):
        self._caller = client
        self._in_progress = True
        self._times = self._vote_times
        self._no = 0
        self._vetoed = 0
        self._yes = 1
        self._votedmark = 'voted_%s' % self.console.time()
        
        client.var(self, self._votedmark).value = True #The caller of the vote votes yes by default
        
        reason = self._currentVote.vote_reason()
        self.bot("Calling a vote " + reason)
        self.console.say(self.getMessage('call_vote', reason))
        self.console.say(self.getMessage('vote_notice'))
        self._current_cron = b3.cron.OneTimeCronTab(self.update_vote, self._rate)
        self.console.cron + self._current_cron

    def cmd_veto(self, data, client, cmd=None):
        """\
        veto current vote
        """      
        self.hold_vote()
        self._cleanup()
        self.bot("Vote vetoed")
        self.console.say(self.getMessage('vote_veto'))
        
    def cmd_cancel(self, data, client, cmd=None):
        """\
        cancel current vote and cleanup
        """
        self._cleanup()
        self.bot("Vote cancelled")
        self.console.say(self.getMessage('vote_cancel'))

    def update_vote(self):
        if not self._vetoed and self._in_progress:
            reason = self._currentVote.vote_reason()
            self.console.say(self.getMessage('voting', str(self._vote_times - self._times + 1), str(self._vote_times), reason))
            self.console.say(self.getMessage('vote_notice'))
            self.console.say(self.getMessage('vote_status', self._yes, self._no))
            self._times -= 1
            if self._times > 0:
                self._current_cron = b3.cron.OneTimeCronTab(self.update_vote, self._rate)
            else:
                self._current_cron = b3.cron.OneTimeCronTab(self.end_vote,  self._rate)
            self.console.cron + self._current_cron
        else:
            if self._in_progress:
                self.cmd_cancel(None, None)

    def hold_vote(self):
        if self._caller.maxLevel < self._admin_level:
            self._caller.var(self, 'holding_vote').value = self.console.time() + self._vote_interval
        
    def end_vote(self):
        self.console.say(self.getMessage('vote_end'))
        self.console.say(self.getMessage('vote_status', self._yes, self._no))
        self.bot("Vote results: Yes: %s^7, No: %s" %(self._yes,  self._no))
        if self._yes > self._no:
            self._currentVote.end_vote_yes(self._yes,  self._no)
        else:
            self._currentVote.end_vote_no(self._yes,  self._no)
            self.hold_vote()
        self._cleanup()

    def cmd_voteyes(self, data, client, cmd=None):
        """\
        vote yes
        """
        if self.vote(client,  cmd):
            if self._currentVote.vote_yes(client):
                self._yes += 1
                cmd.sayLoudOrPM(client, self.getMessage('vote_yes'))

    def cmd_voteno(self, data, client, cmd=None):
        """\
        vote no
        """
        if self.vote(client,  cmd):
            if self._currentVote.vote_no(client):
                self._no += 1
                cmd.sayLoudOrPM(client, self.getMessage('vote_no'))
    
    def vote(self,  client,  cmd):
        if self._in_progress:
            if not client.var(self, self._votedmark).value:
                client.var(self, self._votedmark).value = True
                return True
            else:
                cmd.sayLoudOrPM(client, self.getMessage('already_vote'))
        else:
            cmd.sayLoudOrPM(client, self.getMessage('no_vote'))
        return False

class Vote(object):
    _adminPlugin = None
    _parent = None
    console = None
    config = None
    
    def startup(self, parent, adminPlugin,  console,  config, cmd):
        """\
        Initialize plugin settings
        """
        self._parent = parent
        self._adminPlugin = adminPlugin
        self.console = console
        self.config = config
        try:
            self.min_votes = self.config.getint(cmd, 'min_votes')
        except:
            self.min_votes = self._parent._min_votes
    
    def vote_yes(self, client):
        return True

    def vote_no(self, client):
        return True
                
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
        
        self._parent.go_vote(client)
    
    def get_players_able_to_vote(self):
        return self.console.clients.getClientsByLevel(min=self._parent._minLevel_vote)
        
    def start_vote(self,  data,  client):
        return True

    def cleanup(self):
        return True
        
    def vote_reason(self):
        raise Exception('Not implemented.')

    def end_vote_yes(self,  yes,  no):
        raise Exception('Not implemented.')

    def end_vote_no(self,  yes,  no):
        raise Exception('Not implemented.')
        
class KickVote(Vote):
    _victim = None
    _caller = None
    _reason = None

    _tempban_interval = 0
    _tempban_percent    = 0
    _tempban_minvotes = 0

    def startup(self, parent, adminPlugin,  console,  config, cmd):
        super(KickVote, self).startup(parent, adminPlugin,  console,  config, cmd)

        self._tempban_percent_diff = self.config.getint('votekick', 'tempban_percent_diff')
        self._tempban_interval = self.config.getint('votekick', 'tempban_interval')
        self._tempban_percent = self.config.getint('votekick', 'tempban_percent')
        self._allow_spec = self.config.getint('votekick', 'allow_spec')
        
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
        self._victim = sclient
        self._reason = m[1]
        return True

    def vote_reason(self):
        return self._parent.getMessage('reason_kick', self._victim.exactName, self._reason)
    
    def end_vote_yes(self,  yes,  no):
        if yes < self.min_votes:
            self.console.say(self._parent.getMessage('novotes'))
            return
        if self._victim.connected:
            self._parent.bot("^1KICKING ^3%s" % self._victim.exactName)
            self.console.say("^1KICKING ^3%s" % self._victim.exactName)
            self._victim.kick("by popular vote (%s)" % self._reason,  None)

            player_count = int(round(len(self.get_players_able_to_vote()) * 
                                (self._tempban_percent / 100.0)))
            if (self._tempban_interval and (yes + no) >= player_count and
                yes >= int(round(((yes + no) * self._tempban_percent_diff / 100.0)))):
                self._victim.tempban("Voted out (%s)" % self._reason, duration=self._tempban_interval)
            self._victim = None

    def end_vote_no(self,  yes,  no):
        self.console.say(self._parent.getMessage('no_kick'))
        self._victim = None

class MapVote(Vote):
    _caller = None
    _map= None
        
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
                client.message('do you mean : %s' % string.join(match,', '))
                return False
            self._map = match[0]
            if self._map in self._parent._lastmaps:
                self._parent.bot("Map %s already played" % self._map)
                client.message(self._parent.getMessage('map_played', self._map))
                return False
            return True
        except Exception, e:
            client.message('^7%s' % str(e))
            return False

    def run_vote(self, data, client, cmd=None):
        """\
        <map> - call a vote to change map
        """
        super(MapVote, self).run_vote(data, client, cmd)
        
    def vote_reason(self):
        return self._parent.getMessage('reason_map', self._map)

    def end_vote_yes(self,  yes,  no):
        if (yes-no) < self.min_votes:
            self.console.say(self._parent.getMessage('novotes'))
            return
        self.console.queueEvent(self.console.getEvent('EVT_VOTEMAP_COMMAND', (self._map,), self.client))
        self._parent.bot("Changing map to %s" % self._map)
        self.console.say(self._parent.getMessage('change_map', self._map))
        time.sleep(1)
        self.console.write("map %s" %self._map)

    def end_vote_no(self,  yes,  no):
        self.console.say(self._parent.getMessage('no_map'))
    
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

    def cleanup(self):
        self._voted = False
        return True
        
    def vote_reason(self):
        return self._parent.getMessage('reason_nx_map', self._map)

    def end_vote_yes(self,  yes,  no):
        if yes < self.min_votes:
            self.console.say(self._parent.getMessage('novotes'))
            return
        self.console.queueEvent(self.console.getEvent('EVT_VOTEMAP_COMMAND', (self._map,), self.client))
        self._voted = True
        self._parent.bot("Changing next map to %s" % self._map)
        self.console.write( 'g_nextmap "%s"' % self._map)
        self.console.say(self._parent.getMessage('next_map', self._map))

    def end_vote_no(self,  yes,  no):
        map = self.console.getNextMap()
        if map:
            self.console.say(self._parent.getMessage('next_map_stay', map))

class ShuffleVote(Vote):

    _powerAdminPlugin = None
    _extraAdminPlugin = None
    shuffle_now = False
    
    def startup(self, parent, adminPlugin,  console,  config, cmd):
        super(ShuffleVote, self).startup(parent, adminPlugin,  console,  config, cmd)
        
        try:
            self.shuffle_now = self.config.getboolean('voteshuffle', 'shuffle_now')
        except:
            self.shuffle_now = False

        self._powerAdminPlugin = self.console.getPlugin('poweradminurt')
        if not self._powerAdminPlugin:
            self.console.debug('PowerAdmin not available')

        self._extraAdminPlugin = self.console.getPlugin('extraadmin')
        if not self._extraAdminPlugin:
            self.console.debug('Extra admin not available')

        self._shuffle_percent = self.config.getint('voteshuffle', 'shuffle_percent')
        self._shuffle_diff_percent = self.config.getint('voteshuffle', 'shuffle_diff_percent')
            
    def _doShuffle(self):
        self.console.say("^7Shuffling teams")
        self._parent.bot("Performing shuffle")
        if self.shuffle_now and self._powerAdminPlugin and hasattr(self._powerAdminPlugin,'cmd_paskuffle'):
            self._parent.debug("Using poweradmin shuffle")
            self._powerAdminPlugin.cmd_paskuffle(None, None, None)
        elif self._extraAdminPlugin:
            self._parent.debug("Using extraadmin shuffle")
            if self.shuffle_now:
                self._extraAdminPlugin.cmd_pashuffleteams(None,None,None)
            else:
                self._extraAdminPlugin.cmd_pashuffleteams('all',None,None)
        else:
            self._parent.debug("Using standard shuffle")
            self.console.write('shuffleteams')
        
    def _shuffle(self):
        self._parent.debug("Shuffle init timer")
        self.console.say("^7Shuffle is about to perfom. Waiting for players.")
        for i in range(30,0,-1):
            if i % 5 == 0:
                self.console.say("^7Performing shuffle in ^5%d ^7seconds." % i)
            self._parent.verbose("Wait %d" % i)
            time.sleep(1)
        self._doShuffle()
                     
    def run_vote(self, data, client, cmd=None):
        """\
        call a vote to shuffle teams on next round
        """
        super(ShuffleVote, self).run_vote(data, client, cmd)

    def vote_reason(self):
        if self.shuffle_now:
            return self._parent.getMessage('reason_shuffle_now')
        return self._parent.getMessage('reason_shuffle')

    def end_vote_yes(self,  yes,  no):
        if yes < self.min_votes:
            self.console.say(self._parent.getMessage('novotes'))
            return        
        player_count = int(round(len(self.get_players_able_to_vote()) * 
                            (self._shuffle_percent / 100.0)))
        if (yes + no) < player_count:
            self.console.say(self._parent.getMessage('cant_shuffle', str(player_count)))
        elif yes < int(round(((yes + no) * self._shuffle_diff_percent / 100.0))):
            self.console.say(self._parent.getMessage('cant_shuffle2', str(self._shuffle_diff_percent)))
        else:
            if self.shuffle_now:
                self._parent.bot("Will try shuffle now")
                self._doShuffle()
            else:
                self._parent.bot("Will try shuffle in next round")
                self.console.say(self._parent.getMessage('shuffle'))
                self._parent.addEvent(self._shuffle)

    def end_vote_no(self,  yes,  no):
        self.console.say(self._parent.getMessage('no_shuffle'))

class CycleMapVote(Vote):

    def run_vote(self, data, client, cmd=None):
        """\
        call a vote to cycle maps
        """
        super(CycleMapVote, self).run_vote(data, client, cmd)

    def vote_reason(self):
        return self._parent.getMessage('reason_cycle')

    def end_vote_yes(self,  yes,  no):
        if yes < self.min_votes:
            self.console.say(self._parent.getMessage('novotes'))
            return
        self._parent.bot("Cycling map")
        self.console.say(self._parent.getMessage('cycle'))
        time.sleep(1)
        self.console.write('cyclemap')

    def end_vote_no(self,  yes,  no):
        self.console.say(self._parent.getMessage('no_map'))

class MuteVote(Vote):
    _victim = None
    _caller = None
    _victimCanVote = False
    
    def startup(self, parent, adminPlugin,  console,  config, cmd):
        super(MuteVote, self).startup(parent, adminPlugin,  console,  config, cmd)
        self._victimCanVote = self.config.getboolean('votemute', 'allow_victim_to_vote')
        
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

    def _check_can_vote(self, client):
        if not self._victimCanVote and client.id == self._victim.id:
            client.message(self._parent.getMessage('cant_vote'))
            return False
        return True
        
    def vote_yes(self, client):
        self._check_can_vote(client)

    def vote_no(self, client):
        self._check_can_vote(client)
        
    def vote_reason(self):
        return self._parent.getMessage('reason_mute', self._victim.exactName)
    
    def end_vote_yes(self,  yes,  no):
        if yes < self.min_votes:
            self.console.say(self._parent.getMessage('novotes'))
            return
        if self._victim.connected:
            self._parent.bot("^1MUTE ^3%s" % self._victim.exactName)
            self.console.say("^1MUTE ^3%s" % self._victim.exactName)
            self.console.write('mute %s %s' % (self._victim.cid, ''))
            self._victim = None

    def end_vote_no(self,  yes,  no):
        self.console.say(self._parent.getMessage('failed_vote'))
        self._victim = None

if __name__ == '__main__':
    from b3.fake import fakeConsole
    from b3.fake import superadmin, reg, admin
 
    fakeConsole.setCvar('g_mapcycle','mapcycle.txt')
    setattr(fakeConsole.game,'fs_basepath','/home/gabriel/.q3a')
    setattr(fakeConsole.game,'fs_game','q3ut4')

    p = Voting2GPlugin(fakeConsole, '@b3/extplugins/conf/voting2g.xml')
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
