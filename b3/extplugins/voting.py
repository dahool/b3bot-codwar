# BigBrotherBot(B3) (www.bigbrotherbot.com)
# Plugin for allowing registered users to kick
# Copyright (C) 2009 Ismael Garrido
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
# 24/12/2009 SGT
# Try to fix orphans votes
# 01/10/2009 SGT
# add !votenextmap (vx)
# 28/09/2009 SGT
# change map list fetch
# 25/07/09
# Added !votemap
# Revamped the system, more modular now.
# 12/06/09
# !vk requires a reason to kick
# If more than a certain percent of voters vote yes, the victim is tempbanned
# added !vkveto
# Modlevel is read from admin plugin settings (thanks Bakes)
# 30/05/09
# Added delays between failed votes
# Initial version

__version__ = '1.5.2'
__author__  = 'Ismael'

import b3
import b3.plugin
import b3.cron
import b3.events
from b3 import clients
from b3 import maplist
import time

class VotingPlugin(b3.plugin.Plugin):
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
        
        self.registerEvent(b3.events.EVT_GAME_ROUND_START)

        self._vote_times = self.config.getint('settings', 'vote_times')
        self._vote_interval = self.config.getint('settings', 'vote_interval')
        minLevel_vote = self.config.getint('settings', 'min_level_vote')
        modLevel = self._adminPlugin.config.getint("settings","admins_level")  
        
        self._adminPlugin.registerCommand(self, 'voteyes', minLevel_vote,  self.cmd_voteyes,  'vy')
        self._adminPlugin.registerCommand(self, 'voteno', minLevel_vote, self.cmd_voteno,  'vn')
        self._adminPlugin.registerCommand(self, 'voteveto', modLevel, self.cmd_veto,  'vveto')
        self._adminPlugin.registerCommand(self, 'votecancel', modLevel, self.cmd_cancel, 'vcancel')

        minLevel_kick = self.config.getint('votekick', 'min_level_kick')
        self._adminPlugin.registerCommand(self, 'votekick', minLevel_kick, self.cmd_votekick,  'vk')

        self._votes["kick"] = KickVote()
        self._votes["kick"].startup(self._adminPlugin,  self.console,  self.config)

        minLevel_map = self.config.getint('votemap', 'min_level_map')
        self._adminPlugin.registerCommand(self, 'votemap', minLevel_map, self.cmd_votemap,  'vm')
        self._adminPlugin.registerCommand(self, 'maplist', minLevel_map, self.cmd_maplist,  'mapl')
        self._votes["map"] = MapVote()
        self._votes["map"].startup(self._adminPlugin,  self.console,  self.config)

        minLevel_nextmap = self.config.getint('votenextmap', 'min_level_map')
        self._adminPlugin.registerCommand(self, 'votenextmap', minLevel_nextmap, self.cmd_votenextmap,  'vx')

        self._votes["nextmap"] = NextMapVote()
        self._votes["nextmap"].startup(self._adminPlugin,  self.console,  self.config)


    def onEvent(self, event):
        if event.type == b3.events.EVT_GAME_ROUND_START:
            self._in_progress = False
            self._currentVote = None

    def cmd_maplist(self,  data,  client,  cmd=None):
       client.message("Maps available: " + ", ".join(self._votes["map"].getMapList()))
    
    def pre_vote(self,  client):
        if self._in_progress:
            client.message("A vote is already in progress, wait until it finishes")
            return False
        
        if client.var(self,  'holding_vote').value:
            client.message("You have to wait between failed votes!")
            return False
        return True


    def cmd_votekick(self, data, client, cmd=None):
        """\
        <name> <reason> - call a votekick on that player for that reason
        """
        if not self.pre_vote(client):
            return False
        
        self._currentVote = self._votes["kick"]
        
        if not self._currentVote.start_vote(data,  client):
            return False
        
        self.go_vote(client)

    def cmd_votemap(self, data, client, cmd=None):
        """\
        <map> - call a votemap for that map
        """
        if not self.pre_vote(client):
            return False
        
        self._currentVote = self._votes["map"]

        if not self._currentVote.start_vote(data,  client):
            return False
        
        self.go_vote(client)

    def cmd_votenextmap(self, data, client, cmd=None):
        """\
        <map> - call a votenextmap for that map
        """
        if not self.pre_vote(client):
            return False

        self._currentVote = self._votes["nextmap"]

        if not self._currentVote.start_vote(data,  client):
            return False

        self.go_vote(client)
        
    def go_vote(self,  client):
        self._caller = client
        self._in_progress = True
        self._times = self._vote_times
        self._no = 0
        self._vetoed = 0
        
        self._yes = 1
        client.var(self,  'voted').value = True #The caller of the vote votes yes by default
        
        reason = self._currentVote.vote_reason()
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
        #if self._yes > 1 and self._yes > self._no:
        if self._yes > self._no:
            self._currentVote.end_vote_yes(self._yes,  self._no)
        else:
            self._currentVote.end_vote_no(self._yes,  self._no)
            #The vote failed, the caller can't call another vote for a while
            self._caller.var(self, 'holding_vote').value = True
            self._caller.var(self, 'voted').value = False
            temp = self._caller
            def let_caller_vote():
                self.debug("clearing %s" % temp.exactName)
                temp.var(self,  'holding_vote').value = False
            
            self.console.cron + b3.cron.OneTimeCronTab(let_caller_vote,  0, "*/%s" % self._vote_interval)
        
        self._in_progress = False
        self._currentVote = None
    
        for c in self.console.clients.getList():
            c.var(self,  'voted').value = False

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
            if not client.var(self,  'voted').value:
                client.var(self,  'voted').value = True
                return True
            else:
                cmd.sayLoudOrPM(client,  "You already voted!")
        else:
            cmd.sayLoudOrPM(client,  "No vote in progress")
        return False

class KickVote(object):
    _adminPlugin = None
    console = None
    config = None
    
    _victim = None
    _caller = None
    _reason = None

    _modLevel = 20

    _tempban_interval = 0
    _tempban_percent    = 0
    _tempban_minvotes = 0

    def startup(self,  adminPlugin,  console,  config):
        """\
        Initialize plugin settings
        """

        self._adminPlugin = adminPlugin
        self.console = console
        self.config = config

        self._modLevel = self._adminPlugin.config.getint("settings","admins_level")  
        
        self._tempban_minvotes = self.config.getint('votekick', 'tempban_minvotes')
        self._tempban_interval = self.config.getint('votekick', 'tempban_interval')
        self._tempban_percent = self.config.getint('votekick', 'tempban_percent')
        
    def start_vote(self,  data,  client):
        m = self._adminPlugin.parseUserCmd(data)
        if not m:
            client.message('^7Invalid parameters')
            return False
        if not m[1]:
            client.message('^7Invalid parameters, must provide a reason!')
            return False            
        if len(m[1]) < 3:
            client.message("^7You should write a better reason")
        
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
        self.console.say("^1KICKING ^3%s" %self._victim.exactName)
        self._victim.kick("by popular vote",  None)
        if self._tempban_interval and (yes*100.0 / no) > self._tempban_percent and yes > self._tempban_minvotes:
            self._victim.tempban("", "Voted out", self._tempban_interval, None)
        self._victim = None

    def end_vote_no(self,  yes,  no):
        self.console.say("Player is ^2safe!")
        self._victim = None

class MapVote:
    _adminPlugin = None
    console = None
    config = None

    _caller = None
    _map= None

    def startup(self,  adminPlugin,  console,  config):
        """\
        Initialize plugin settings
        """

        self._adminPlugin = adminPlugin
        self.console = console
        self.config = config
        
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

    def getMapList(self):
        return maplist.listCycleMaps(self.console)
        
    def vote_reason(self):
        return "to change map to ^3%s" % (self._map)

    def end_vote_yes(self,  yes,  no):
        self.console.say("^1Changing map to ^3%s" %self._map)
        time.sleep(1)
        self.console.write("map %s" %self._map)

    def end_vote_no(self,  yes,  no):
        self.console.say("Map ^2stays!")
    
class NextMapVote(MapVote):

    def vote_reason(self):
        return "to set ^6next ^7map to ^3%s" % (self._map)

    def end_vote_yes(self,  yes,  no):
        self.console.write( 'g_nextmap "%s"' % self._map)
        self.console.say("^1Next map is ^3%s" %self._map)

    def end_vote_no(self,  yes,  no):
        map = self.console.getNextMap()
        if map:
            self.console.say("Next map stays in ^2%s" % map)
