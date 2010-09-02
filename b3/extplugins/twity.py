#
# TwityPlugin
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
# 08/31/2010 - SGT
# Use oAuth authentication
# 01/18/2010 - SGT
# remove format mark
# 01/16/2010 - SGT
# add unban event
# 01/15/2010 - 1.0.0 - SGT

__version__ = '1.0.4'
__author__  = 'SGT'

import re
import time

import tweepy

import b3, threading, time
import b3.events
import b3.plugin
import poweradminurt as padmin

#--------------------------------------------------------------------------------------------------
class TwityPlugin(b3.plugin.Plugin): 
    
    def onStartup(self):
        self.submark = re.compile('(\^\d)')
        self._adminPlugin = self.console.getPlugin('admin')
        self.servername = self.console.getCvar("sv_hostname").getString()
        self.api = None

        self.registerEvent(b3.events.EVT_CLIENT_BAN)
        self.registerEvent(b3.events.EVT_CLIENT_BAN_TEMP)
        self.registerEvent(b3.events.EVT_CLIENT_UNBAN)
        self.registerEvent(b3.events.EVT_CLIENT_PUBLIC)

        self.post_update("Started")

    def onLoadConfig(self):
        self._key = self.config.get('settings','consumer_key')
        self._secret = self.config.get('settings','consumer_secret')
        self._token = self.config.get('settings','access_token')
        self._token_secret = self.config.get('settings','secret_token')
        self._show_password = self.config.getboolean('settings','showpassword')
        
    def onEvent(self, event):
        if (event.type == b3.events.EVT_CLIENT_BAN or
            event.type == b3.events.EVT_CLIENT_BAN_TEMP):
            self._ban_event(event)
        elif event.type == b3.events.EVT_CLIENT_PUBLIC:
            self._public_event(event)
        elif event.type == b3.events.EVT_CLIENT_UNBAN:
            self._unban_event(event)
        return
      
    def post_update(self, message):
        message = "(%s) %s" % (self.servername,message)
        message = self.submark.sub('',message)
        self.debug(message)
        p = threading.Thread(target=self._twitthis, args=(message,))
        p.start()
        
    def _get_connection(self):
        try:
            self.debug("Get connection")
            auth = tweepy.OAuthHandler(self._key, self._secret)
            auth.set_access_token(self._token, self._token_secret)
            self.api = tweepy.API(auth)
        except:
            self.error(e)
            return False
        else:
            return True
        
    def _twitthis(self, message):
        if not self.api:
            if not self._get_connection():
                return
        try:
            self.debug("Post update")
            self.api.update_status(status=message)
            self.debug("Message posted!")
            return
        except Exception, e:
            self.error(e)

    def _unban_event(self, event):
        message = "%s [%s] was unbanned by %s [%s]" % (event.client.name, event.client.id,event.data.name, event.data.id)
        self.post_update(message)
    
    def _ban_event(self, event):
        if event.data.find("banned by") <> -1:
            self.post_update(event.data)

    def _public_event(self, event):
        if event.data == "":
            msg = "Server opened by %s" % event.client.name
        else:
            if self._show_password:
                msg = "Server closed by %s [%s]" % (event.client.name,event.data)
            else:
                msg = "Server closed by %s" % event.client.name
        self.post_update(msg)

def do_initial_setup():
    import b3.config
    import pprint
    
    config = b3.config.load("@b3/extplugins/conf/twity.xml")
    key = config.get('settings','consumer_key')
    secret = config.get('settings','consumer_secret')
    print "Prepare auth"
    twitter = tweepy.OAuthHandler(key, secret)
    print "Paste into browser:"
    print(twitter.get_authorization_url())
    # Get the pin # from the user and get our permanent credentials
    pin = raw_input('What is the PIN? ').strip()
    access_token = twitter.get_access_token(verifier=pin)
    
    print("oauth_token: " + access_token.key)
    print("oauth_token_secret: " + access_token.secret)
        
    # Do a test API call using our new credentials
    api = tweepy.API(twitter)
    user_timeline = api.user_timeline()

    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(user_timeline)

    print("oauth_token: " + access_token.key)
    print("oauth_token_secret: " + access_token.secret)
    
if __name__ == '__main__':
    from b3.fake import fakeConsole
    from b3.fake import joe
    import sys
    
    if len(sys.argv)>1 and sys.argv[1]=="setup":
        do_initial_setup()
    else:
        setattr(fakeConsole.game,'fs_basepath','/home/gabriel/io1')
        setattr(fakeConsole.game,'fs_game','q3ut4')
        fakeConsole.setCvar('sv_hostname','C3')

        p = TwityPlugin(fakeConsole, '@b3/extplugins/conf/twity.xml')
        p.onStartup()
        p.post_update("System test")
