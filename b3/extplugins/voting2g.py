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

__version__ = '1.0.3'
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
        self.minLevel_vote = self.config.getint('settings', 'min_level_vote')
        modLevel = self._adminPlugin.config.getint('settings','admins_level')  
        
        self._adminPlugin.registerCommand(self, 'voteyes', self.minLevel_vote,  self.cmd_voteyes,  'vy')
        self._adminPlugin.registerCommand(self, 'voteno', self.minLevel_vote, self.cmd_voteno,  'vn')
        self._adminPlugin.registerCommand(self, 'voteveto', modLevel, self.cmd_veto,  'vveto')
        self._adminPlugin.registerCommand(self, 'votecancel', modLevel, self.cmd_cancel, 'vcancel')
        self._adminPlugin.registerCommand(self, 'maplist', self.minLevel_vote, self.cmd_maplist,  'mapl')

        for cmd in self.config.options('votes'):
            claz = self.config.get('votes', cmd)
            sp = cmd.split('-')
            alias = None
            if len(sp) == 2:
                cmd, alias = sp
            try:
                level = self.config.getint(cmd,'min_level_vote')
            except:
                level = self.minLevel_vote
            try:
                self.debug("Registering vote %s" % cmd)
                self._votes[cmd] = self.load_instance(claz)()
                self._votes[cmd].startup(self, self._adminPlugin,  self.console,  self.config)
                self._adminPlugin.registerCommand(self, cmd, level, self._votes[cmd].run_vote, alias)
            except Exception, e:
                self.error("Unable to load vote for %s" % cmd)
		raise
                
    def onEvent(self, event):
        if event.type == b3.events.EVT_GAME_WARMUP:
            self.debug("Cleanning votes")
            self._in_progress = False
            self._currentVote = None

    def load_instance(self, claz):
        modname = globals()['__name__']
        mod = sys.modules[modname]
        return getattr(mod,claz)
        
    def cmd_maplist(self,  data,  client,  cmd=None):
        client.message("Maps available: " + ", ".join(maplist.listCycleMaps(self.console)))
    
    def pre_vote(self,  client):
        if self._in_progress:
            client.message("A vote is already in progress, wait until it finishes")
            return False
        
        hv = client.var(self, 'holding_vote').value
        if hv and hv > self.console.time():
            self.debug("Client cannot call a vote right now")
            client.message("You have to wait between failed votes!")
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
        self.debug("Calling a vote " + reason)
        self.console.say("Calling a vote " + reason)
        self.console.say("Type ^1!vy ^7to vote ^1yes^7, ^2!vn ^7to vote ^2no")
        self.console.cron + b3.cron.OneTimeCronTab(self.update_vote,  "*/1")

    def cmd_veto(self, data, client, cmd=None):
        self._vetoed = 1

    def cmd_cancel(self, data, client, cmd=None):
        self._in_progress = False
        self._currentVote = None
        self.console.say("Vote ^1cancelled!")

    def update_vote(self):
        if not self._vetoed:
            reason = self._currentVote.vote_reason()
            self.console.say("^7[%d/%d] Voting " % (self._vote_times - self._times + 1,  self._vote_times) + reason)
            self.console.say("Type ^1!vy ^7to vote ^1yes^7, ^2!vn ^7to vote ^2no")
            self.console.say("^1Yes: %s^7, ^2No: %s" %(self._yes,  self._no))
            self._times -= 1
            if self._times > 0:
                self.console.cron + b3.cron.OneTimeCronTab(self.update_vote,  "*/1")
            else:
                self.console.cron + b3.cron.OneTimeCronTab(self.end_vote,  "*/1")
        else:
            self.cmd_cancel(None, None)
    
    def end_vote(self):
        self.console.say("Vote ended")
        self.console.say("^1Yes: %s^7, ^2No: %s" %(self._yes,  self._no))
        self.debug("Vote results: Yes: %s^7, No: %s" %(self._yes,  self._no))
        #if self._yes > 1 and self._yes > self._no:
        if self._yes > self._no:
            self._currentVote.end_vote_yes(self._yes,  self._no)
        else:
            self._currentVote.end_vote_no(self._yes,  self._no)
            #The vote failed, the caller can't call another vote for a while
            self._caller.var(self, 'holding_vote').value = self.console.time() + self._vote_interval
#            temp = self._caller
#            def let_caller_vote():
#                self.debug("clearing %s" % temp.exactName)
#                temp.var(self,  'holding_vote').value = False
            
#            self.console.cron + b3.cron.OneTimeCronTab(let_caller_vote,  0, "*/%s" % self._vote_interval)
        
        self._in_progress = False
        self._currentVote = None

    def cmd_voteyes(self, data, client, cmd=None):
        if self.vote(client,  cmd):
            self._yes += 1
            cmd.sayLoudOrPM(client,  "Voted ^1YES")

    def cmd_voteno(self, data, client, cmd=None):
        if self.vote(client,  cmd):
            self._no += 1
            cmd.sayLoudOrPM(client,  "Voted ^2NO")
    
    def vote(self,  client,  cmd):
        if self._in_progress:
            if not client.var(self, self._votedmark).value:
                client.var(self, self._votedmark).value = True
                return True
            else:
                cmd.sayLoudOrPM(client,  "You already voted!")
        else:
            cmd.sayLoudOrPM(client,  "No vote in progress")
        return False

class Vote(object):
    _adminPlugin = None
    _parent = None
    console = None
    config = None
    
    def startup(self, parent, adminPlugin,  console,  config):
        """\
        Initialize plugin settings
        """
        self._parent = parent
        self._adminPlugin = adminPlugin
        self.console = console
        self.config = config
    
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
        return self.console.clients.getClientsByLevel(min=self._parent.minLevel_vote)
        
    def start_vote(self,  data,  client):
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

    _modLevel = 20

    _tempban_interval = 0
    _tempban_percent    = 0
    _tempban_minvotes = 0

    def startup(self, parent, adminPlugin,  console,  config):
        super(KickVote, self).startup(parent, adminPlugin,  console,  config)

        self._modLevel = self._adminPlugin.config.getint("settings","admins_level")  
        
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
            client.message('^7Invalid parameters')
            return False
        if not m[1]:
            client.message('^7Invalid parameters, must provide a reason!')
            return False            
        if len(m[1]) < 2:
            client.message("^7You should write a better reason")
            return False
            
        cid = m[0]
        sclient = self._adminPlugin.findClientPrompt(cid, client)
        if not sclient:
            return False
            
        if sclient.maxLevel >= self._modLevel:
            client.message("You can't kick an admin!")
            return False
        
        self._caller = client
        self._victim = sclient
        self._reason = m[1]
        return True

    def vote_reason(self):
        return "against ^3%s because ^3%s" % (self._victim.exactName,  self._reason)
    
    def end_vote_yes(self,  yes,  no):
        self.console.say("^1KICKING ^3%s" % self._victim.exactName)
        self._victim.kick("by popular vote (%s)" % self._reason,  None)

        player_count = int(round(len(self.get_players_able_to_vote()) * 
                            (self._tempban_percent / 100.0)))
        if (self._tempban_interval and (yes + no) >= player_count and
            yes >= int(round(((yes + no) * self._tempban_percent_diff / 100.0)))):
            self._victim.tempban("Voted out (%s)" % self._reason, duration=self._tempban_interval)
        self._victim = None

    def end_vote_no(self,  yes,  no):
        self.console.say("Player is ^2safe!")
        self._victim = None

class MapVote(Vote):
    _caller = None
    _map= None
        
    def start_vote(self,  data,  client):
        m = self._adminPlugin.parseUserCmd(data)
        if not m:
            client.message('^7Invalid parameters')
            return False
        if not m[0]:
            client.message('^7Invalid parameters, must provide a map to vote!')
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
        return "to change map to ^3%s" % (self._map)

    def end_vote_yes(self,  yes,  no):
	if (yes==1):
	    self.console.say("^7Not enough votes for change map")
	    return
	self.console.queueEvent(self.console.getEvent('EVT_VOTEMAP_COMMAND', (self._map,), self.client))
        self.console.say("^1Changing map to ^3%s" % self._map)
        time.sleep(1)
        self.console.write("map %s" %self._map)

    def end_vote_no(self,  yes,  no):
        self.console.say("Map ^2stays!")
    
class NextMapVote(MapVote):

    def run_vote(self, data, client, cmd=None):
        """\
        <map> - call a vote to change next map
        """
        super(NextMapVote, self).run_vote(data, client, cmd)

    def vote_reason(self):
        return "to set ^6NEXT MAP ^7to ^3%s" % (self._map)

    def end_vote_yes(self,  yes,  no):
	self.console.queueEvent(self.console.getEvent('EVT_VOTEMAP_COMMAND', (self._map,), self.client))
        self.console.write( 'g_nextmap "%s"' % self._map)
        self.console.say("^1Next map is ^3%s" %self._map)

    def end_vote_no(self,  yes,  no):
        map = self.console.getNextMap()
        if map:
            self.console.say("Next map stays in ^2%s" % map)

class ShuffleVote(Vote):

    def startup(self, parent, adminPlugin,  console,  config):
        super(ShuffleVote, self).startup(parent, adminPlugin,  console,  config)
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
        return "to ^6shuffle teams ^3on NEXT MATCH"

    def end_vote_yes(self,  yes,  no):
        player_count = int(round(len(self.get_players_able_to_vote()) * 
                            (self._shuffle_percent / 100.0)))
        if (yes + no) < player_count:
            self.console.say("^7At least %d players should vote for shuffle" % player_count)
        elif yes < int(round(((yes + no) * self._shuffle_diff_percent / 100.0))):
            self.console.say("^7Sholud be at least %s%% of positive votes to shuffle" % self._shuffle_diff_percent)
        else:
            self.console.say("Teams will be shuffled at the start of the next match")
            #self._schedullerPlugin.add_event(b3.events.EVT_GAME_EXIT,self._shuffleMaster.compute_players)
            self._schedullerPlugin.add_event(b3.events.EVT_GAME_WARMUP,self._shuffle)

    def end_vote_no(self,  yes,  no):
        self.console.say("Teams will be kept as is.")

class CycleMapVote(Vote):

    def run_vote(self, data, client, cmd=None):
        """\
        call a vote to cycle maps
        """
        super(CycleMapVote, self).run_vote(data, client, cmd)

    def vote_reason(self):
        return "to ^6cycle map"

    def end_vote_yes(self,  yes,  no):
        self.console.say("^1Cycling map")
        time.sleep(1)
        self.console.write('cyclemap')

    def end_vote_no(self,  yes,  no):
        self.console.say("Map ^2stays!")
