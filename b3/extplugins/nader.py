# Nader Plugin

__author__  = 'SvaRoX'
__version__ = '0.3'


import b3
import b3.events
import b3.plugin
import string
import time, thread, threading
import re # for debug purpose only
#
#
#
#
#
#
# ----------------> QUAND PAS DE NOM : ERROR PROCESSING COMMAND - 22:17 (crossing)
#
#
#
#
# -------------------> testscore : probleme dans le calcul d'arrondi : 2.0*0.2 = 0.0, 2.0*0.6 = 1.0, 2.0*0.3 = 1.0
#
#
# 183_.59 : Scarryman, 1791.71 Me -> !kntest scarr -> Earned: 2 * 3.7 = 7, 2 * 2.2 = 4.0
#
#
#
#
#
#
#
#
#
#
#

#--------------------------------------------------------------------------------------------------
class NaderPlugin(b3.plugin.Plugin):
    _adminPlugin = None
    _xlrstatsPlugin = None
    _minLevel = 100
    _hegrenadeId = 25 # see config file
    _heEnabled = 0
    _stfu = 0 # if 1, no bigtexts
    _nbHEK = 0 # Total number of HE grenade kills
    _nbTop = 5
    _msgLevels = set()
    _nadeKillers = {}
    _challengeTarget = None
    _challengeDuration = 300
    _challengeThread = None
    _db_tableHEF = ''
    _db_mapName = ''
    _db_playerid = ''
    _db_score = ''
    _db_time = ''
    
    def onLoadConfig(self):
        self._adminPlugin = self.console.getPlugin('admin')
        if not self._adminPlugin:
            self.error('Could not find admin plugin')
            return False
        # else:
            # self._adminPlugin.debug('Plugin loaded')
        self._xlrstatsPlugin = self.console.getPlugin('xlrstats')
        if not self._xlrstatsPlugin:
            self.debug('Could not find xlrstats plugin')

        # Options loading
        try:
            self._minLevel = self.config.getint('settings', 'minlevel')
        except:
            pass
        self.debug('Minimum Level to use commands = %d' % self._minLevel)

        try:
            self._nbTop = self.config.getint('settings', 'nbtop')
        except:
            pass
        self.debug('Number of top n displayed = %d' % self._nbTop)

        try:
            if self.config.getint('settings', 'enabled') == 1:
                self._heEnabled = 1
        except:
            pass

        try:
            self._hegrenadeId = self.config.getint('settings', 'hegrenadeid')
        except:
            pass
        self.debug('hegrenade ID = %d' % self._hegrenadeId)

        try:
            self._challengeDuration = self.config.getint('settings', 'challengeduration')
        except:
            pass
        self.debug('Challenge duration = %d' % self._challengeDuration)

        for m in self.config.options('messages'):
            sp = m.split('_')
            nb = 0
            if len(sp) == 2:
                try:
                    nb = int(sp[1])
                    self._msgLevels.add(nb)
                    self.debug('Message displayed at %d HE grenade kills' % nb)
                except:
                    pass

        try:
            self._db_tableHEF = self.config.get('settings', 'db_table_hef')
            self._db_mapName = self.config.get('settings', 'db_map_name')
            self._db_playerid = self.config.get('settings', 'db_playerid')
            self._db_score = self.config.get('settings', 'db_score')
            self._db_time = self.config.get('settings', 'db_time')
        except:
            self.error('Cannot load database settings')

        self._adminPlugin.registerCommand(self, 'heenable', self._minLevel, self.cmd_heenable)
        self._adminPlugin.registerCommand(self, 'hedisable', self._minLevel, self.cmd_hedisable)
        self._adminPlugin.registerCommand(self, 'hestfu', self._minLevel, self.cmd_stfu)
        self._adminPlugin.registerCommand(self, 'hestats', 0, self.cmd_displaySelfScores, 'hes')
        self._adminPlugin.registerCommand(self, 'hetopstats', 0, self.cmd_displayScores, 'hets')
        self._adminPlugin.registerCommand(self, 'heallstats', 0, self.cmd_allstats, 'heas')
        self._adminPlugin.registerCommand(self, 'hechallenge', 0, self.cmd_challenge, 'hech')
        self._adminPlugin.registerCommand(self, 'hetestscore', 0, self.cmd_testscore, 'hetest')
        self._adminPlugin.registerCommand(self, 'herecord', 0, self.cmd_record, 'herec')

        self.query = self.console.storage.query
        
    def onStartup(self):
        self.registerEvent(b3.events.EVT_GAME_ROUND_START)
        self.registerEvent(b3.events.EVT_GAME_EXIT)
        # '-> See poweradmin 604
        self.registerEvent(b3.events.EVT_CLIENT_KILL)
    
    def onEvent(self, event):
        if event.type == b3.events.EVT_CLIENT_KILL:
            self.someoneKilled(event.client, event.target, event.data)
        # elif (event.type == b3.events.EVT_GAME_EXIT) or (event.type == b3.events.EVT_GAME_ROUND_START):
        elif (event.type == b3.events.EVT_GAME_EXIT):
            self.displayScores(0)
            thread.start_new_thread(self.updateHallOfFame, (self._nadeKillers, self.console.game.mapName))
            self.resetScores()
            try:
                self._challengeThread.cancel()
            except:
                pass
        elif (event.type == b3.events.EVT_GAME_ROUND_START):
            if self._challengeThread != None:
                self._challengeThread.cancel()
        # elif event.type == b3.events.EVT_GAME_ROUND_END:
            # self.displayScores(0)
    
    def resetScores(self):
        self._nbHEK = 0
        self._nadeKillers = {}
    
    def cmd_stfu(self, data, client, cmd=None):
        """\
        Enable/disable silent mode (no more bigtexts)
        """
        msg = ['off', 'on']
        self._stfu = (self._stfu + 1) % 2
        cmd.sayLoudOrPM(client, '^7HE grenade plugin : silent mode %s' % msg[self._stfu])

    def cmd_heenable(self, data, client, cmd=None):
        """\
        Enable the plugin
        """
        cmd.sayLoudOrPM(client, '^7HE grenade : enabled')
        self._heEnabled = 1

    def cmd_hedisable(self, data, client, cmd=None):
        """\
        Disable plugin commands, but still counts nade kills
        """
        cmd.sayLoudOrPM(client, '^7HE grenade plugin : disabled')
        self._heEnabled = 0
        
    def cmd_displaySelfScores(self, data, client, cmd=None):
        """\
        <player> Display nade kills stats for a given client (or yourself)
        """
        if not self._heEnabled:
            cmd.sayLoudOrPM(client, '^7HE grenade stats are disabled')
            return
        msg = ''
        if not data:
            if client.cid in self._nadeKillers:
                msg = '%s : ^2%d ^7HE grenade kills' % (client.exactName, client.var(self, 'hegrenadeKills', 0).value)
            else:
                msg = '^7No HE grenade kill yet... try again'
        else:
            m = self._adminPlugin.parseUserCmd(data)
            if m:
                sclient = self._adminPlugin.findClientPrompt(m[0], client)
                if not sclient:
                    msg = 'No player found'
                # elif len(sclient) > 1:
                    # msg = 'Too many players found, please try an other request'
                else:
                    msg = '%s : ^2%d ^7HE grenade kills' % (sclient.exactName, sclient.var(self, 'hegrenadeKills', 0).value)
        # if unnecessary ?
        if msg:
            cmd.sayLoudOrPM(client, msg)

    def cmd_displayScores(self, data, client, cmd=None):
        """\
        List the top naders for the current map
        """
        if not self._heEnabled:
            client.message('^7HE grenade stats are disabled')
            return
        if not len(self._nadeKillers):
            client.message('^7No top HE grenade stats for the moment')
        else:
            self.displayScores(1)

    def cmd_challenge(self, data, client, cmd=None):
        """\
        <player> Challenge someone. The first player to nades him wins the challenge.
        """
        if (not self._heEnabled) or (self._stfu == 1):
            cmd.sayLoudOrPM(client, '^7HE grenade stats are disabled')
            return
        if data:
            m = self._adminPlugin.parseUserCmd(data)
            if m:
                sclient = self._adminPlugin.findClientPrompt(m[0], client)
                if not sclient:
                    # pass
                    # cmd.sayLoudOrPM(client, 'No player found')
                    return
                else:
                    self.console.write('bigtext "^3New challenge : ^2try to nade ^3%s"' % (sclient.exactName))
                    self._challengeTarget = sclient
        self._challengeThread = threading.Timer(self._challengeDuration, self.challengeEnd)
        self._challengeThread.start()
        self.debug('Starting challenge thread : %d seconds' % self._challengeDuration)

    def cmd_allstats(self, data, client, cmd=None):
        """\
        [<player>] Displays the total nade kills for you/someone from xlrstats
        """
        if self._xlrstatsPlugin == None:
            client.message('Command unavailable, please try later"')
            return

        # cid = client.id
        fclient = client
        if data:
            m = self._adminPlugin.parseUserCmd(data)
            if m:
                sclient = self._adminPlugin.findClientPrompt(m[0], client)
                if not sclient:
                    # msg = 'No player found'
                    return
                else:
                    fclient = sclient

        self.allStats(client, fclient)

    def cmd_testscore(self, data, client, cmd=None):
        """\
        <player> Displays the XLR skills points gained when killing a player
        """
        if self._xlrstatsPlugin == None:
            client.message('Command unavailable, please try later"')
            return

        if not data:
            client.message('Wrong parameter, try !help hetestscore')
        else:
            m = self._adminPlugin.parseUserCmd(data)
            if m:
                sclient = self._adminPlugin.findClientPrompt(m[0], client)
                if not sclient:
                    pass
                    # cmd.sayLoudOrPM(client, 'No player found')
                else:
                    # if client.cid == sclient.cid:
                        # client.message('You cannot nade yourself...')
                        # return
                    self.testScore(client, sclient)

    def cmd_record(self, data, client, cmd=None):
        """\
        Displays the best nade user for the current map
        """
        message = '^7No record found on this map'
        (currentRecordHolder, currentRecordValue) = self.getRecord()
        if (currentRecordHolder != '') and (currentRecordValue != ''):
            message = '^7HE grenade kills record on this map: ^1%s ^2%s ^7kills' % (currentRecordHolder, currentRecordValue)
            # message = '^7Nade kills record on this map: ^1%s %s' % (currentRecordHolder, currentRecordValue)
        client.message(message)

    def displayScores(self, fromCmd):
        # From stats plugin
        listKills = []
        he = self._nadeKillers
        for cid, c in he.iteritems():
            listKills.append((c, he[cid].var(self, 'hegrenadeKills', 0).value))

        if len(listKills):
            tmplist = [(x[1], x) for x in listKills]
            tmplist.sort()
            listKills = [x for (key, x) in tmplist]
            listKills.reverse()
            
            limit = self._nbTop
            if len(listKills) < limit:
                limit = len(listKills)
                # self._nbTop = len(listKills)
            i = 0
            results = []
            for c, kills in listKills:
                i = i + 1
                results.append('^1#%d. ^4%s ^1(^3%d^1)^7' % (i, c.name, c.var(self, 'hegrenadeKills', 0).value))
                if i >= limit:
                    break
            # self.debug('^1Top %d nade killers : %s' % (self._nbTop, string.join(results, ' ,')))
            self.console.say('^1Top %d HE grenade killers (total %d)  : %s' % (limit, self._nbHEK, string.join(results, ' ,')))
        # else:
            # if fromCmd:
                # self.console.say('No nade kills this round')
    
    def someoneKilled(self, client, target, data=None):
        if data[1] == self.console.UT_MOD_HEGRENADE:
            # do not count same team
            if client.team == target.team and client.team > 0:
                return False
            self._nbHEK += 1
            if self._nbHEK == 1:
                self.console.write('bigtext "^3%s ^7: first HE grenade kill"' % (client.exactName))
            numnades = 1
            if client.cid not in self._nadeKillers:
                client.setvar(self, 'hegrenadeKills', 1)
                self._nadeKillers[client.cid] = client
            else:
                numnades = self._nadeKillers[client.cid].var(self, 'hegrenadeKills', 0).value + 1
                self._nadeKillers[client.cid].setvar(self, 'hegrenadeKills', numnades)
            self.debug('Client %s, %d HE grenade kills' % (client.name, client.var(self, 'hegrenadeKills', 0).value))
            # if not numCuts % 3:
                # self.console.write('bigtext "%s : %d nade kills !"' % (client.name, client.var(self, 'nadeKills', 0).value))
            if (not self._stfu) and (numnades in self._msgLevels):
                msg = self.getMessage('msg_%d' % numnades, { 'name' : client.exactName, 'score' : numnades })
                self.console.write('bigtext "%s"' % msg)

            if self._challengeTarget != None:
                self.debug('challengeTarget exists')
                if target != None:
                    self.debug('target exists')
                    if self._challengeTarget.cid == target.cid:
                        try:
                            self._challengeThread.cancel()
                        except:
                            pass
                        self.console.write('bigtext "^7Good job ^3%s^7, you naded ^3%s ^7!"' % (client.exactName, target.exactName))
                        self._challengeTarget = None

    def allStats(self, client, fclient):
        hegrenadeXlrId = self._xlrstatsPlugin.get_WeaponStats(self._hegrenadeId).id
        # self.debug('XLR nade id = %d' % nadeXlrId)
        player = self._xlrstatsPlugin.get_PlayerStats(fclient)
        xlrResult = self._xlrstatsPlugin.get_WeaponUsage(hegrenadeXlrId, player.id)
        # self.info('Nb of kills = %d' % xlrResult.kills)
        client.message('^7Total HE grenade kills (xlrstats): ^2%d' % xlrResult.kills)

    def challengeEnd(self):
        self.debug('Challeng has ended')
        self.console.write('bigtext "^3%s ^7has won the HE grenade challenge!"' % self._challengeTarget.exactName)
        self._challengeTarget = None
    
    def testScore(self, client, sclient):
        # for cmd in self._xlrstatsPlugin.config.options('commands'):
            # self.debug(cmd)
        killerstats = self._xlrstatsPlugin.get_PlayerStats(client)
        victimstats = self._xlrstatsPlugin.get_PlayerStats(sclient)
        killer_prob = self._xlrstatsPlugin.win_prob(killerstats.skill, victimstats.skill)
        victim_prob = self._xlrstatsPlugin.win_prob(victimstats.skill, killerstats.skill)
        self.debug('Killer skill = %s, victim skill = %s' % (killerstats.skill, victimstats.skill))
        try:
            weapon_factor = self.config.getfloat('settings', 'hegrenadefactor')
        except:
            weapon_factor = 0.5
        kill_bonus = self._xlrstatsPlugin.kill_bonus
        if killerstats.kills > self._xlrstatsPlugin.Kswitch_kills:
            KfactorKiller = self._xlrstatsPlugin.Kfactor_low
        else:
            KfactorKiller = self._xlrstatsPlugin.Kfactor_high
        if victimstats.kills > self._xlrstatsPlugin.Kswitch_kills:
            KfactorVictim = self._xlrstatsPlugin.Kfactor_low
        else:
            KfactorVictim = self._xlrstatsPlugin.Kfactor_high
        # skillGained = kill_bonus * Kfactor * weapon_factor * (1-killer_prob)
        skillGained = kill_bonus * KfactorKiller * (1-killer_prob)
        skillLost = KfactorVictim * (0-victim_prob)
        self.debug('kill bonus=%s, kfactorKiller=%s, kfactorVictim=%s, weapfact =%s, killer_prb=%s' % (kill_bonus, KfactorKiller, KfactorVictim, weapon_factor, killer_prob))
        # client.message('%s*%s=^1%s ^7skill points gained for nading ^3%s^7, opponent will loose %s*%s=^1%s' % (str(weapon_factor), str(round(skillGained, 2)), str(round(weapon_factor*skillGained, 2)), sclient.exactName, str(weapon_factor), str(round(-1*skillLost, 2)), str(round(-1*weapon_factor*skillLost, 2))))
        # client.message('%s*%s=^1%s ^7skill points gained for nading ^3%s^7, opponent will loose %s*%s=^1%s' % (str(weapon_factor), str(skillGained), str(weapon_factor*skillGained), sclient.exactName, str(weapon_factor), str(-1*skillLost), str(-1*weapon_factor*skillLost)))
        client.message('%s*%1.02f=^1%1.02f ^7skill points gained for nading ^3%s^7, opponent will loose %s*%1.02f=^1%1.02f' % (str(weapon_factor), skillGained, weapon_factor*skillGained, sclient.exactName, str(weapon_factor), -1*skillLost, -1*weapon_factor*skillLost))

    def updateHallOfFame(self, nadeKillers, mapName):
        self.debug('Updating Hall of Fame')
        if len(nadeKillers) == 0:
            return

        cursor = None
        newRecord = 0
        message = ''
        
        # Find the best nade player
        listKills = []
        he = nadeKillers
        for cid, c in he.iteritems():
            listKills.append((c, he[cid].var(self, 'hegrenadeKills', 0).value))

        if len(listKills):
            tmplist = [(x[1], x) for x in listKills]
            tmplist.sort()
            listKills = [x for (key, x) in tmplist]
            listKills.reverse()
        
        (bestPlayer, topKills) = listKills[0]
        self.debug('BestPlayer : %s, topKills : %s' % (bestPlayer, topKills))
        
        # Retrieve data for current map (if exists)
        currentMap = mapName
        (currentRecordHolder, currentRecordValue) = self.getRecord()
        if currentRecordValue == '-1':
            self.debug('MySQL error, cannot get record')
            return
        # Retrieve HEF for the current map
        if (currentRecordHolder != '') and (currentRecordValue != '0'):
            self.debug('Record already exists in DB')
            if topKills > int(currentRecordValue):
                # New record
                newRecord = 1
                currentRecordHolder = bestPlayer.exactName
                currentRecordValue = topKills
                q = 'UPDATE %s SET %s=\'%s\', %s=\'%s\', %s=%d WHERE %s=\'%s\'' % (
                                                    self._db_tableHEF,
                                                    self._db_playerid,
                                                    str(bestPlayer.id),
                                                    self._db_score,
                                                    str(topKills),
                                                    self._db_time,
                                                    self.console.time(),
                                                    self._db_mapName,
                                                    currentMap)
                self.debug('New record, updating: %s' % q)
                try:
                    cursor = self.query(q)
                except:
                    self.error('Can\'t execute query : %s' % q)
            else:
                # currentRecordHolder = self.console.clients.getByDB(r[self._db_playerid]).exactName
                # currentRecordValue = r[self._db_score]
                self.debug('No new record, previous record for %s = %s HE grenade kills' % (currentRecordHolder, currentRecordValue))
        else:
            # New record
            newRecord = 1
            currentRecordHolder = bestPlayer.exactName
            currentRecordValue = topKills
            q = 'INSERT INTO %s (%s, %s, %s, %s) VALUES(\'%s\', %s, \'%s\',%d)' % (
                                        self._db_tableHEF,
                                        self._db_mapName,
                                        self._db_playerid,
                                        self._db_score,
                                        self._db_time,
                                        currentMap,
                                        str(bestPlayer.id),
                                        topKills,
                                        self.console.time())
            self.debug('New record, inserting: %s' % q)
            try:
                cursor = self.query(q)
            except:
                self.error('Can\'t execute query : %s' % q)
        if newRecord:
            message = '^2%s ^7HE grenade kills: congratulations ^3%s^7, new record on this map!!' % (currentRecordValue, currentRecordHolder)
        else:
            message = '^7HE grenade kills record on this map: ^1%s ^2%s ^7kills' % (currentRecordHolder, currentRecordValue)
        self.console.say(message)

    def getRecord(self):
        RecordHolder = ''
        RecordValue = '-1'
        cursor = None
        q = 'SELECT * FROM %s WHERE %s = \'%s\'' % (self._db_tableHEF, self._db_mapName, self.console.game.mapName)
        try:
            cursor = self.query(q)
        except:
            self.error('Can\'t execute query : %s' % q)

        self.debug('getRecord : %s' % q)
        if cursor and (cursor.rowcount > 0):
            r = cursor.getRow()
            # clients:899 -> m = re.match(r'^@([0-9]+)$', id) -> add @
            id = '@' + str(r[self._db_playerid])
            clientList = []
            clientList = self.console.clients.getByDB(id)
            if len(clientList):
                RecordHolder = clientList[0].exactName
                self.debug('record holder found: %s' % clientList[0].exactName)
            RecordValue = r[self._db_score]
        elif cursor and (cursor.rowcount == 0):
            RecordValue = 0
        return (RecordHolder, str(RecordValue))
