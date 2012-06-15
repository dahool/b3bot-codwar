# 2012-05-27 - 1.0.6 - SGT
# handle some events that takes to long in threads

__version__ = '1.0.6'
__author__  = 'Anubis'

import b3, threading, thread
import b3.events
import b3.plugin
import time
from b3 import clients
import datetime
import b3.cron

class TimeStats:
    came = None
    left = None 
    client = None

#--------------------------------------------------------------------------------------------------
class CtimePlugin(b3.plugin.Plugin):
    requiresConfigFile = False
    _clients = {} 
    _cronTab = None
    _max_age_in_days = 365
    _hours = 5
    _minutes = 0

    def onStartup(self):
        self.registerEvent(b3.events.EVT_CLIENT_AUTH)
        self.registerEvent(b3.events.EVT_CLIENT_DISCONNECT)
        self.query = self.console.storage.query
        tzName = self.console.config.get('b3', 'time_zone').upper()
        tzOffest = b3.timezones.timezones[tzName]
        hoursGMT = (self._hours - tzOffest)%24
        self.debug("%02d:%02d %s => %02d:%02d UTC" % (self._hours, self._minutes, tzName, hoursGMT, self._minutes))
        self.info('everyday at %2d:%2d %s, connection info older than %s days will be deleted'%(self._hours, self._minutes, tzName, self._max_age_in_days))
        self._cronTab = b3.cron.PluginCronTab(self, self.purge, 0, self._minutes, hoursGMT, '*', '*', '*')
        self.console.cron + self._cronTab

    #def onLoadConfig(self):
        #self._welcomeFlags = self.config.getint('settings', 'flags')
        #self._newbConnections = self.config.getint('settings', 'newb_connections')

    def purge(self):
        if not self._max_age_in_days or self._max_age_in_days == 0:
            self.warning('max_age is invalid [%s]'%self._max_age_in_days)
            return False

        self.info('purge of connection info older than %s days ...'%self._max_age_in_days)
        q = "DELETE FROM ctime WHERE came < %i"%(self.console.time() - (self._max_age_in_days*24*60*60))
        self.debug("CTIME QUERY: " + q)
        cursor = self.console.storage.query(q)
    
    def onEvent(self, event):
        if event.type == b3.events.EVT_CLIENT_AUTH:
            if  not event.client or \
                not event.client.id or \
                event.client.cid == None or \
                not event.client.connected or \
                event.client.pbid == 'WORLD':
                return
            
            thread.start_new_thread(self.update_time_stats_connected, (event.client,))
            
        elif event.type == b3.events.EVT_CLIENT_DISCONNECT:
            thread.start_new_thread(self.update_time_stats_exit, (event.data, ))

    def update_time_stats_connected(self, client):
        if (self._clients.has_key(client.cid)):
            self.debug("CTIME CONNECTED: Client exist! : " + str(client.cid));
            tmpts = self._clients[client.cid]
            if(tmpts.client.guid == client.guid):
                self.debug("CTIME RECONNECTED: Player " + client.exactName + " connected again, but playing since: " + str(tmpts.came))
                return
            else:
                del self._clients[client.cid]
        
        ts = TimeStats()
        ts.client = client
        ts.came = datetime.datetime.now()
        self._clients[client.cid] = ts
        self.debug("CTIME CONNECTED: Player " + client.exactName + " started playing at: " + str(ts.came))

    def formatTD(self, td):
        hours = td // 3600
        minutes = (td % 3600) // 60
        seconds = td % 60
        return '%s:%s:%s' % (hours, minutes, seconds) 
  
    def update_time_stats_exit(self, clientid):
        self.debug("CTIME LEFT:")
        if (self._clients.has_key(clientid)):
            ts = self._clients[clientid]
            # Sometimes PB in cod4 returns 31 character guids, we need to dump them. Lets look ahead and do this for the whole codseries.
            if(self.console.gameName[:3] == 'cod' and self.console.PunkBuster and len(ts.client.guid) != 32):
                pass
            else:
                ts.left = datetime.datetime.now()
                diff = (int(time.mktime(ts.left.timetuple())) - int(time.mktime(ts.came.timetuple())))
                
                self.debug("CTIME LEFT: Player:" + str(ts.client.exactName) + " played this time: " + str(diff) + " sec")
                self.debug("CTIME LEFT: Player:" + str(ts.client.exactName) + " played this time: " + self.formatTD(diff))
                #INSERT INTO `ctime` (`guid`, `came`, `left`) VALUES ("6fcc4f6d9d8eb8d8457fd72d38bb1ed2", 1198187868, 1226081506)
                q = 'INSERT INTO ctime (guid, came, gone, nick) VALUES (\"%s\", \"%s\", \"%s\", \"%s\")' % (ts.client.guid, int(time.mktime(ts.came.timetuple())), int(time.mktime(ts.left.timetuple())), ts.client.name)
                self.query(q)
                
            self._clients[clientid].left = None
            self._clients[clientid].came = None
            self._clients[clientid].client = None
                
            del self._clients[clientid]
           
        else:
            self.debug("CTIME LEFT: Player " + str(clientid) + " var not set!")            
