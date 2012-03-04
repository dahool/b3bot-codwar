#
# BigBrotherBot(B3) (www.bigbrotherbot.com)
# This parser read map cycle from mapcycle file only.
# Also catch event Survivor Winner
# Raise Unban event
#
# Copyright (C) 2010 Sergio Gabriel Teves
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
# 2010-05-12 - SGT
# Initial version
# 04/05/2010 - SGT
# try to fix issue with OnSay when something like this come and the match could'nt find the name group
# say: 7 -crespino-:
#
# 2011-02-19 - SGT
# Create Survivor Winner Event
# Create Unban event

from b3.parsers.iourt41 import __version__ as parent_version

__author__  = 'SGT'
__version__ = parent_version + "A"

import os

import b3
import b3.events
import re
from b3.parsers.iourt41 import Iourt41Parser

class Iourt41AParser(Iourt41Parser):

    _lineFormats = (
        #Generated with ioUrbanTerror v4.1:
        #Hit: 12 7 1 19: BSTHanzo[FR] hit ercan in the Helmet
        #Hit: 13 10 0 8: Grover hit jacobdk92 in the Head
        re.compile(r'^(?P<action>[a-z]+):\s(?P<data>(?P<cid>[0-9]+)\s(?P<acid>[0-9]+)\s(?P<hitloc>[0-9]+)\s(?P<aweap>[0-9]+):\s+(?P<text>.*))$', re.IGNORECASE),
        #re.compile(r'^(?P<action>[a-z]+):\s(?P<data>(?P<cid>[0-9]+)\s(?P<acid>[0-9]+)\s(?P<hitloc>[0-9]+)\s(?P<aweap>[0-9]+):\s+(?P<text>(?P<aname>[^:])\shit\s(?P<name>[^:])\sin\sthe(?P<locname>.*)))$', re.IGNORECASE),

        #6:37 Kill: 0 1 16: XLR8or killed =lvl1=Cheetah by UT_MOD_SPAS
        #2:56 Kill: 14 4 21: Qst killed Leftovercrack by UT_MOD_PSG1
        re.compile(r'^(?P<action>[a-z]+):\s(?P<data>(?P<acid>[0-9]+)\s(?P<cid>[0-9]+)\s(?P<aweap>[0-9]+):\s+(?P<text>.*))$', re.IGNORECASE),
        #re.compile(r'^(?P<action>[a-z]+):\s(?P<data>(?P<acid>[0-9]+)\s(?P<cid>[0-9]+)\s(?P<aweap>[0-9]+):\s+(?P<text>(?P<aname>[^:])\skilled\s(?P<name>[^:])\sby\s(?P<modname>.*)))$', re.IGNORECASE),

        #Processing chats and tell events...
        #5:39 saytell: 15 16 repelSteeltje: nno
        #5:39 saytell: 15 15 repelSteeltje: nno
        re.compile(r'^(?P<action>[a-z]+):\s(?P<data>(?P<cid>[0-9]+)\s(?P<acid>[0-9]+)\s(?P<name>[^ ]+):\s+(?P<text>.*))$', re.IGNORECASE),

        # We're not using tell in this form so this one is disabled
        #5:39 tell: repelSteeltje to B!K!n1: nno
        #re.compile(r'^(?P<action>[a-z]+):\s+(?P<data>(?P<name>[^:]+)\s+to\s+(?P<aname>[^:]+):\s+(?P<text>.*))$', re.IGNORECASE),

        #3:53 say: 8 denzel: lol
        #15:37 say: 9 .:MS-T:.BstPL: this name is quite a challenge
        #2:28 sayteam: 12 New_UrT_Player_v4.1: woekele
        #16:33 Flag: 2 0: team_CTF_redflag
        # SGT - CHANGED
        re.compile(r'^(?P<action>[a-z]+):\s(?P<data>(?P<cid>[0-9]+)\s(?P<name>[^ ]+):\s*(?P<text>.*))$', re.IGNORECASE),

        #15:42 Flag Return: RED
        #15:42 Flag Return: BLUE
        re.compile(r'^(?P<action>Flag Return):\s(?P<data>(?P<color>.+))$', re.IGNORECASE),

        #Bombmode actions:
        #3:06 Bombholder is 2
        re.compile(r'^(?P<action>Bombholder)(?P<data>\sis\s(?P<cid>[0-9]))$', re.IGNORECASE),
        #was planted, was defused, was tossed, has been collected (doh, how gramatically correct!)
        #2:13 Bomb was tossed by 2
        #2:32 Bomb was planted by 2
        #3:01 Bomb was defused by 3!
        #2:17 Bomb has been collected by 2
        re.compile(r'^(?P<action>Bomb)\s(?P<data>(was|has been)\s(?P<subaction>[a-z]+)\sby\s(?P<cid>[0-9]+).*)$', re.IGNORECASE),

        #Falling thru? Item stuff and so forth
        re.compile(r'^(?P<action>[a-z]+):\s(?P<data>.*)$', re.IGNORECASE),
        #Shutdowngame and Warmup... the one word lines
        re.compile(r'^(?P<action>[a-z]+):$', re.IGNORECASE)
    )
    
    def startup(self):
        Iourt41Parser.startup(self)
        self.Events.createEvent('EVT_SURVIVOR_WIN', 'Survivor Winner')

    def unban(self, client, reason='', admin=None, silent=False, *kwargs):
        Iourt41Parser.unban(self, client, reason, admin, silent, *kwargs)
        self.queueEvent(b3.events.Event(b3.events.EVT_CLIENT_UNBAN, admin, client))

    # survivor winner
    def OnSurvivorwinner(self, action, data, match=None):
        self.debug('EVENT: OnSurvivorwinner')
        return b3.events.Event(b3.events.EVT_SURVIVOR_WIN, data)  

    # endmap/shutdown
    def OnShutdowngame(self, action, data=None, match=None):
        self.debug('EVENT: OnShutdowngame')
        self.game.mapEnd()
        # self.clients.sync()
        # self.debug('Synchronizing client info')
        # set data to true to differentiate it from the EXIT event sent by abstract
        data = True
        self._maplist = None # when UrT server reloads, newly uploaded maps get available: force refresh
        return b3.events.Event(b3.events.EVT_GAME_EXIT, data)

    def getMapsCycle(self):
        mapcycle = self.getCvar('g_mapcycle').getString()
        if self.game.fs_game is None:
            try:
                self.game.fs_game = self.getCvar('fs_game').getString().rstrip('/')
            except:
                self.game.fs_game = None
                self.warning("Could not query server for fs_game")
        if self.game.fs_basepath is None:
            try:
                self.game.fs_basepath = self.getCvar('fs_basepath').getString().rstrip('/')
            except:
                self.game.fs_basepath = None
                self.warning("Could not query server for fs_basepath")
        mapfile = self.game.fs_basepath + '/' + self.game.fs_game + '/' + mapcycle
        if not os.path.isfile(mapfile):
            if self.game.fs_homepath is None:
                try:
                    self.game.fs_homepath = self.getCvar('fs_homepath').getString().rstrip('/')
                except:
                    self.game.fs_homepath = None
                    self.warning("Could not query server for fs_homepath")
            mapfile = self.game.fs_homepath + '/' + self.game.fs_game + '/' + mapcycle
        if not os.path.isfile(mapfile):
            self.error("Unable to find mapcycle file %s" % mapcycle)
            return None

        cyclemapfile = open(mapfile, 'r')
        lines = cyclemapfile.readlines()

        if len(lines) == 0:
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

        return maps
