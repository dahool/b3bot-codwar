# Copyright (C) 2008 Courgette
# Inspired by the spree plugin from Walker
#
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
#
# 
#
# Changelog :
# 0.1.0 : initial release
# This plugin was made with a tranformation of the plugin Headshoturt by Courgette
# 0.2.0 : initial release
# Put timer to create events that old parser can't give
# 0.3.0 : Bugs corrections
# 0.4.0 : Plugin simplified work with parseriourt41 1.5.0 or above
# 0.5.0 : 
#    Refactoring and cleaning
#    fix bug when no flag is captured
#    quickest flag award separated from max flag award.
#    cmd !flag also give best personnal time
#    add tests
# 0.6.0 : SGT - Save map stats to db

__version__ = '0.6.0'
__author__  = 'Beber888'


import b3, time
import b3.events
import b3.plugin

class FlagStats:
    flag = 0
    minTime = None

    
#--------------------------------------------------------------------------------------------------
class FlagstatsPlugin(b3.plugin.Plugin):
    '''
    CREATE TABLE `flagstats` (
    `mapname` VARCHAR( 255 ) NOT NULL ,
    `most_capture_client` INT( 11 ) UNSIGNED NOT NULL ,
    `most_capture_score` INT( 11 ) UNSIGNED NOT NULL ,
    `most_capture_timeadd` INT( 11 ) UNSIGNED NOT NULL ,
    `quick_capture_client` INT( 11 ) UNSIGNED NOT NULL ,
    `quick_capture_score` FLOAT( 20, 2 ) UNSIGNED NOT NULL ,
    `quick_capture_timeadd` INT( 11 ) UNSIGNED NOT NULL ,
    PRIMARY KEY ( `mapname` ) ,
    INDEX ( `most_capture_client` , `quick_capture_client` )
    ) ENGINE = MYISAM     
    '''

    _INSERT_QUERY = "INSERT INTO `flagstats` VALUES ('%s', %d, %d, %d, %d, %f, %d)"
    _UPDATE_QUERY = "UPDATE `flagstats` SET %s=%d, %s=%d, %s=%d, %s=%d, %s=%f, %s=%d WHERE mapname='%s'"
    _UPDATE_QUERY_D = "UPDATE `flagstats` SET %s=%d, %s=%d, %s=%d WHERE mapname='%s'"
    _UPDATE_QUERY_F = "UPDATE `flagstats` SET %s=%d, %s=%f, %s=%d WHERE mapname='%s'"
    _SELECT_QUERY = "SELECT * FROM `flagstats` WHERE `mapname` = '%s'"
    
    _adminPlugin = None
    _reset_flagstats_stats = None
    _min_level_flagstats_cmd = None
    _clientvar_name = 'flagstats_info'
    _show_awards = None
    maxFlagBlue = 0
    maxFlagRed = 0
    maxFlagClientsRed = None
    maxFlagClientsBlue = None
    TimeRed = 0
    TimeBlue = 0
    MinTimeBlue = 999
    MinTimeRed = 999
    minTimeClientBlue = None
    minTimeClientRed = None
    TakenTimeBlue = 0
    TakenTimeRed = 0
    FlagRedTaken = 0
    FlagBlueTaken = 0
    GameType = 0
    
    def onLoadConfig(self):

        try:
            self._reset_flagstats_stats = self.config.getboolean('settings', 'reset_flagstats')
        except:
            self._reset_flagstats_stats = False
        self.debug('reset flag stats : %s' % self._reset_flagstats_stats)
            
            
        try:
            self._show_awards = self.config.getboolean('settings', 'show_awards')
        except:
            self._show_awards = False
        self.debug('show awards : %s' % self._show_awards)            
        
        
        try:
              self._min_level_flagstats_cmd = self.config.getint('settings', 'min_level_flagstats_cmd')
        except:
            self._min_level_flagstats_cmd = 0
        self.debug('min level for flag cmd : %s' % self._min_level_flagstats_cmd)
        
        
        
        # get the plugin so we can register commands
        self._adminPlugin = self.console.getPlugin('admin')
        if not self._adminPlugin:
            # something is wrong, can't start without admin plugin
            self.error('Could not find admin plugin')
        else:
            self._adminPlugin.registerCommand(self, 'flag', self._min_level_flagstats_cmd, self.cmd_flagstats, 'fs')

        
    def onStartup(self):
        self.registerEvent(b3.events.EVT_CLIENT_ACTION)
        self.registerEvent(b3.events.EVT_GAME_FLAG_RETURNED)
        self.registerEvent(b3.events.EVT_GAME_EXIT)
        self.registerEvent(b3.events.EVT_GAME_ROUND_END)
        self.registerEvent(b3.events.EVT_GAME_ROUND_START)
        
        self.query = self.console.storage.query
        
    def onEvent(self, event):
        """\
        Handle intercepted events
        """
        if self.console.game.gameType == 'ctf':
            if event.type == b3.events.EVT_CLIENT_ACTION:
                self.FlagCounter(event)
            elif event.type == b3.events.EVT_GAME_FLAG_RETURNED:
                self.FlagReturn(event)
            elif event.type == b3.events.EVT_GAME_EXIT or \
                    event.type == b3.events.EVT_GAME_ROUND_END:
                self.handle_gameexit(event)
            elif (event.type == b3.events.EVT_GAME_ROUND_START):
                self.show_halloffame()

    def init_flagstats_stats(self, client):
        # initialize the clients flag stats
        client.setvar(self, self._clientvar_name, FlagStats())


    def get_flagstats_stats(self, client):
        
        if not client.isvar(self, self._clientvar_name):
            client.setvar(self, self._clientvar_name, FlagStats())
            
        return client.var(self, self._clientvar_name).value


    def FlagCounter(self, event):
        """\
        A Event was made. 
        """
        # GESTION REDFLAG
        #Flag pris
        if  event.data == 'team_CTF_redflag' and event.client.team == b3.TEAM_BLUE \
                                    and self.FlagRedTaken == 0:# and self.PorteurRed == 0:
            self.FlagRedTaken = 1
            self.TakenTimeRed = time.time()  
        
        #Flag ramene         
        elif event.data == 'flag_returned' and self.FlagRedTaken == 1 \
                                    and event.client.team == b3.TEAM_RED:
            self.FlagRedTaken = 0
                    
        #Flag capture  
        elif event.data == 'flag_captured' and event.client.team == b3.TEAM_BLUE \
                            and event.client != '' and self.FlagRedTaken == 1: #and event.client ==  self.PorteurRed:
            self.FlagRedTaken = 0
            timeCapture = time.time() - self.TakenTimeRed

            client = event.client
            if client:        
                stats = self.get_flagstats_stats(client)
                stats.flag += 1
                if self.maxFlagBlue < stats.flag:
                    self.maxFlagBlue = stats.flag
                    self.maxFlagClientsBlue = client
                if self.MinTimeBlue > timeCapture :
                    self.MinTimeBlue = timeCapture
                    self.minTimeClientBlue = client
                if stats.minTime is None or stats.minTime > timeCapture:
                    # new personal record !
                    stats.minTime = timeCapture
                    self.show_messageToClient(client, timeCapture, bestTime=True)
                else:
                    self.show_messageToClient(client, timeCapture)
                    

    
        # GESTION BLUEFLAG
        #Flag pris
        elif event.data == 'team_CTF_blueflag' and event.client.team == b3.TEAM_RED \
                        and event.client != '' and self.FlagBlueTaken == 0:# and self.PorteurRed == 0:
             self.FlagBlueTaken = 1
             self.TakenTimeBlue = time.time()

        #Flag ramene         
        elif event.data == 'flag_returned' and self.FlagBlueTaken == 1 \
                                            and event.client.team == b3.TEAM_BLUE:
            self.FlagBlueTaken = 0
                    
        #Flag capture  
        elif event.data == 'flag_captured' and event.client.team == b3.TEAM_RED \
                        and event.client != '' and self.FlagBlueTaken == 1: #and event.client ==  self.PorteurRed:
            self.FlagBlueTaken = 0
            timeCapture = time.time() - self.TakenTimeBlue

            client = event.client
            if client:        
                stats = self.get_flagstats_stats(client)
                stats.flag += 1
                if self.maxFlagRed < stats.flag:
                    self.maxFlagRed = stats.flag
                    self.maxFlagClientsRed = client
                if self.MinTimeRed > timeCapture:
                    self.MinTimeRed = timeCapture
                    self.minTimeClientRed = client
                if stats.minTime is None or stats.minTime > timeCapture:
                    # new personal record !
                    stats.minTime = timeCapture
                    self.show_messageToClient(client, timeCapture, bestTime=True)
                else:
                    self.show_messageToClient(client, timeCapture)
                    
            

    def FlagReturn(self, event):
        if event.data == 'RED':
            self.FlagRedTaken = 0
        if event.data == 'BLUE':
            self.FlagBlueTaken = 0

    
    def show_messageToClient(self, client, timeCapture, bestTime=False):
        """\
        display the message
        """
        self.debug('show_messageToClient')
        flagStats = self.get_flagstats_stats(client)
        plurial = ''
        if flagStats.flag > 1:
            plurial = 's'
        self.console.write('^1%s^3 captured ^6%s^3 Flag%s' % (client.name, flagStats.flag, plurial))        
        self.console.write('^3time : ^6%0.2f^3 Sec' % (timeCapture))
        if bestTime:
            client.message('^3New personnal record ! (^6%0.2f^3 sec)' % (timeCapture))




    def cmd_flagstats(self, data, client, cmd=None):
        """\
        [player] - Show a players number of flag captured
        """        
        if data is None or data=='':
            if client is not None:
                flagStats = self.get_flagstats_stats(client)
                if flagStats.flag > 0:
                    client.message('^7You captured ^2%s^7 flag. Best time : ^2%0.2f' % (flagStats.flag, flagStats.minTime))
                else:
                    client.message(client, '^7You captured no flag')
        else:
            input = self._adminPlugin.parseUserCmd(data)
            if input:
                # input[0] is the player id
                sclient = self._adminPlugin.findClientPrompt(input[0], client)
                if not sclient:
                    # a player matchin the name was not found, a list of closest matches will be displayed
                    # we can exit here and the user will retry with a more specific player
                    client.message('^7Invalid data, can\t find player %s'%data)
                    return False
            else:
                client.message('^7Invalid data, try !help flag')
                return False
            
            flagStats = self.get_flagstats_stats(sclient)
            if flagStats.flag > 0:
                client.message('^7%s captured ^2%s^7 flag' % (sclient.name, flagStats.flag))
            else:
                client.message('^7%s captured no flag'%sclient.name)
       
       

    def handle_gameexit(self, event):
        self.debug("handle_gameexit")
        if self._show_awards:
            if self.maxFlagClientsBlue is not None:
                plurial = ''
                if self.maxFlagBlue > 1:
                    plurial = 's'
                self.console.write('^2Most Red Flag Award : %s^3 (^6%s^3 Flag%s)'%(self.maxFlagClientsBlue.name, self.maxFlagBlue, plurial))
            if self.maxFlagClientsRed is not None:
                plurial = ''
                if self.maxFlagRed > 1:
                    plurial = 's'
                self.console.write('^2Most Blue Flag Award : %s^3 (^6%s^3 Flag%s)'%(self.maxFlagClientsRed.name, self.maxFlagRed, plurial))  
            if self.minTimeClientBlue is not None:
                self.console.write('^2Quickest Red Flag Award : %s^3 (^6%0.2f^3 Sec)'%(self.minTimeClientBlue.name, self.MinTimeBlue))
            if self.minTimeClientRed is not None:
                self.console.write('^2Quickest Blue Flag Award : %s^3 (^6%0.2f^3 Sec)'%(self.minTimeClientRed.name, self.MinTimeRed))

        try:
            self.saveData()
        except Exception, e:
            self.error("Couldn't update hall of fame")
            self.error(str(e))
            
        if self._reset_flagstats_stats:
            for c in self.console.clients.getList():
                self.init_flagstats_stats(c)

        self.maxFlagClientsBlue = None
        self.maxFlagBlue = 0
        self.maxFlagClientsRed = None
        self.maxFlagRed = 0
        self.MinTimeBlue = 999
        self.MinTimeRed = 999
        self.minTimeClientBlue = None
        self.minTimeClientRed = None
        self.FlagRedTaken = 0
        self.FlagBlueTaken = 0
        
    def show_halloffame(self):
        current = self.getRecord()
        if current:
            holder, score = current['most']
            if holder:
                if score > 1:
                    plurial = 's'
                else:
                    plurial = ''
                self.console.write('^2Most Captured Flags on this map: %s^3 (^6%s^3 Flag%s)'%(holder, str(score), plurial))
                
            holder, score = current['quick']
            if holder:
                self.console.write('^2Quickest Flag on this map: %s^3 (^6%0.2f^3 Sec)'%(holder, score))
        return
        
    def saveData(self):
        maxClient = None
        maxScore = 0
        quickClient = None
        quickScore = 999
        q = None
        
        if self.maxFlagClientsBlue:
            maxClient = self.maxFlagClientsBlue
            maxScore = self.maxFlagBlue
        if self.maxFlagClientsRed:
            if self.maxFlagRed > maxScore:
                maxClient = self.maxFlagClientsRed
                maxScore = self.maxFlagRed
            #elif self.maxFlagRed == maxScore:
        if self.minTimeClientBlue:
            quickClient = self.minTimeClientBlue
            quickScore = self.MinTimeBlue
        if self.minTimeClientRed:
            if self.MinTimeRed < quickScore:
                quickScore = self.MinTimeRed
                quickClient = self.minTimeClientRed
            #elif self.MinTimeRed == quickScore:
                
        current = self.getRecord()

        if current:
            holder, score = current['most']
            if maxScore > score:
                q = self._UPDATE_QUERY_D % ('most_capture_client',maxClient.id,
                                    'most_capture_score',maxScore,
                                    'most_capture_timeadd', self.console.time(),
                                    self.console.game.mapName)
            holder, score = current['quick']
            if quickScore < score:
                if q:
                    q = self._UPDATE_QUERY % ('most_capture_client',maxClient.id,
                                        'most_capture_score',maxScore,
                                        'most_capture_timeadd', self.console.time(),
                                        'quick_capture_client', quickClient.id,
                                        'quick_capture_score', quickScore,
                                        'quick_capture_timeadd', self.console.time(),
                                        self.console.game.mapName)
                else:
                    q = self._UPDATE_QUERY_D % ('quick_capture_client', quickClient.id,
                                        'quick_capture_score', quickScore,
                                        'quick_capture_timeadd', self.console.time(),
                                        self.console.game.mapName)                    
        else:
            if maxClient and quickClient:
                q = self._INSERT_QUERY % (self.console.game.mapName,
                                            maxClient.id,
                                            maxScore,
                                            self.console.time(),
                                            quickClient.id,
                                            quickScore,
                                            self.console.time())

        if q:
            cursor = self.query(q)
            cursor.close()
            self.debug("Updated hall of fame")
        
    def getRecord(self):
        mHolder = None
        mScore = 0
        qHolder = None
        qScore = 0
        
        q = self._SELECT_QUERY % (self.console.game.mapName)
        try:
            cursor = self.query(q)
        except Exception, e:
            cursor = None
            self.error('Can\'t execute query : %s' % q)
            self.error(str(e))
            
        self.debug('getRecord : %s' % q)
        
        if cursor and (cursor.rowcount > 0):
            r = cursor.getRow()
            # most
            id = '@' + str(r['most_capture_client'])
            clientList = []
            clientList = self.console.clients.getByDB(id)
            if len(clientList):
                mHolder = clientList[0].exactName
                self.debug('most capture record holder found: %s' % clientList[0].exactName)
            mScore = r['most_capture_score']
            # quickest
            id = '@' + str(r['quick_capture_client'])
            clientList = []
            clientList = self.console.clients.getByDB(id)
            if len(clientList):
                qHolder = clientList[0].exactName
                self.debug('quick capture record holder found: %s' % clientList[0].exactName)
            qScore = r['quick_capture_score']
            cursor.close()
        else:
            return None
            
        return {'most': (mHolder,mScore), 'quick': (qHolder, qScore)}
                

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
  
    fakeConsole = FakeUrtConsole('@b3/conf/b3.xml')
    fakeConsole.startup()
    
    p = FlagstatsPlugin(fakeConsole, 'C:/Users/Thomas/workspace/b3/b3-plugins/b3-plugin-flagstats/conf/flagstats.xml')
    p.onStartup()
    p._show_awards = True
    
    from b3.fake import joe, simon
    joe.team = b3.TEAM_BLUE
    simon.team = b3.TEAM_RED
    jack = FakeClient(fakeConsole, cid=42, name="Jack", exactName="Jack", guid="qsd654sqf", _maxLevel=1, authed=True, team=b3.TEAM_RED)

    
    ## initialize gametype
    fakeConsole.game.gameType = 'ctf'
    
    ############# END setup test environment ##################
    
    print "================= ROUND 1 ==================="
    
    joe.takesFlag()
    joe.says('!flag')
    simon.returnsFlag()
    
    simon.takesFlag()
    time.sleep(1.5)
    simon.capturesFlag()
    time.sleep(0.5)
    simon.says('!flag')
    
    jack.takesFlag()
    time.sleep(0.8)
    jack.capturesFlag()
    time.sleep(0.5)
    jack.says('!fs')
    
    simon.takesFlag()
    time.sleep(1.23)
    simon.capturesFlag()
    time.sleep(0.5)
    simon.says('!fs')
    
    fakeConsole.queueEvent(b3.events.Event(b3.events.EVT_GAME_EXIT, None))
    time.sleep(1)
    
    print "\n================= ROUND 2 ==================="
    
    joe.takesFlag()
    time.sleep(0.88)
    joe.capturesFlag()
    time.sleep(0.5)
    
    jack.takesFlag()
    time.sleep(0.5)
    fakeConsole.queueEvent(b3.events.Event(b3.events.EVT_GAME_FLAG_RETURNED, 'BLUE'))
    time.sleep(0.5)
    
    jack.takesFlag()
    time.sleep(1)
    jack.capturesFlag()
    time.sleep(0.5)
    jack.says('!flag')
    
    jack.takesFlag()
    time.sleep(3)
    jack.capturesFlag()
    time.sleep(0.5)
    jack.says('!flag')
    
    fakeConsole.queueEvent(b3.events.Event(b3.events.EVT_GAME_EXIT, None))
    
    time.sleep(5)
