#
# xMaps Plugin for BigBrotherBot(B3) (www.bigbrotherbot.com)
# Copyright (C) 2009 Sergio Gabriel Teves (SGT)
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

__version__ = '1.0.1'
__author__  = 'SGT'

import b3
import string
import b3.plugin
from b3 import maplist

#--------------------------------------------------------------------------------------------------
class XmapsPlugin(b3.plugin.Plugin):

    _adminPlugin = None
 
    def startup(self):
        """\
        Initialize plugin settings
        """
        # get the admin plugin so we can register commands
        self._adminPlugin = self.console.getPlugin('admin')
        if not self._adminPlugin:
        # something is wrong, can't start without admin plugin
            self.error('Could not find admin plugin')
            return False
    
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
                  
        self.debug('Started')

    def getCmd(self, cmd):
        cmd = 'cmd_%s' % cmd
        self.debug('Looking for %s' % cmd)
        if hasattr(self, cmd):
            func = getattr(self, cmd)
            return func
        self.debug('%s not found' % cmd)
        return None

    def cmd_zsetnextmap(self, data, client, cmd=None):
        """\
        <mapname> - Set the nextmap.
        """

        if not data:
            client.message('^7Invalid or missing data, try !help setnextmap')
        return False
   
        try:
            mfile = maplist.listCycleMaps(self.console, data)
            self.console.write( 'g_nextmap "%s"' % mfile )
            map = self.console.getNextMap()
            self.console.say('^7Nextmap is: ^2%s' % map)
            return True
        except Exception, e:
            client.message('^7%s' % str(e))
            return False
            
    def cmd_zmap(self, data, client, cmd=None):
        """\
        <map> - switch current map
        """
        if not data:
            client.message('^7You must supply a map to change to.')
        return

        try:
            mfile = maplist.listCycleMaps(self.console, data)
            self.console.say('^7Changing map to %s' % mfile)
            time.sleep(1)
            self.console.write('map %s' % mfile)
            return True
        except Exception, e:
            client.message('^7%s' % str(e))
            return False

    def cmd_zmaps(self, data, client=None, cmd=None):
        """\
        - list the server's map rotation
        [name] - list maps matching name
        [N] - list maps by page number
        """
        if not self._adminPlugin.aquireCmdLock(cmd, client, 60, True):
            client.message('^7Do not spam commands')
            return

        maxList = 30
        page = None
        maps = maplist.listCycleMaps(self.console)
        if maps:
            if data:
                if data.isdigit():
                    page = int(data)
                    if page == 0:
                        client.message('^7Invalid page number')
                        return
                    else:
                        self.debug('List len %d' % len(maps))
                        if len(maps)<=maxList:
                            total = 1
                        else:
                            ft = float(len(maps))/float(maxList)
                            it = len(maps)/maxList
                            if ft > it:
                                total = it+1
                            else:
                                total = it
                        if page > total:
                            client.message('^7Page doesn\'t exists. Total pages %d' % total)
                            return
                        showpage = page * maxList
                        if showpage > len(maps):
                            showpage = len(maps)
                        maps = maps[showpage-maxList:showpage]
                else:
                    data = data.strip().lower()
                    nmaps = []
                    for m in maps:
                        if m.lower().find(data)>-1:
                            nmaps.append(m)
                    maps = nmaps

            if len(maps)>maxList:
                if data:
                    client.message('^7Map list is too big. Try to be more specific.')
                else:
                    client.message('^7Map list is too big. Try !maps <name> to filter the list.')
            else:
                if page:
                    cmd.sayLoudOrPM(client, '^7Map list [page %d of %d]: ^2%s' % (page,total,string.join(maps, '^7, ^2')))
                else:
                    cmd.sayLoudOrPM(client, '^7Map list: ^2%s' % string.join(maps, '^7, ^2'))
        else:
            client.message('^7Error: could not get map list')
            
if __name__ == '__main__':
  print '\nThis is version '+__version__+' by '+__author__+' for BigBrotherBot.\n'
