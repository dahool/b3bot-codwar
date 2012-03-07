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
# 2011-02-19 - SGT
# Create Survivor Winner Event
# Create Unban event
# B - 2012-03-07 - SGT
# Move common changes to upstream. Keep own methods only.

from b3.parsers.iourt41 import __version__ as parent_version

__author__  = 'SGT'
__version__ = parent_version + "B"

import os

import b3
import b3.events
import re
from b3.parsers.iourt41 import Iourt41Parser

class Iourt41AParser(Iourt41Parser):

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
