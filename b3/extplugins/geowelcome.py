#
# GeoIP Welcome
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
# 11/12/2009 - 1.0.0 - SGT
# Initial version
# 11/28/2009 - 1.0.1 - SGT
# Fix enconding issues
# 12/02/2009 - 1.0.2 - SGT
# Add broadcast
# 01/15/2010 - 1.0.3 - SGT
# Do not broadcast disconnected clients
# 02/01/2010 - 1.0.4 - SGT
# Add message format 
# 04-22-2010 - 1.0.5 - SGT
# Add cmd_greeting removed from the admin plugin since b3 1.3
# indent to 4 spaces
# 04-28-2010 - 1.1.0 - SGT
# Move whereis command from locator plugin
# Add country filter from countryfilter plugin
# 1.1.1 - SGT
# fix minor error in !wis
# 08-24-2010 - 1.1.2 - SGT
# Change in broadcast for cod servers
# Added some more debugs logs
# 11-16-2010 - 1.1.3 - SGT
# If we can't get location allow all clients to connect
# 05-25-2012 - 1.1.3 - SGT
# Some changes in allow to connect

__version__ = '1.1.4'
__author__  = 'SGT'

import b3, threading, time
import b3.events
from b3.plugins.welcome import WelcomePlugin
from b3 import geoip
from b3.translator import translate

#--------------------------------------------------------------------------------------------------
class GeowelcomePlugin(WelcomePlugin):

    def onLoadConfig(self):
        self._adminPlugin = self.console.getPlugin('admin')

        self.LoadWelcomeConfig()
        self.LoadLocatorConfig()
        self.LoadFilterConfig()
        
        # check if we have greeting command, if not, we assume we are using b3 1.2.x
        if hasattr(self,'cmd_greeting'):
            self.debug('Using self greeting command')
            try:
                self._cmd_greeting_minlevel = self.config.getint('commands', 'greeting')
            except:
                self._cmd_greeting_minlevel = 20
                self.warning('using default value %s for command !greeting' % self._cmd_greeting_minlevel)
            
            if self._adminPlugin:
                self._adminPlugin.registerCommand(self, 'greeting', self._cmd_greeting_minlevel, self.cmd_greeting)
        else:
            self.debug('Using admin greeting command')

    def LoadFilterConfig(self):
        try:
            self._enablefilter = self.config.getboolean('settings', 'enablefilter')
        except:
            self._enablefilter = False
        try:
            self.cf_order = self.config.get('settings', 'cf_order')
        except:
            self.cf_order = 'allow,deny'
        try:
            self.cf_deny_from = self.config.get('settings', 'cf_deny_from')
        except:
            self.cf_deny_from = 'none'
        try:
            self.cf_allow_from = self.config.get('settings', 'cf_allow_from')
        except:
            self.cf_allow_from = 'all'
        try:
            self.ignore_ips = self.config.get('ignore', 'ips').split(",")
        except:
            self.ignore_ips = []
        
    def LoadLocatorConfig(self):
        try:
            self._locate_level = self.config.getint('commands', 'whereis')
        except:
            self._locate_level = 20
                    
        if self._adminPlugin:
            self._adminPlugin.registerCommand(self, 'whereis', self._locate_level,  self.cmd_locate,  'wis')
                    
    def LoadWelcomeConfig(self):
        self._welcomeFlags = self.config.getint('settings', 'flags')
        self._newbConnections = self.config.getint('settings', 'newb_connections')
        try:
            self._welcomeDelay = self.config.getint('settings', 'delay')
            if self._welcomeDelay < 15 or self._welcomeDelay > 90:
                self._welcomeDelay = 30
                self.debug('Welcome delay not in range 15-90 using 30 instead.')
        except:
            self._welcomeDelay = 30
        
        try:
            self._country_format = self.config.get('settings','country_format')
        except:
            self._country_format = '%(city)s (%(country_name)s)'
            self.debug('Using default country format')

        try:
            self._broadcast = self.config.getboolean('settings', 'broadcast')
        except:
            self._broadcast = True
                    
    def onEvent(self, event):
        if event.type == b3.events.EVT_CLIENT_AUTH:
            self.onClientConnect(event.client)

    def onClientConnect(self, client):
        if not client or \
            not client.id or \
            client.cid == None or \
            client.pbid == 'WORLD':
            return
        
        if self._enablefilter:
            is_allowed = self.isAllowToConnect(client)
        else:
            is_allowed = True
        
        if is_allowed:
            if  self._welcomeFlags < 1 or \
                self.console.upTime() < 300:
                return

            b = threading.Timer(10, self.broadcast, (client,))
            b.start()

            t = threading.Timer(self._welcomeDelay, self.welcome, (client,))
            t.start()
        else:
            location = self.get_client_location(client)
            if location:
                data = {
                    'name'  : client.name,
                    'country' : location['country_name'],
                }             
                message = self.getMessage('cf_deny_message', data)
                self.console.say(message)
                client.kick(reason='Reject connection from %s' % data['country'], silent=True)
                self.debug("Reject. %(name)s - %(country)s" % data)
    
    def isAllowToConnect(self, client):
        # I will use it anyway so, lets get it
        country = self.get_client_location(client)
        if not country or not country['country_code']:
            # allow all if we can't get country
            return True
        countryCode = country['country_code']
        
        # this part is taken from countryfilter plugin
        result = True

        if client.ip in self.ignore_ips:
            self.debug('Ip address is on ignorelist, allways allowed to connect')
            result = True
        elif 'allow,deny' == self.cf_order:
            result = False # deny
            if -1 != self.cf_allow_from.find('all'):
                result = True
            if -1 != self.cf_allow_from.find(countryCode):
                result = True
            if -1 != self.cf_deny_from.find('all'):
                result = False
            if -1 != self.cf_deny_from.find(countryCode):
                result = False
        else: # 'deny,allow' (default)
            result = True; # allow
            if -1 != self.cf_deny_from.find('all'):
                result = False
            if -1 != self.cf_deny_from.find(countryCode):
                result = False
            if -1 != self.cf_allow_from.find('all'):
                result = True
            if -1 != self.cf_allow_from.find(countryCode):
                result = True
        return result        
    
    def get_client_location(self, client):
        if client.isvar(self,'localization'):
            return client.var(self, 'localization').value    
        else:
            # lets find the country
            try:
                ret = geoip.geo_ip_lookup(client.ip)
                if ret:
                    client.setvar(self, 'localization', ret)
                return ret
            except Exception, e:
                self.error(e)
                return False
    
    def broadcast(self, client):
        if client.connected:
            if self._broadcast and self.get_client_location(client):
                info = {
                    'name'  : client.exactName,
                    'country'  : translate(self._country_format % self.get_client_location(client)),
                }
                self.debug('Connected %s from %s' % (client.ip,info['country']))
                self.debug('Broadcasting location')
                if self.console.gameName.startswith('cod'):
                    self.console.say(self.getMessage('broadcast', info))
                else:
                    self.console.write(self.getMessage('broadcast', info))
            else:
                self.debug('Broadcasting disable or client doesn\'t have location data')
        else:
            self.debug('Broadcasting location')
            
    def welcome(self, client):
        _timeDiff = 0
        if client.lastVisit:
            self.debug('LastVisit: %s' %(self.console.formatTime(client.lastVisit)))
            _timeDiff = self.console.time() - client.lastVisit
        else:
            self.debug('LastVisit not available. Must be the first time.')
            _timeDiff = 1000000 # big enough so it will welcome new players

        # don't need to welcome people who got kicked or where already welcomed in the last hour
        if client.connected and _timeDiff > 3600:
            info = {
                'name'    : client.exactName,
                'id'    : str(client.id),
                'connections' : str(client.connections)
            }

            if client.maskedGroup:
                info['group'] = client.maskedGroup.name
                info['level'] = str(client.maskedGroup.level)
            else:
                info['group'] = 'None'
                info['level'] = '0'

            if client.connections >= 2:
                info['lastVisit'] = self.console.formatTime(client.lastVisit)
            else:
                info['lastVisit'] = 'Unknown'

            if self.get_client_location(client):
                info['country'] = translate(self._country_format % self.get_client_location(client))
            
            if client.connections >= 2:
                self.debug('Newb welcome')
                if client.maskedGroup:
                    if self._welcomeFlags & 16:
                        client.message(self.getMessage('user', info))
                elif self._welcomeFlags & 1:
                        client.message(self.getMessage('newb', info))

                if self._welcomeFlags & 2 and client.connections < self._newbConnections:
                    if info.has_key('country'):
                        self.console.say(self.getMessage('announce_user_geo', info))
                    else:
                        self.console.say(self.getMessage('announce_user', info))
            else:
                self.debug('User welcome')
                if self._welcomeFlags & 4:
                    client.message(self.getMessage('first', info))
                if self._welcomeFlags & 8:
                    if info.has_key('country'):
                        self.console.say(self.getMessage('announce_first_geo', info))
                    else:
                        self.console.say(self.getMessage('announce_first', info))
                        
            if self._welcomeFlags & 32 and client.greeting:
                info['greeting'] = client.greeting % info
                self.console.say(self.getMessage('greeting', info))
            
        else:
            if _timeDiff <= 3600:
                self.debug('Client already welcomed in the past hour')

    def cmd_locate(self, data, client, cmd=None):
        """\
        <name> - show where the user is connected from
        """
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
      
        location = self.get_client_location(sclient)
        if location:
            country = translate(self._country_format % location)
            client.message('^3%s [@%s] ^7is connected from ^3%s' % (sclient.name,str(sclient.id),country)) 
            self.debug('[LOCATE] %s [@%s] is connected from %s' % (sclient.name,str(sclient.id),country))
        else:
            client.message('^7Cannot found client location.')
            self.debug('[LOCATE] Cannot found client location.')
