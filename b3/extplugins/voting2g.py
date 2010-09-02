# BigBrotherBot(B3) (www.bigbrotherbot.com)
# Plugin for allowing registered users to vote
# Copyright (C) 2010 Sergio Gabriel Teves
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

__version__ = '1.0.5'
__author__  = 'SGT'

import sys
import b3
import b3.plugin
import b3.cron
import b3.events
from b3 import clients
from b3 import maplist
import time
from b3.extrafunctions import ShuffleMaster

class Voting2GPlugin(b3.plugin.Plugin):
    _adminPlugin = None
    _currentVote = None
    
    _caller = None

    _in_progress = False
    _yes = 0
    _no = 0
    _vetoed = 0
    _times = 0
    _vote_times = 3
    _vote_interval = 0

    _votes = {}
    
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
        
        self.registerEvent(b3.events.EVT_GAME_WARMUP)
        self.createEvent('EVT_VOTEMAP_COMMAND', 'Vote Map Command')

        self._vote_times = self.config.getint('settings', 'vote_times')
        self._vote_interval = self.config.getint('settings', 'vote_interval')
        self._minLevel_vote = self.config.getint('settings', 'min_level_vote')
        self._veto_level = self.config.getint('settings', 'veto_level')
        self._cancel_level = self.config.getint('settings', 'cancel_level')
        self._min_votes = self.config.getint('settings', 'min_votes')
        self._admin_level = self._adminPlugin.config.getint('settings','admins_level')
        
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

    def _cleanup(self, init=False):
        self.debug("Cleanning votes")
        self._in_progress = False
        self._currentVote = None
        if init:
            for vote in self._votes.values():
                vote.cleanup()
    
    def load_instance(self, claz):
        modname = globals()['__name__']
        mod = sys.modules[modname]
        return getattr(mod,claz)
        
    def cmd_maplist(self,  data,  client,  cmd=None):
        """\
        list maps available to vote
        """
        client.message("Maps available: " + ", ".join(maplist.listCycleMaps(self.console)))
    
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
        self.console.cron + b3.cron.OneTimeCronTab(self.update_vote,  "*/1")

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
                self.console.cron + b3.cron.OneTimeCronTab(self.update_vote,  "*/1")
            else:
                self.console.cron + b3.cron.OneTimeCronTab(self.end_vote,  "*/1")
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
            self._yes += 1
            cmd.sayLoudOrPM(client, self.getMessage('vote_yes'))

    def cmd_voteno(self, data, client, cmd=None):
        """\
        vote no
        """
        if self.vote(client,  cmd):
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
            self.bot("^1KICKING ^3%s" % self._victim.exactName)
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
            self._map = maplist.findMap(self.console, data)
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
        if yes < self.min_votes:
            self.console.say(self._parent.getMessage('novotes'))
            return
        self.console.queueEvent(self.console.getEvent('EVT_VOTEMAP_COMMAND', (self._map,), self.client))
        self.bot("Changing map to %s" % self._map)
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
        self.bot("Changing next map to %s" % self._map)
        self.console.write( 'g_nextmap "%s"' % self._map)
        self.console.say(self._parent.getMessage('next_map', self._map))

    def end_vote_no(self,  yes,  no):
        map = self.console.getNextMap()
        if map:
            self.console.say(self._parent.getMessage('next_map_stay', map))

class ShuffleVote(Vote):

    def startup(self, parent, adminPlugin,  console,  config, cmd):
        super(ShuffleVote, self).startup(parent, adminPlugin,  console,  config, cmd)
        self._schedullerPlugin = self.console.getPlugin('eventscheduller')
        if not self._schedullerPlugin:
            self.error('Could not find scheduller plugin')
            return False
        self._extraAdminPlugin = self.console.getPlugin('extraadmin')
        if not self._extraAdminPlugin:
            self.debug('Extra admin not available')
            
#        if not self._shuffleMaster:
#            self._shuffleMaster = ShuffleMaster(console)

        self._shuffle_percent = self.config.getint('voteshuffle', 'shuffle_percent')
        self._shuffle_diff_percent = self.config.getint('voteshuffle', 'shuffle_diff_percent')
    
    def _shuffle(self):
        if self._extraAdminPlugin:
            self._extraAdminPlugin.cmd_pashuffleteams(None,None,None)
        else:
            self.console.write('shuffleteams')
                     
    def run_vote(self, data, client, cmd=None):
        """\
        call a vote to shuffle teams on next round
        """
        super(ShuffleVote, self).run_vote(data, client, cmd)

    def vote_reason(self):
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
            self.bot("Shuffling")
            self.console.say(self._parent.getMessage('shuffle'))
            self._schedullerPlugin.add_event(b3.events.EVT_GAME_WARMUP,self._shuffle)

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
        self.bot("Cycling map")
        self.console.say(self._parent.getMessage('cycle'))
        time.sleep(1)
        self.console.write('cyclemap')

    def end_vote_no(self,  yes,  no):
        self.console.say(self._parent.getMessage('no_map'))
