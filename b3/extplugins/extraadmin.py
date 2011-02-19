#
# PowerAdmin Plugin for BigBrotherBot(B3) (www.bigbrotherbot.com)
# Copyright (C) 2009 Sergio Gabriel Teves
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
# 04-25-2010 - SGT
# add cmd_groups removed from admin since 1.3
# 04-22-2010 - SGT
# Make independent of poweradmin
# 04-05-2010 - SGT
# Add bandetail
# 02-01-2010 - SGT
# Change GAME_START event for WARMUP
# 03-13-2010 - SGT
# Random team shuffle

__version__ = '1.1.4'
__author__  = 'SGT'

import b3, time, thread, threading, re
import b3.events
import b3.plugin
import b3.cron
from b3.functions import soundex, levenshteinDistance
from b3 import clients

import os
import random
import string
import traceback
import datetime

#--------------------------------------------------------------------------------------------------
class ExtraadminPlugin(b3.plugin.Plugin):

    def onStartup(self):
        self._nextMap = None
        self._currentMap = self.console.game.mapName
        
        # get the admin plugin so we can register commands
        self._adminPlugin = self.console.getPlugin('admin')
        if not self._adminPlugin:
            # something is wrong, can't start without admin plugin
            self.error('Could not find admin plugin')
            return False
        self._padminPlugin = self.console.getPlugin('poweradminurt')
        if not self._padminPlugin:
            self.error('Could not find power admin plugin')
            self._padminPlugin = None
            
        # register our commands
        if 'commands' in self.config.sections():
            for cmd in self.config.options('commands'):
                level = self.config.get('commands', cmd)
                sp = cmd.split('-')
                alias = None
                if len(sp) == 2:
                    cmd, alias = sp

                func = self.getCmd(cmd)
                if func:
                    self._adminPlugin.registerCommand(self, cmd, level, func, alias)
            
        self.registerEvent(b3.events.EVT_GAME_WARMUP)
        self.registerEvent(b3.events.EVT_GAME_ROUND_START)
        self.registerEvent(b3.events.EVT_SURVIVOR_WIN)
        self.registerEvent(b3.events.EVT_GAME_ROUND_END)

        try:
            self.registerEvent(b3.events.EVT_VOTEMAP_COMMAND)
        except:
            self.warning("Unable to register event VOTEMAP")

        self._survivorEnd = False
        self._matchmode = False
        
    def getCmd(self, cmd):
        cmd = 'cmd_%s' % cmd
        if hasattr(self, cmd):
            func = getattr(self, cmd)
            return func
        return None
    
    def onLoadConfig(self):
        try:
            self._random_rotation = self.config.getboolean('maprotation', 'use_random')
        except:
            self._random_rotation = True
            self.debug('Using default value (%s) for random_rotation', self._random_rotation)
        try:
            self._enable_rotation = self.config.getboolean('maprotation','enable')
        except:
            self._enable_rotation = True
        try:
            self._enable_autobalance = self.config.getboolean('settings','auto_balance')
        except:
            self._enable_autobalance = True
        try:
            self._min_maps_level = self.config.getint('settings','min_maps_level')
        except:
            self._min_maps_level = False
        try:
            self._min_reg_connections = self.config.getint('settings','min_reg_connections')
        except:
            self._min_reg_connections = False
        try:
            self._super_reg_level = self.config.getint('settings','super_reg_level')
        except:
            self._super_reg_level = False                        
        try:
            self._config_location = self.config.get('settings','load_location')
        except:
            self._config_location = False
            self.debug('paload disabled')
        try:
            self._announce = self.config.getint('settings','announce')
        except:
            self._announce = 2
                 
    def onEvent(self, event):
        """\
        Handle intercepted events
        """
        if event.type == b3.events.EVT_GAME_WARMUP:
            # fix to use scores on status plugin
            if self.console.game.gameType in ('ts','tdm','ctf','bomb'):
                self.console.setCvar('g_teamScores','0:0')
            if not self.is_matchmode():
                self.handle_rotation(event)
        elif event.type == b3.events.EVT_GAME_ROUND_START:
            self.raisethedead()
            self.checkRoundStart()
        elif event.type == b3.events.EVT_SURVIVOR_WIN:
            self._survivorEnd = True
            self.do_autobalance()
        elif event.type == b3.events.EVT_GAME_ROUND_END:
            self.debug("GAME_ROUND_END EVENT")
        elif event.type == b3.events.EVT_VOTEMAP_COMMAND:
            self.find_next_map_rotation(event.data[0])

    def checkRoundStart(self):
        if self._survivorEnd:
            self.debug("Survivor round end")
            self._survivorEnd = False
        else:
            if self.is_matchmode():
                if self.console.game.gameType == 'ts':
                    self.debug("Starting TS match")
                    self.initGame()
                elif self.console.game.gameType == 'ctf':
                    self.debug("Starting CTF match")
                    self.initGame()

    def initGame(self):
        self.console.game.startMap()
        self.console.game.rounds = 0
        self.console.setCvar('g_teamScores','0:0')

    def teambalance(self):
        if self._padminPlugin:
            self._padminPlugin.teambalance()
        else:
            self.debug("Teambalance not available")
        
    def do_autobalance(self):
        if not self._enable_autobalance or self._matchmode:
            self.debug("Skip autobalance")
            return
        self.debug("Try autobalance")
        self.teambalance()
        
    def raisethedead(self):
        self.debug("Raise the dead")
        for client in self.console.clients.getList():
            client.state = b3.STATE_ALIVE
            
    def is_matchmode(self):
        self._matchmode = self.console.getCvar('g_matchmode').getBoolean()
        return self._matchmode
        
    def handle_rotation(self, event):
        self.debug("Handle rotation")
        self._currentMap = self.console.game.mapName
        if self._enable_rotation:
            if self._nextMap:
                self.debug("Set next map to %s" % self._nextMap)
                self.console.write('g_nextmap %s' % self._nextMap)
                self.console.say('^7Next map in rotation: ^2%s' % self._nextMap)
                self._nextMap = None
            else:
                self.debug("No next map setted")
  
    def find_next_map_rotation(self, chmap):
        self.debug("Find next map in rotation")
        currentmap = self.console.game.mapName
        if self._nextMap:
            self.debug("Next map already set. Skipping")
            return
#        if not self._nextMap or currentmap == self._nextMap:
#            nmap = self.console.getCvar('g_nextmap').getString()
#            self.debug('g_nextmap: %s' % nmap)
#            if nmap != "":
#                self._nextMap = nmap
#                self.debug("Next map already set. Skipping")
#                return
     
          # seek the next map from the mapcyle file
        if not currentmap:
            self.debug("No current map set")
            return None
        self.debug("Current map %s" % currentmap)
 
        mapcycle = self.console.getCvar('g_mapcycle').getString()
        mapfile = self.console.game.fs_basepath + '/' + self.console.game.fs_game + '/' + mapcycle
        if not os.path.isfile(mapfile):
            mapfile = self.console.game.fs_homepath + '/' + self.console.game.fs_game + '/' + mapcycle

        firstmap = None
        cyclemapfile = open(mapfile, 'r')
        lines = cyclemapfile.readlines()
      
        if len(lines) == 0:
            self.debug("No maps in cycle")
            return None
            
        # get maps 
        maps = []
        try:
            while True:
                tmp = lines.pop(0).strip()
                if tmp[0] == '{':
                    while tmp[0] != '}':
                        tmp = lines.pop(0).strip()
                        tmp = lines.pop(0).strip()
                maps.append(tmp)
        except IndexError:
            pass
        
        if len(maps) == 0:
            return None
        else:
            self.debug("Map list size %d" % len(maps))

        firstmap = maps[0]
        mapl = []
        mapl.extend(maps)
      
        # remove unselectable maps
        try:
            maps.remove(chmap)
        except:
            pass
      
        try:
            cur = maps.index(currentmap)
            if cur == len(maps)-1:
                self._nextMap = maps[1]
            else:
                try:
                    self._nextMap = maps[cur+2]
                except IndexError:
                    self._nextMap = firstmap
#            tmp = maps.pop(0)
#            while currentmap != tmp:
#                tmp = maps.pop(0)
#                if currentmap == tmp:
#                    if len(maps) > 0:
#                        self._nextMap = maps.pop(0)
#                        break
#                    else:
#                        self._nextMap = firstmap
#                        break
        except (IndexError, ValueError):
            self.debug("Current map not found")
            if self._random_rotation:
                self.debug("Select a random map")
                try:
                    i = random.randint(0,len(mapl)-1)
                    self._nextMap = mapl[i]
                except:
                    self.debug("Something went wrong with random selection")
            else:
                self.debug("Use first map")
                self._nextMap = firstmap
        self.debug("Next map in rotation %s" % self._nextMap)
    
    def _getMapList(self, client=None):
        try:
            from b3 import maplist as mplist
        except:
            return self.console.getMaps()
        else:
            if client:
                if client.maxLevel >= self._min_maps_level:
                    maplist = self.console.getMaps()
                else:
                    maplist = mplist.listCycleMaps(self.console)
            else:
                maplist = mplist.listCycleMaps(self.console)
            return maplist
        
    def getMapsSoundingLike(self, mapname, client=None):
        maplist = self._getMapList(client)
                
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
                self.debug("shortmaplist sorted by distance : %s" % shortmaplist)
                match = shortmaplist[:3]
            else:
                maplist.sort(key=lambda map: levenshteinDistance(data, string.replace(string.replace(map.strip(), 'ut4_',''), 'ut_','')))
                self.debug("maplist sorted by distance : %s" % maplist)
                match = maplist[:3]
            # we have the list sorted by distance. check if the first one match
            if len(match)>1:
                if string.replace(string.replace(match[0].lower(), 'ut4_',''), 'ut_','') == data.lower():
                    return match[0]
        
        return match

    def cmd_who(self, data, client, cmd=None):
        client.message('^7Your id is ^3@%s' % client.id)
        return True
                  
    def cmd_pamap(self, data, client, cmd=None):
        """\
        <map> - switch current map
        """
        if not data:
            client.message('^7You must supply a map to change to.')
            return False
        
        match = self.getMapsSoundingLike(data, client)

        if len(match) > 1:
            client.message('do you mean : %s' % string.join(match,', '))
            return True
            
        if len(match) == 1:
            mapname = match[0]
        else:
            client.message('^7cannot find any map like [^4%s^7].' % data)
            return False
    
        self.find_next_map_rotation(mapname)
        self.console.changeMap(mapname)
        return True

    def cmd_pasetnextmap(self, data, client=None, cmd=None):
        """\
        <mapname> - Set the nextmap (partial map name works)
        """
        if not data:
            client.message('^7Invalid or missing data, try !help setnextmap')
            return False
        else:
            match = self.getMapsSoundingLike(data, client)
            if len(match) > 1:
                client.message('do you mean : %s ?' % string.join(match,', '))
                return False
            if len(match) == 1:
                mapname = match[0]
                self.find_next_map_rotation(mapname)
                self.console.write('g_nextmap %s' % mapname)
                if client:
                    client.message('^7nextmap set to %s' % mapname)
            else:
                client.message('^7cannot find any map like [^4%s^7].' % data)
                return False
        return True

    def cmd_pashuffleteams(self, data, client, cmd=None):
        """\
        Shuffle teams (randomly)
        (You can safely use the command without the 'pa' at the beginning)
        """
        self.debug("Shuffle teams")        
        
        if self._announce == 1:
            self.console.write('say Shuffling Teams!')
        elif self._announce == 2:
            self.console.write('bigtext "Shuffling Teams!"')
                 
        random.seed(os.urandom(40))
        clients = self.console.clients.getList()
        for i in range(0,3):
            random.shuffle(clients)
        team = random.choice(['blue','red'])
        teamname = {-1:'UNKNOWN', b3.TEAM_SPEC: 'SPEC', b3.TEAM_RED: 'RED', b3.TEAM_BLUE: 'BLUE'}
        for c in clients:
            self.debug("Client %s current team %s" % (c.name, teamname[c.team]))
            if c.team in [b3.TEAM_RED,b3.TEAM_BLUE]:
                self.debug("Client forced to %s" % team)
                self.console.write('forceteam %s %s' % (c.cid, team))
                if 'red' == team: team = 'blue'
                else: team = 'red'
            else:
                self.debug("Client untouched")
        self.teambalance()
        return True

    def cmd_pasetpassword(self, data, client, cmd=None): 
        """\
        set the server public password
        """
        if not data:
            client.message("^7You must suply a password")
            return False
        
        self.console.setCvar('g_password',data)
        return True

    def cmd_pasetteamname(self, data, client, cmd=None):
        """\
        <team: red/blue> <name> - Set the team name
        """
        if not data:
            client.message("^7Invalid or missing data, try !help setteamname")
            return False
        
        input = data.split(' ',1)
        team = "g_teamname%s" % input[0]
        self.console.setCvar(team,input[1])
        return True

    def cmd_pabandetail(self, data, client, cmd=None):
        """\
        <name> - more detailed ban info
        """      
        m = self._adminPlugin.parseUserCmd(data)
        if not m:
            client.message('^7Invalid parameters')
            return False

        sclient = self._adminPlugin.findClientPrompt(m[0], client)
        if sclient:
            if sclient.numBans:
                penalty = self.console.storage.getClientLastPenalty(sclient, type=('Ban', 'TempBan'))
                cadmin = self._adminPlugin.findClientPrompt("@%s" % penalty.adminId,client)
                if cadmin:
                    if penalty.timeExpire > 0:
                        cmd.sayLoudOrPM(client, '^7Banned by %s until %s. Reason: %s' % (cadmin.name,self.timetodate(penalty.timeExpire), penalty.reason))
                    else:
                        cmd.sayLoudOrPM(client, '^7Permanent banned by %s. Reason: %s' % (cadmin.name, penalty.reason))
                else:
                    if penalty.timeExpire > 0:
                        cmd.sayLoudOrPM(client, '^7Banned until %s. Reason: %s' % (self.timetodate(penalty.timeExpire), penalty.reason))
                    else:
                        cmd.sayLoudOrPM(client, '^7Permanent banned. Reason: %s' % penalty.reason)
            else:
                cmd.sayLoudOrPM(client, '^7%s ^7has no active bans' % sclient.exactName)
        return True

    def timetodate(self, value):
        return datetime.datetime.fromtimestamp(float(value)).strftime('%d-%m-%Y')

    def cmd_paload(self, data, client, cmd=None):
        """\
        <conf> Load specific configuration file.
        """        
#        if self.is_matchmode():
        if not data:
            client.message('^7Invalid or missing data.')
        else:
            if self._config_location:
                cfgfile = open(self._config_location,'r')
                cfglist = cfgfile.read().strip('\n').split('\n')            
                if cfglist:
                    found = False
                    for cfg in cfglist:
                        if data.lower() == cfg:
                            if os.path.exists(os.path.join(self.console.game.fs_homepath,self.console.game.fs_game,'%s.cfg' % cfg)):
                                self.debug('Executing configfile = [%s]',cfg)
                                self.console.write('exec %s.cfg' % cfg)
                                return True
                            else:
                                client.message('^7File not found!')
                            found = True
                            break
                    if not found:
                        client.message('^7Config not found.')
                else:
                    client.message('^7No config found.')
            else:
                client.message('^7Command disabled')
#        else:
#            client.message('^7This command is enabled in match mode only')
#        return False

    def cmd_paslapall(self, data, client, cmd=None):
        """\
        <player> slap all
        (You can safely use the command without the 'pa' at the beginning)
        """
        clients = self.console.clients.getList()
        slist = []
        for sclient in clients:
            if sclient.cid == client.cid:
                continue
            elif sclient.maxLevel >= client.maxLevel:
                continue
            else:
                slist.append(sclient)
        thread.start_new_thread(self.threadedpunish, (slist, client, 'slap'))
        return True

    def cmd_groups(self, data, client, cmd=None):
        """\
        <name> - lists all the player's groups
        """
        m = self._adminPlugin.parseUserCmd(data)
        if m:
            lclient = self._adminPlugin.findClientPrompt(m[0], client)
        else:
            lclient = client

        if lclient:
            if len(lclient.groups):
                glist = []
                for group in lclient.groups:
                    glist.append(group.keyword);
                cmd.sayLoudOrPM(client, self._adminPlugin.getMessage('groups_in', lclient.exactName, string.join(glist, ', ')))
            else:
                cmd.sayLoudOrPM(client, self._adminPlugin.getMessage('groups_none', lclient.exactName))
        return True

    def threadedpunish(self, sclients, client, cmd):
        self.debug('Entering threadedpunish...')
        for sclient in sclients:
            self.console.write('%s %s' % (cmd, sclient.cid))
            time.sleep(1)

    def cmd_paunreg(self, data, client, cmd=None):
        """\
        <name> - remove a regular user
        """

        m = self._adminPlugin.parseUserCmd(data)
        if not m:
            client.message('^7Invalid parameters')
            return False

        cid = m[0]

        try:
            group = clients.Group(keyword='reg')
            group = self.console.storage.getGroup(group)
        except Exception, e:
            self.error(e)
            client.message('^7Group reg does not exist')
            return False

        sclient = self._adminPlugin.findClientPrompt(cid, client)
        if sclient:
            if sclient.maxLevel > group.level:
                client.message('^7%s ^7is in a higher level group' % sclient.exactName)
            elif sclient.inGroup(group):
                sclient.remGroup(group)
                sclient.save()
                client.message("^7Unregistered client %s" % sclient.exactName)
                return True
            else:
                client.message('^7%s ^7is not a regular user' % sclient.exactName)
        return False

    def cmd_pamaps(self, data, client=None, cmd=None):
        """\
        - list the server's map rotation
        """
        if not self._adminPlugin.aquireCmdLock(cmd, client, 60, True):
            client.message('^7Do not spam commands')
            return False

        maps = self._getMapList(client)
        if maps:
            cmd.sayLoudOrPM(client, '^7Map Rotation: ^2%s' % string.join(maps, '^7, ^2'))
        else:
            client.message('^7Error: could not get map list')
            return False
        return True

    def cmd_makereg(self, data, client, cmd=None):
        """\
        <name> <group> - make a name a regular
        """

        m = self._adminPlugin.parseUserCmd(data)
        if not m:
            client.message('^7Invalid parameters')
            return False

        cid = m[0]

        try:
            group = clients.Group(keyword='reg')
            group = self.console.storage.getGroup(group)
        except:
            client.message('^7Group reg does not exist')
            return False

        sclient = self._adminPlugin.findClientPrompt(cid, client)
        if sclient:
            if sclient.inGroup(group):
                client.message(self.getMessage('groups_already_in', sclient.exactName, group.name))
            elif sclient.maxLevel >= group.level:
                client.message('^7%s ^7is already in a higher level group' % sclient.exactName)
            else:
                if client.maxLevel >= self._super_reg_level or sclient.connections >= self._min_reg_connections:
                    sclient.setGroup(group)
                    sclient.save()
                    cmd.sayLoudOrPM(client, self._adminPlugin.getMessage('groups_put', sclient.exactName, group.name))
                    return True
                else:
                    client.message('^7Client with %s connections cannot be regular' % sclient.connections)
        return False
                                              
if __name__ == '__main__':
    from b3.fake import fakeConsole
    from b3.fake import joe
 
    fakeConsole.setCvar('g_mapcycle','mapcycle.txt')
    setattr(fakeConsole.game,'fs_basepath','/home/gabriel/urbanterror')
    setattr(fakeConsole.game,'fs_game','q3ut4')

    p = ExtraadminPlugin(fakeConsole, '@b3/extplugins/conf/extraadmin.xml')
    p.onStartup()
    
    print p._nextMap
    print p._currentMap
    p.find_next_map_rotation('ut4_tejen_beta3')
    print p._nextMap
