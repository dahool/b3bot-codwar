#
# Plugin for BigBrotherBot(B3) (www.bigbrotherbot.com)
# Copyright (C) 2005 www.xlr8or.com
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
# Changelog:
# 1.1.0       : Added support for other games
# 1.1.1 - SGT : change event for warmup

__version__ = '1.1.1'
__author__  = 'xlr8or'

import b3, re, threading, time, os
import b3.events
import b3.plugin
import os.path

# from os.path
# isfile(path)
#    Return True if path is an existing regular file. This follows symbolic links, so both islink() and isfile() can be true for the same path.
#--------------------------------------------------------------------------------------------------
class ConfigmanagerPlugin(b3.plugin.Plugin):
    _map = None
    _mappath = None
    _gametype = None
    _gametypepath = None
    _typeandmap = None
    _typeandmappath = None
    _mainconfpath = ''
    _confpath = ''
    _modpath = ''
    _gameName = ''

    def onStartup(self):
        """\
        Initialize plugin settings
        """
        # Register our events
        self.verbose('Registering events')
        #self.registerEvent(b3.events.EVT_GAME_ROUND_START)
        self.registerEvent(b3.events.EVT_GAME_WARMUP)
        self.debug('Started')

    def onLoadConfig(self):
        # load our settings
        self.verbose('Loading config')
    
        # the name of the running parser
        self._gameName = self.console.gameName

        self._confpath = self.console.getCvar('fs_homepath')
        if self._confpath != None:
            self._confpath = self._confpath.getString()
    
        self._modpath = self.console.getCvar('fs_game')
        if self._modpath != None:
            self._modpath = self._modpath.getString()
        elif self._gameName[:3] == 'cod':
            self._modpath = 'main'
        elif self._gameName[:3] == 'iou':
            self._modpath = 'q3ut4'
        elif self._gameName[:3] == 'wop':
            self._modpath = 'wop'

        # Not really needed but to make sure we dont get stuck in the CoD root dir.
        #if self._modpath == '':
        #  self._modpath = 'main'

        self._confpath += '/' + self._modpath + '/'
        self.bot('Store your b3_<gametype>_<mapname>.cfg, b3_<gametype>.cfg and/or b3_main.cfg here:')
        self.bot('GameConfigPath: %s for game: %s' %(self._confpath, self._gameName))

    def onEvent(self, event):
        """\
        Handle intercepted events
        """
        if event.type == b3.events.EVT_GAME_WARMUP:
            c = self.console.game
            self._typeandmap = 'b3_%s_%s.cfg' % (c.gameType, c.mapName)
            self._typeandmappath = '%sb3_%s_%s.cfg' % (self._confpath, c.gameType, c.mapName)
            self.debug('Type and Map Config: %s' %(self._typeandmappath))
            self._gametype = 'b3_%s.cfg' % (c.gameType)
            self._gametypepath = '%sb3_%s.cfg' % (self._confpath, c.gameType)
            self.debug('Gametype Config: %s' %(self._gametypepath))
            self._mainconfpath = '%sb3_main.cfg' % (self._confpath)
            self.debug('Main Config: %s' %(self._mainconfpath))
     
            t1 = threading.Timer(1, self.checkConfig)
            t1.start()

    def checkConfig(self):
        """\
        Check and run the configs
        """
        if os.path.isfile(self._typeandmappath):       # b3_<gametype>_<mapname>.cfg
            self.console.write('exec %s' % self._typeandmap)
            self.debug('Executing %s' %(self._typeandmappath))
        elif os.path.isfile(self._gametypepath):       # b3_<gametype>.cfg
            self.console.write('exec %s' % self._gametype)
            self.debug('Executing %s' %(self._gametypepath))
        elif os.path.isfile(self._mainconfpath):       # b3_main.cfg
            self.console.write('exec b3_main.cfg')
            self.debug('Executing %s' %(self._mainconfpath))
        else:
            self.debug('No matching configs found.')
