#
# BigBrotherBot(B3) (www.bigbrotherbot.com)
# iourt parser extend for survivor winner catch
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
# 2010-05-12 - Initial version

__author__  = 'SGT'
__version__ = '1.0.0'

import os

import b3
import b3.events
import b3.parsers.iourt41

class Wiourt41Parser(b3.parsers.iourt41.Iourt41Parser):
          
    def OnSurvivorwinner(self, action, data, match=None):
        self.debug('EVENT: OnSurvivorwinner')
        return b3.events.Event(b3.events.EVT_SURVIVOR_WIN, data)  

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
