# BigBrotherBot(B3) (www.bigbrotherbot.com)
# Plugin for allowing registered users to kick
# Copyright (C) 2009 Sergio Gabriel Teves
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
# 12/02/2009 - 1.0.0 - SGT

__version__ = '1.0.0'
__author__  = 'SGT'

import b3
import b3.plugin
from b3 import geoip
from b3.translator import translate

class LocatorPlugin(b3.plugin.Plugin):
  _adminPlugin = None
  _level = 20
    
  def onStartup(self):
    self._adminPlugin = self.console.getPlugin('admin')
    if self._adminPlugin:
      self._adminPlugin.registerCommand(self, 'whereis', self._level,  self.cmd_locate,  'wi')

  def onLoadConfig(self):
    try:
      self._level = self.config.getint('settings', 'level')
    except:
      self._level = 20

  def cmd_locate(self, data, client, cmd=None):
    input = self._adminPlugin.parseUserCmd(data)
    if input:
      # input[0] is the player id
      sclient = self._adminPlugin.findClientPrompt(input[0], client)
      if not sclient:
        # a player matchin the name was not found, a list of closest matches will be displayed
        # we can exit here and the user will retry with a more specific player
        return False
    else:
      client.message('^7Invalid data, try !help whereis')
      return False
  
    if sclient.isvar(self,'country'):
      country = sclient.var(self, 'country').value    
    else:
      # lets find the country
      try:
        ret = geoip.geo_ip_lookup(sclient.ip)
        country = translate(u'%s (%s)' % (ret['city'],ret['country_name']))
        sclient.setvar(self, 'country', country)
      except Exception, e:
        self.error(e)
        client.message('^7Unable to find client location.')
        return False
    client.message('^3%s [@%s] ^7is connected from ^3%s' % (sclient.name,str(sclient.id),country)) 
