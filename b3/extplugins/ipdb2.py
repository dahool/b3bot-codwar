#
# BigBrotherBot(B3) (www.bigbrotherbot.com)
# Copyright (C) 2011 SGT
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
# 2011-04-21 - SGT - 1.1.0
# Implement new IPDB API
# 2011-05-08 - SGT - 1.1.1
# Send time in UTC
# Use twitter if available
# 2011-05-08 - SGT - 1.1.2
# We need to keep a list of the players CID to use on the disconnect event
# Allow to check for update only if autoudate is not enabled
# 2011-05-10 - SGT - 1.1.4
# Use alternative method if client is not found on disconnect
# 2011-05-12 - SGT - 1.1.6
# Send all dates as timestamp
# Fix issue in baninfo dump
# 2011-05-16 - SGT - 1.1.7
# Fix error no autoenabling when disabled
# 2011-05-18 - SGT - 1.1.8
# Fix error in dump baninfo
# 2011-05-19 - SGT - 1.1.9
# Fix error in string format in !ipdb
# Add force update command
# 2011-05-25 - SGT - 1.1.10
# Better exception handling
# Set timeout
# 2011-05-26 - SGT - 1.1.11
# Check if we missed and event
# Clean initial update
# 2011-05-28 - SGT - 1.1.12
# Fix issue with force update command
# 2011-05-28 - SGT - 1.1.13
# Handle disconnection in thread
# 2011-06-08 - SGT - 1.1.14
# Send admin name in baninfo
# Update service url
# 2011-06-10 - SGT - 1.1.15
# Change baninfo format
# Handle notice and unban command
# Encode xml entities
# 2011-06-13 - SGT - 1.2.0
# Add remote queue handling
# 2011-06-16 - SGT - 1.2.1
# Link user command
# 2011-07-10 - SGT - 1.2.2
# Add alive cron
# 2011-07-15 - SGT - 1.2.3
# Collect unban info
# 2011-08-29 - SGT - 1.2.4
# Include admin name and admin id in penalty
# 2011-09-05 - SGT - 1.2.5
# Minor fixes
# 2011-09-07 - SGT - 1.2.6
# Minor encoding fix
# 2011-09-26 - SGT - 1.2.7
# Change link user command to handle new API
# Put default commands in code
# 2011-10-12 - SGT - 1.2.8
# Increase update list size
# 2011-10-18 - SGT - 1.3.0
# Implement time diff
# Add event confirmation
# Use UTC for times
# Fix clean events
# Add refresh event
# 2011-11-02 - SGT - 1.3.1
# Fix minor issues with remote notices
# 2011-11-03 - SGT - 1.3.2
# Fix minor issue with empty list update
# 2011-11-03 - SGT - 1.3.3
# Refresh player on group update
# Reload host name in each server name update

__author__  = 'SGT'
__version__ = '1.3.3'

import b3, time, threading, xmlrpclib, re, thread
import b3.events
import b3.plugin
import b3.cron
import random, datetime
import socket
from b3.clients import ClientNotice, ClientBan
from b3.querybuilder import QueryBuilder

try:
    import hashlib
    hash = hashlib.sha1
except ImportError:
    import sha
    hash = sha.new
    
#--------------------------------------------------------------------------------------------------
class Ipdb2Plugin(b3.plugin.Plugin):
    _url = 'http://api.iddb.com.ar/api/v4/xmlrpc'

    _timeout = 15
    
    _twitterPlugin = None
    _adminPlugin = None
    
    _pluginEnabled = True
    _cronTab    = []
    _banCronTab = None
    _rpc_proxy  = None
    _interval   = 2
    _key        = None
    _hostname   = None
    _last       = None
    _always_update = False
    _banInfoInterval = 2
    _delta = None
    _failureCount = 0
    _failureMax = 20
    _eventqueue = []
    _banInfoDumpTime = 7
    #_clientInfoDumpTime = 7
    _color_re = re.compile(r'\^[0-9]')
    _maxOneTimeUpdate = 50
    
    _updated = False
    _notifyUpdateLevel = 80
    _autoUpdate = True
    _running = False
    _onlinePlayers = []
    _banqueue = []
    _updateCrontab = None
    _showBanAdmin = True
    
    _remotequeue = []
    
    _clientCache = {}
    
    _remotePermission = 15 # all
    
    _remoteInterval = 30
    
    _EVENT_CONNECT = "connect"
    _EVENT_DISCONNECT = "disconnect"
    _EVENT_UPDATE = "update"
    _EVENT_BAN = "banned" # 1
    _EVENT_ADDNOTE = "addnote" # 4
    _EVENT_DELNOTE = "delnote" # 8
    _EVENT_UNBAN = "unbanned" # 2
    _EVENT_REFRESH = "refresh"
    
    _BAN_QUERY = "SELECT c.id as client_id, p.id as id, p.duration as duration, p.reason as reason, p.time_add as time_add, p.admin_id as admin_id "\
    "FROM penalties p INNER JOIN clients c ON p.client_id = c.id "\
    "WHERE (p.type='Ban' OR p.type='TempBan') AND (p.time_expire=-1 OR p.time_expire > %(now)d) "\
    "AND p.time_edit >= %(since)d AND p.inactive=0 AND keyword <> 'ipdb2'"

    _UNBAN_QUERY = "SELECT c.id as client_id, p.id as id "\
    "FROM penalties p INNER JOIN clients c ON p.client_id = c.id "\
    "WHERE (p.type='Ban' OR p.type='TempBan') AND (p.inactive = 1 OR (p.time_expire > 0 AND p.time_expire < %(now)d)) "\
    "AND (keyword = 'ipdb2' or keyword = 'ipdb')"
            
    # keep commands here in case conf file is outdated
    _commands = {"userlink-link": 2,
                 "dbaddnote-addnote": 40,
                 "dbdelnote-delnote": 40,
                 "dbclearban-clearban": 60,
                 "showqueue-ipdb": 1,
                 "iddbupdate-ipdbup": 80}
                 
    def onStartup(self):
        self._rpc_proxy = xmlrpclib.ServerProxy(self._url)
        
        self._eventqueue = []
        self._banqueue = []
        self._onlinePlayers = []
        self._clientCache = {}
        
        self.registerEvent(b3.events.EVT_CLIENT_AUTH)
        self.registerEvent(b3.events.EVT_CLIENT_DISCONNECT)
        self.registerEvent(b3.events.EVT_CLIENT_NAME_CHANGE)
        self.registerEvent(b3.events.EVT_CLIENT_BAN)
        self.registerEvent(b3.events.EVT_CLIENT_BAN_TEMP)
        self.registerEvent(b3.events.EVT_ADMIN_COMMAND)
         
        try:
            self.registerEvent(b3.events.EVT_CLIENT_UNBAN)
        except:
            self.warning('Unban event not available')
        
        self.setupCron()
        self.updateName()
        
        # get the admin plugin so we can register commands
        self._adminPlugin = self.console.getPlugin('admin')
        if not self._adminPlugin:
            self.error('Could not find admin plugin')
        else:
            # register our commands
            for cmd, level in self._commands.items():
                sp = cmd.split('-')
                alias = None
                if len(sp) == 2:
                    cmd, alias = sp
                try:
                    level = self.config.get('commands', cmd)
                except:
                    pass
                func = self.getCmd(cmd)
                if func:
                    self._adminPlugin.registerCommand(self, cmd, level, func, alias)

        self._twitterPlugin = self.console.getPlugin('twity')
        if not self._twitterPlugin:
            self.debug("Twitter plugin not avaiable.")

    def getCmd(self, cmd):
        cmd = 'cmd_%s' % cmd
        if hasattr(self, cmd):
            func = getattr(self, cmd)
            return func

        return None
            
    def setupCron(self):
        self.debug("will send update every %02d minutes" % self._interval)
        self._cronTab.append(b3.cron.PluginCronTab(self, self.update, minute='*/%d' % self._interval))
        self._cronTab.append(b3.cron.PluginCronTab(self, self.updateBanQueue, minute='*/30'))
        self._cronTab.append(b3.cron.PluginCronTab(self, self.validateOnlinePlayers, minute='*/10'))
        if self._banInfoInterval > 0:
            rmin = random.randint(5,59)
            self.debug("will send ban info every %02d:%02d hours" % (self._banInfoInterval,rmin))
            self._delta = datetime.timedelta(hours=self._banInfoInterval, minutes=15+rmin)
            self._cronTab.append(b3.cron.PluginCronTab(self, self.updateBanInfo, 0, rmin, '*/%d' % self._banInfoInterval))
        if self._banInfoDumpTime >= 0:
            self.debug("will dump ban info at %02d" % (self._banInfoDumpTime))
            self._cronTab.append(b3.cron.PluginCronTab(self, self.dumpBanInfo, 0, random.randint(5,59), self._banInfoDumpTime))
            self._cronTab.append(b3.cron.PluginCronTab(self, self.dumpUnbanInfo, 0, random.randint(5,59), self._banInfoDumpTime))
        if self._remotePermission > 0:
            self._cronTab.append(b3.cron.PluginCronTab(self, self.processRemoteQueue, minute='*/%d' % self._remoteInterval))
        if self._showAdInterval > 0:
            self._cronTab.append(b3.cron.PluginCronTab(self, self.consoleMessage, minute='*/%d' % self._showAdInterval))

        rhour = random.randint(0,23)
        rmin = random.randint(5,59)
        self.debug("will send heartbeat at %02d:%02d every day" % (rhour,rmin))
        self._cronTab.append(b3.cron.PluginCronTab(self, self.updateName, 0, rmin, rhour, '*', '*', '*'))

        if self._updateCrontab:
            self.console.cron - self._updateCrontab
        
        self._updateCrontab = b3.cron.PluginCronTab(self, self.checkNewVersion, 0, rmin, '*/12')
        self.console.cron + self._updateCrontab

    def onLoadConfig(self):
        try:
            self._key = self.config.get('settings', 'key')
        except:
            raise Exception("Invalid key")
        try:
            self._interval = self.config.getint('settings', 'interval')
        except:
            pass
        try:
            self._banInfoDumpTime = self.config.getint('settings', 'baninfodump')
        except:
            pass
        try:
            self._banInfoInterval = self.config.getint('settings', 'baninfointerval')
        except:
            pass
        try:
            self._notifyUpdateLevel = self.config.getint('settings', 'updatelevelwarn')
        except:
            pass
        try:
            self._autoUpdate = self.config.getboolean('settings', 'enableautoupdate')
        except:
            pass
        try:
            self._showBanAdmin = self.config.getboolean('settings', 'showbanadmin')
        except:
            pass            
        try:
            self._remotePermission = self.config.getint('settings', 'remotepermission')
        except:
            pass
        try:
            self._showAdInterval = self.config.getint('settings', 'showmessageinterval')
        except:
            self._showAdInterval = 30
                                                    
    def onEvent(self, event):
        if event.type == b3.events.EVT_CLIENT_AUTH:
            self.onClientConnect(event.client)
        elif event.type == b3.events.EVT_CLIENT_NAME_CHANGE:
            self.onClientUpdate(event.client)
        elif event.type == b3.events.EVT_CLIENT_DISCONNECT:
            thread.start_new_thread(self.onClientDisconnect,(event.data,))
        elif event.type == b3.events.EVT_CLIENT_BAN or event.type == b3.events.EVT_CLIENT_BAN_TEMP:
            self.onClientBanned(event.client)
        elif event.type == b3.events.EVT_ADMIN_COMMAND:
            thread.start_new_thread(self.handleAdminCommand,(event.data,event.client))
        else:
            try:
                if event.type == b3.events.EVT_CLIENT_UNBAN:
                    self.onClientUnban(event.client)
            except:
                pass

    # =============================== EVENT HANDLING ===============================

    def handleAdminCommand(self, data, client = None):
        command, data, result = data
        # old b3 send function instead of command
        if hasattr(command,'__call__'):
            command_name = command.func_name
        else:
            command_name = command.func.func_name
        
        if 'cmd_notice' == command_name:
            self.handleAddNoticeCommand(data, client)
        elif 'cmd_unban' == command_name:
            self.handleUnbanCommand(data, client)
        elif 'cmd_ungroup' == command_name or 'cmd_putgroup' == command_name:
            self.handleGroupCommand(data, client)
            
    def handleGroupCommand(self, data, client):
        self.debug("Handle group command")
        try:
            cid, group = self._adminPlugin.parseUserCmd(data)
            sclient = self._adminPlugin.findClientPrompt(cid, None)
            if sclient:
                self.debug("Refresh client %s" % sclient.name)
                self._eventqueue.append(self._buildEventInfo(self._EVENT_REFRESH, sclient, sclient.timeEdit))
        except Exception, e:
            self.error(str(e))
            
    def handleUnbanCommand(self, data, client):
        # if we are handling the event, discard
        self.debug("Handle unban command")
        try:
            ev = b3.events.EVT_CLIENT_UNBAN
        except:
            try:
                cid, reason = self._adminPlugin.parseUserCmd(data)
                sclient = self._adminPlugin.findClientPrompt(cid, None)
                if sclient and sclient.numBans == 0:
                    self.onClientUnban(sclient)
            except Exception, e:
                self.error(str(e))
            
    def handleAddNoticeCommand(self, data, client):
        # we have no way to know if the notice was actually added
        # get the last notice from the database
        self.debug("Handle add notice command")
        try:
            cid, notice = self._adminPlugin.parseUserCmd(data)
            sclient = self._adminPlugin.findClientPrompt(cid, None)
            if sclient:
                penalty = self.console.storage.getClientLastPenalty(sclient, 'Notice')
                if penalty and penalty.adminId == client.id: # check if is the same admin :)
                    self.add_notice(penalty.reason, sclient, client)
        except Exception, e:
            self.error(str(e))
                    
    def _cache_connect(self, client):
        self._onlinePlayers.append(client)
        self._clientCache[client.cid] = client

    def onClientConnect(self, client):
        if not client or \
            not client.id or \
            client.cid == None or \
            client.pbid == 'WORLD' or \
            not client.connected:
            return
    
        self.debug('Client connected: %s' % client.name)    
        self._cache_connect(client)
        
        self._eventqueue.append(self._buildEventInfo(self._EVENT_CONNECT, client))
        
        if self._updated:
            if client.maxLevel >= self._notifyUpdateLevel:
                if not client.var(self, 'ipdb_warn') or not client.var(self, 'ipdb_warn').value:
                    b = threading.Timer(30, self.notifyUpdate, (client,))
                    b.start()                
        
    def onClientBanned(self, client):
        self.debug('Client banned: %s' % client.name)
        self._banqueue.append(client)
            
    def onClientDisconnect(self, cid):
        self.debug('Client disconnected: %s' % cid)
        if self._clientCache.has_key(cid):
            client = self._clientCache[cid]
            del self._clientCache[cid]
            self._eventqueue.append(self._buildEventInfo(self._EVENT_DISCONNECT, client))
            
            try:
                if client in self._onlinePlayers:            
                    self._onlinePlayers.remove(client)
            except Exception, e:
                self.error(e)
            
        else:
            self.debug('Not found cid %s. Try alternative method' % cid)
            self.validateOnlinePlayers()

    def onClientUpdate(self, client):
        self.debug('Client updated %s' % client.name)
        self._eventqueue.append(self._buildEventInfo(self._EVENT_UPDATE, client))

    def onClientUnban(self, client):
        self.debug('Client unbanned %s' % client.name)
        self._eventqueue.append(self._buildEventInfo(self._EVENT_UNBAN, client, client.timeEdit))
            
    # =============================== Processing ===============================
    def consoleMessage(self):
        self.console.say('^5IPDB ^7is watching you')
        
    def _buildClientInfo(self, client, timeEdit = None):
        if not timeEdit:
            timeEdit = int(time.time())
        info = [self.sanitize(client.name), client.guid, client.id, client.ip, client.maxLevel, timeEdit]
        return info
        
    def _buildEventInfo(self, event, client, timeEdit = None):
        self.verbose('Queued event %s for %s' % (event, client.name))
        info = [event]
        info.extend(self._buildClientInfo(client, timeEdit))
        self.verbose(info)
        return info
    
    def cleanEvents(self):
        '''clean connect events in case of disabled.
        '''
        tempList = self._eventqueue[:]
        tempClients = []
        self._eventqueue = []
        for event in tempList:
            # check if guid is already in the list
            if not event[2] in tempClients:
                if event[0] in (self._EVENT_CONNECT, self._EVENT_UPDATE):
                    event[0] = self._EVENT_REFRESH
                self._eventqueue.append(event)
                tempClients.append(event[2])
        maxQueueSize = self._maxOneTimeUpdate * 2
        if len(self._eventqueue) > maxQueueSize:
            self._eventqueue = self._eventqueue[:maxQueueSize:-1]
           
    # =============================== UPDATE ===============================
    def send_update(self, list):
        try:
            socket.setdefaulttimeout(self._timeout)
            self._rpc_proxy.server.update(self._key, list, int(time.time()))
            self._failureCount = 0
        except xmlrpclib.ProtocolError, protocolError:
            self.error(str(protocolError))
            self.increaseFail()
            raise Exception()
        except xmlrpclib.Fault, applicationError:
            self.error(applicationError.faultString)
            self.increaseFail()
            raise Exception()
        except socket.timeout, timeoutError:
            self.warning("Connection timed out")
            raise Exception()
        except socket.error, socketError:
            self.error(str(socketError))
            self.increaseFail()
            raise Exception()
        except Exception, e:
            self.error("General error. %s" % str(e))
        finally:
            socket.setdefaulttimeout(None)
        
    def validateOnlinePlayers(self):
        self.debug('Check online players')
        
        clients = self.console.clients.getList()
        for client in clients:
            if client not in self._onlinePlayers:
                self._cache_connect(client)
                self._eventqueue.append(self._buildEventInfo(self._EVENT_CONNECT, client))
                self.verbose('Missed connect')
        
        for client in self._onlinePlayers[:]:
            if client not in clients:
                self._eventqueue.append(self._buildEventInfo(self._EVENT_DISCONNECT, client))
                try:
                    self._onlinePlayers.remove(client)
                    if self._clientCache[client.cid].id == client.id:
                        del self._clientCache[client.cid]
                except:
                    pass
                self.verbose('Missed disconnect')
        
        if len(clients) == 0:
            # nobody here, lets send an empty list
            # send first any item in the queue
            if not self._running:
                self.update()
            else:
                time.sleep(self._timeout)
            self.debug("Sending empty list")
            try:
                self.send_update([])
            except:
                pass
            
    def _buildBanInfo(self, penalty, client):
        status = None
        if penalty and (penalty.duration < 1 or penalty.duration > 30): # no tempban less than 30 minutes
            if penalty.duration == -1 or penalty.duration == 0:
                pType = "pb"
            else:
                pType = "tb"

            admin_name = ""
            admin_id = 0
            if self._showBanAdmin:
                if penalty.adminId and penalty.adminId > 0:
                    admin = self._adminPlugin.findClientPrompt('@%s' % str(penalty.adminId), None)
                    if admin:
                        admin_name = admin.name
                        admin_id = admin.guid

            baninfo = [pType, penalty.timeAdd, penalty.duration, self.sanitize(penalty.reason), admin_name, admin_id]
            status = self._buildEventInfo(self._EVENT_BAN, client, client.timeEdit)
            self.verbose(baninfo)
            status.append(baninfo)
        return status
        
    def updateBanQueue(self):
        self.debug('Update ban queue')
        while len(self._banqueue) > 0:
            client = self._banqueue.pop()
            status = self._buildBanInfo(client.lastBan, client)
            if status:
                self._eventqueue.append(status)
                                            
    def notifyUpdate(self, client):
        self.verbose('Notify update')
        if self._autoUpdate:
            client.message('^7A new version of ^5IPDB ^7has been installed. Please restart the bot.')
        else:
            client.message('^7A new version of ^5IPDB ^7is available.')
        client.setvar(self, 'ipdb_warn', True)

    def updateName(self):
        self._hostname = self.sanitize(self.console.getCvar('sv_hostname').getString())
        try:
            self.debug('Update server name')
            socket.setdefaulttimeout(self._timeout)
            self._rpc_proxy.server.updateName(self._key, self._hostname, [__version__, self._remotePermission])
            self.do_enable()
        except Exception, e:
            self.error("Error updating server name. %s" % str(e))
            if self.increaseFail():
                self.console.cron + b3.cron.OneTimeCronTab(self.updateName, '*/30')
        socket.setdefaulttimeout(None)
        
    def update(self):
        self.debug('Try update')
        if not self._running:
            self._running = True
            if len(self._eventqueue) > 0:
                last = len(self._eventqueue)
                if last > self._maxOneTimeUpdate: last = self._maxOneTimeUpdate
                status = self._eventqueue[0:last]
                self.bot("Updating %d" % len(status))
                try:
                    self.send_update(status)
                    del self._eventqueue[0:last]
                except:
                    pass
            self._running = False
        else:
            self.debug("Already running")

    def doInitialUpdate(self):
        self.debug('Do initial update')
        self._onlinePlayers = []
        self._clientCache = {}
        clients = self.console.clients.getList()
        for client in clients:
            self._cache_connect(client)
            self._eventqueue.append(self._buildEventInfo(self._EVENT_CONNECT, client))
        try:
            self.send_update([])
        except:
            pass
        time.sleep(self._timeout)
        self.update()

    def do_enable(self):
        self.debug('IPDB enabled')
        self._failureCount = 0
        current_st = self._pluginEnabled
        self._pluginEnabled = True
        for ct in self._cronTab:
            self.console.cron + ct
        if self._twitterPlugin and not current_st: # if it was disabled
            self._twitterPlugin.post_update('IPDB back on business.')
            
        b = threading.Thread(target=self.doInitialUpdate)
        b.start()
        
    def do_disable(self):
        self.debug('IPDB disabled')
        self._pluginEnabled = False
        for ct in self._cronTab:
            self.console.cron - ct
        
    def increaseFail(self):
        self._failureCount += 1
        self.debug('Update failed %d' % self._failureCount)
        if self._failureCount >= self._failureMax:
            self.do_disable()
            self.cleanEvents()
            self.console.cron + b3.cron.OneTimeCronTab(self.updateName, second=0, minute='*/30')
            self._failureCount = 0
            if self._twitterPlugin:
                self._twitterPlugin.post_update('IPDB too many failures. Disabled.')
            self.bot('Too many failures. Disabled')
            return False
        return True
        
    def updateBanInfo(self, sendAll = False):
        self.debug('Collect ban info')
        now = int(time.time())
        if sendAll:
            since = 1262314800
            q = self._BAN_QUERY + " LIMIT 20"
        else:
            since = int(time.mktime((datetime.datetime.utcnow() - self._delta).timetuple()))
            q = self._BAN_QUERY + " LIMIT 25"
        cursor = self.console.storage.query(q % {'now': now,
                                                'since': since})
                                                                  
        list = []
        keys = []
        while not cursor.EOF:
            r = cursor.getRow()
            client = self._adminPlugin.findClientPrompt("@%s" % r['client_id'], None)
            if client:
                penalty = ClientBan()
                penalty.duration = r['duration']
                penalty.clientId = client.id
                penalty.adminId = r['admin_id']
                penalty.reason = r['reason']
                penalty.timeAdd = r['time_add']
                status = self._buildBanInfo(penalty, client)
                if status: list.append(status)
            keys.append(r['id'])
            cursor.moveNext()
        
        if len(list) > 0:
            self.debug('Update ban info')
            if self._running:
                time.sleep(self._timeout)
            try:
                self._running = True
                self.send_update(list)
                cursor = self.console.storage.query("UPDATE penalties SET keyword = 'ipdb2' WHERE id IN (%s)" % ",".join(keys))
            except:
                pass
            self._running = False
        else:
            self.debug('No ban info to send')

    def dumpUnbanInfo(self):
        self.debug('Collect unban info')
        now = int(time.time())
        since = int(time.mktime((datetime.datetime.utcnow() - self._delta).timetuple()))
        q = self._UNBAN_QUERY + " LIMIT 25"
        cursor = self.console.storage.query(q % {'now': now,
                                                'since': since})
                                                                  
        list = []
        keys = []
        while not cursor.EOF:
            r = cursor.getRow()
            client = self._adminPlugin.findClientPrompt("@%s" % r['client_id'], None)
            if client:
                status = self._buildEventInfo(self._EVENT_UNBAN, client, client.timeEdit)
                list.append(status)
            keys.append(r['id'])
            cursor.moveNext()
        
        if len(list) > 0:
            self.debug('Update unban info')
            if self._running:
                time.sleep(self._timeout)
            try:
                self._running = True
                self.send_update(list)
                cursor = self.console.storage.query("UPDATE penalties SET keyword = '' WHERE id IN (%s)" % ",".join(keys))
            except:
                pass
            self._running = False
        else:
            self.debug('No ban info to send')
                
    def dumpBanInfo(self):
        self.debug('Collect all ban info')
        self.updateBanInfo(True)

    def checkNewVersion(self, force = False):
        if self._updated and not force:
            return
        p = PluginUpdater(__version__, self)
        self._updated, ver = p.verifiy(self._autoUpdate)
        if self._updated:
            self.bot('New version available')
            if self._twitterPlugin:
                self._twitterPlugin.post_update('IPDB %s is available.' % ver)

    def cmd_showqueue(self, data, client, cmd=None):
        if client.maxLevel >= 80:
            if self._pluginEnabled:
                cmd.sayLoudOrPM(client, '^7Hello. IPDB v%s is online.' % __version__)
                if len(self._eventqueue) == 0:
                    cmd.sayLoudOrPM(client, '^7Events queue is empty.')
                else:
                    cmd.sayLoudOrPM(client, '^7%d events pending in queue.' % len(self._eventqueue))
            else:
                cmd.sayLoudOrPM(client, '^7Hello. IPDB v%s is offline.' % __version__)
        else:
            if self._pluginEnabled:
                cmd.sayLoudOrPM(client, '^7Hello. IPDB v%s is online.' % __version__)
            else:
                cmd.sayLoudOrPM(client, '^7Hello. IPDB v%s is offline.' % __version__)
    
    def add_notice(self, data, client, admin):
        status = self._buildEventInfo(self._EVENT_ADDNOTE, client, client.timeEdit)
        status.append([int(time.time()), data, admin.name, admin.guid])
        self._eventqueue.append(status)
                    
    def cmd_dbaddnote(self ,data , client, cmd=None):
        """\
        <player> <text>: Add/Update a notice on ipdb for given player
        """
        if not self._pluginEnabled or not self.isEnabled():
            client.message('^Sorry, IPDB is disabled right now')
            return False
                    
        input = self._adminPlugin.parseUserCmd(data)
        if input:
            # input[0] is the player id
            sclient = self._adminPlugin.findClientPrompt(input[0], client)
            if not sclient:
                return False
        else:
            client.message('^7Invalid data, try !help dbaddnote')
            return False

        if not len(input)==2:
            client.message('^7Missing data, try !help dbaddnote')
            return False
        
        self.add_notice(input[1], sclient, client)
        client.message('^7Done.')
            
    def cmd_dbdelnote(self ,data , client, cmd=None):
        """\
        <player>: Remove a notice on ipdb for given player
        """
        if not self._pluginEnabled or not self.isEnabled():
            client.message('^Sorry, IPDB is disabled right now')
            return False
                    
        input = self._adminPlugin.parseUserCmd(data)
        if input:
            # input[0] is the player id
            sclient = self._adminPlugin.findClientPrompt(input[0], client)
            if not sclient:
                return False
        else:
            client.message('^7Invalid data, try !help dbdelnote')
            return False
        
        status = self._buildEventInfo(self._EVENT_DELNOTE, sclient, sclient.timeEdit)
        self._eventqueue.append(status)
        client.message('^7Done.')

    def cmd_dbclearban(self ,data , client, cmd=None):
        """\
        <player>: Remove baninfo on ipdb for given player
        """
        if not self._pluginEnabled or not self.isEnabled():
            client.message('^Sorry, IPDB is disabled right now')
            return False
                    
        input = self._adminPlugin.parseUserCmd(data)
        if input:
            # input[0] is the player id
            sclient = self._adminPlugin.findClientPrompt(input[0], client)
            if not sclient:
                return False
        else:
            client.message('^7Invalid data, try !help dbclearban')
            return False
        
        status = self._buildEventInfo(self._EVENT_UNBAN, sclient, sclient.timeEdit)
        self._eventqueue.append(status)
        client.message('^7Done.')

    def cmd_iddbupdate(self ,data , client, cmd=None):
        """\
        Force a check for new ipdb version
        """
        self.checkNewVersion(True)
        if self._updated:
            self.notifyUpdate(client)
        else:
            client.message('^7IPDB is up to date.')

    def cmd_userlink(self, data, client, cmd=None):
        """\
        Register yourself in ipdb
        <username>: you ipdb username
        """
        if not self._pluginEnabled or not self.isEnabled():
            client.message('^Sorry, IPDB is disabled right now')
            return False
            
        input = self._adminPlugin.parseUserCmd(data)
        if not input or not input[0]:
            client.message('^7Invalid data, try !help userlink')
            return False
            
        username = input[0]
        data = self._buildClientInfo(client)
        client.message('^7Linking ... please wait.')
        try:
            socket.setdefaulttimeout(self._timeout)
            r = self._rpc_proxy.server.register(self._key, username, data)
            if r == 0:
                client.message('^7You have been linked succesfully to the username %s.' % username)
            elif r == 1:
                client.message('^7Please try again after some minutes.')
            elif r == 2:
                client.message('^7The username you entered is not valid.')
            elif r == 3:
                client.message('^7This player is already linked.')
            else:
                client.message('^7Unknown error. Ask your administrator to update ipdb [%d]' % r)
        except xmlrpclib.ProtocolError, protocolError:
            self.error(str(protocolError))
            client.message('^7An error occured while linking your user. Please try again later.')
        except xmlrpclib.Fault, applicationError:
            self.error(str(applicationError))
            client.message('^7An error occured while linking your user. Please try again later.')
        except socket.timeout, timeoutError:
            self.warning("Connection timed out")
            client.message('^7An error occured while linking your user. Please try again later.')
        except socket.error, socketError:
            self.error(str(socketError))
            client.message('^7An error occured while linking your user. Please try again later.')
        except Exception, e:
            self.error("General error. %s" % str(e))
            client.message('^7An error occured while linking your user. Please try again later.')
        finally:
            socket.setdefaulttimeout(None)
        
    def sanitize(self, data):
        return self.encodeEntities(self._color_re.sub('',data))
        
    def encodeEntities(self, data):
        #return data.replace("<", "\<").replace(">","\>")
        return data
        
    # --- REMOTE EVENT HANDLING --- #
    def processRemoteQueue(self):
        try:
            list = self.getRemoteQueue()
        except:
            list = []
        if len(list) > 0:
            self.debug('Received %d events. Processing' % len(list))
            for event in list:
                try:
                    self.debug(event)
                    if event[0] == self._EVENT_BAN:
                        self.processRemoteBan(event)
                    elif event[0] == self._EVENT_UNBAN:
                        self.processRemoteUnBan(event)
                    elif event[0] == self._EVENT_ADDNOTE:
                        self.processRemoteNotice(event)
                    elif event[0] == self._EVENT_DELNOTE:
                        self.processRemoteUnNotice(event)
                except Exception, e:
                    self.error(e)
        else:
            self.debug('No events received')
        self.remoteEventStatus()
            
    def processRemoteBan(self, event):
        m, ev, client_id, duration, reason, admin_id = event
        self.debug("Process ban %s" % client_id)
        if self._remotePermission & 1:
            sclient = self._adminPlugin.findClientPrompt("@%s" % client_id, None)
            if sclient:
                if admin_id == 0:
                    admin = None
                else:
                    admin = self._adminPlugin.findClientPrompt("@%s" % admin_id, None)
                
                if admin is None:
                    self.confirmRemoteEvent(ev, "Invalid admin @%s" % admin_id)
                    self.warning("Remote ban: admin @%s not found" % admin_id)
                    return
                    
                if duration > 0:
                    sclient.tempban(duration=duration, reason=reason, admin=admin, silent=True, data='Banned from IPDB')
                else:
                    sclient.ban(reason=reason, admin=admin, silent=True, data='Banned from IPDB')
                self.confirmRemoteEvent(ev)
            else:
                self.confirmRemoteEvent(ev, "Client @%s not found" % client_id)
                self.warning("Remote ban: client @%s not found" % client_id)
        else:
            self.confirmRemoteEvent(ev, "Not enough permission for remote ban")
            self.warning("Not enough permission for remote ban")

    def processRemoteUnBan(self, event):
        m, ev, client_id = event
        self.debug("Process unban %s" % client_id)
        if self._remotePermission & 2:
            sclient = self._adminPlugin.findClientPrompt("@%s" % client_id, None)
            if sclient:
                sclient.unban(silent=True)
                self.confirmRemoteEvent(ev)
            else:
                self.confirmRemoteEvent(ev, "Client @%s not found" % client_id)
                self.warning("Remote unban: client @%s not found" % client_id)
        else:
            self.confirmRemoteEvent(ev, "Not enough permission for remote unban")
            self.warning("Not enough permission for remote unban")
                        
    def processRemoteNotice(self, event):
        m, ev, pkey, client_id, reason, admin_id = event
        self.debug("Process notice %s" % client_id)
        if self._remotePermission & 4:
            sclient = self._adminPlugin.findClientPrompt("@%s" % client_id, None)
            if sclient:
                if admin_id == 0:
                    admin = None
                else:
                    admin = self._adminPlugin.findClientPrompt("@%s" % admin_id, None)

                if admin is None:
                    self.confirmRemoteEvent(ev, "Invalid admin @%s" % admin_id)
                    self.warning("Remote notice: admin @%s not found" % admin_id)
                    return
                                        
                p = ClientNotice()
                p.timeAdd = self.console.time()
                p.clientId = sclient.id
                if admin:
                    p.adminId = admin.id
                else:
                    p.adminId = 0
                p.reason = reason
                p.data = pkey
                p.save(self.console)
                self.confirmRemoteEvent(ev)
            else:
                self.confirmRemoteEvent(ev, "Client @%s not found" % client_id)
                self.warning("Remote notice: client @%s not found" % client_id)
        else:
            self.confirmRemoteEvent(ev, "Not enough permission for remote notice")
            self.warning("Not enough permission for remote notice")
          
    def processRemoteUnNotice(self, event):
        m, ev, pkey = event
        self.debug("Process unnotice %s" % ev)
        if self._remotePermission & 8:
            self.console.storage.query(QueryBuilder(self.console.storage.db).UpdateQuery( { 'inactive' : 1 }, 'penalties', { 'data' : pkey } ))
            self.confirmRemoteEvent(ev)
        else:
            self.confirmRemoteEvent(ev, 'Not enough permission for remote notice remove')
            self.warning("Not enough permission for remote notice remove")
                
    def confirmRemoteEvent(self, eventId, msg = ''):
        self.verbose("Queue event confirmation %s [%s]" % (eventId, msg))
        self._remotequeue.append([eventId, msg])
        
    def remoteEventStatus(self):
        self.debug("Check remote events status [%d]" % len(self._remotequeue))
        if len(self._remotequeue) == 0: return
        last = len(self._remotequeue)
        if last > self._maxOneTimeUpdate: last = self._maxOneTimeUpdate
        status = self._remotequeue[0:last]
        try:
            self.debug("Send remote events confirmation")
            socket.setdefaulttimeout(self._timeout * 2)
            self._rpc_proxy.server.confirmEvent(self._key, status)
            self._failureCount = 0
            del self._remotequeue[0:last]
        except xmlrpclib.ProtocolError, protocolError:
            self.error(str(protocolError))
            self.increaseFail()
            raise Exception()
        except xmlrpclib.Fault, applicationError:
            self.error(applicationError.faultString)
            self.increaseFail()
            raise Exception()
        except socket.timeout, timeoutError:
            self.warning("Connection timed out")
            raise Exception()
        except socket.error, socketError:
            self.error(str(socketError))
            self.increaseFail()
            raise Exception()
        except Exception, e:
            self.error("General error. %s" % str(e))
        finally:
            socket.setdefaulttimeout(None)
                
    def getRemoteQueue(self):
        list = []
        try:
            socket.setdefaulttimeout(self._timeout * 2)
            list = self._rpc_proxy.server.eventQueue(self._key)
            self._failureCount = 0
        except xmlrpclib.ProtocolError, protocolError:
            self.error(str(protocolError))
            self.increaseFail()
            raise Exception()
        except xmlrpclib.Fault, applicationError:
            self.error(applicationError.faultString)
            self.increaseFail()
            raise Exception()
        except socket.timeout, timeoutError:
            self.warning("Connection timed out")
            raise Exception()
        except socket.error, socketError:
            self.error(str(socketError))
            self.increaseFail()
            raise Exception()
        except Exception, e:
            self.error("General error. %s" % str(e))
        finally:
            socket.setdefaulttimeout(None)
        return list
                    
import urllib2, urllib
try:
    from b3.lib.elementtree import ElementTree
except:
    from xml.etree import ElementTree
from distutils import version
import shutil, os

class PluginUpdater(object):
    _update_url = 'http://update.ipdburt.com.ar/update.xml'
    _timeout = 10
    _currentVersion = None
    _path = None
    _parent = None
    
    def __init__(self, current, plugin):
        self._currentVersion = current
        self._parent = plugin
        self._path = self._getPath('@b3/extplugins')
        
    def verifiy(self, doUpdate = True):
        import socket
        original_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(self._timeout)
        errorMessage = None
        updated = False
        latestVersion = None
        try:
            self._parent.debug("Checking new version...")
            f = urllib2.urlopen(self._update_url)
            _xml = ElementTree.parse(f)
            latestVersion = _xml.getroot().find('version').text
            _lver = version.LooseVersion(latestVersion)
            _cver = version.LooseVersion(self._currentVersion)
            if _cver < _lver:
                if doUpdate:
                    self._doUpdate(list(_xml.getroot().find('files')))
                updated = True
        except IOError, e:
            if hasattr(e, 'reason'):
                errorMessage = "%s" % e.reason
            elif hasattr(e, 'code'):
                errorMessage = "error code: %s" % e.code
            else:
                errorMessage = "%s" % e
        except OSError, e:
            errorMessage = "%s" % e 
        except Exception, e:
            errorMessage = "%s" % e
        socket.setdefaulttimeout(original_timeout)
        if errorMessage:
            self._parent.warning(errorMessage)
        return (updated, latestVersion)
    
    def _getPath(self, path):
        if path[0:3] == '@b3':
            path = "%s/%s" % (b3.getB3Path(), path[3:])
        elif path[0:6] == '@conf/' or path[0:6] == '@conf\\':
            path = "%s/%s" % (b3.getConfPath(), path[5:])
        return os.path.normpath(os.path.expanduser(path))
            
    def _doUpdate(self, files):
        for elem in files:
            temp = self._getFile(elem.text, elem.attrib['hash'])
            if elem.attrib.has_key('dst'):
                dst = './%s' % elem.attrib['dst']
            else:
                dst = './'
            fname = os.path.join(self._path, dst, elem.attrib['name'])
            if elem.attrib.has_key('conf') and elem.attrib['conf'] and os.path.exists(fname):
                self._updateConfigFile(temp, fname)
            else:
                if os.path.exists(fname):
                    os.remove(fname)
                shutil.move(temp, fname)
            
    def _getFile(self, url, sum):
        d = urllib.urlretrieve(url)
        f = file(d[0], 'rb')
        s = hash(f.read()).hexdigest()
        f.close()
        if s == sum:
            return d[0]
        raise Exception("Checksums doesn't match")
    
    def _updateConfigFile(self, newFile, currentFile):
        _newConfig = ElementTree.parse(newFile)
        _currentConfig = ElementTree.parse(currentFile)
        
        for element in _newConfig.getroot().getchildren(): 
            self._processConfigElement(element, _currentConfig)
    
    def _processConfigElement(self, element, currentConfig):
        if currentConfig.find(element.tag):        
            # not implemented
            pass
                
if __name__ == '__main__':
    from b3.fake import fakeConsole
    from b3.fake import joe, simon, moderator, superadmin
    import time
    
    fakeConsole.setCvar('sv_hostname','IPDB Test Server')    
    
    p = Ipdb2Plugin(fakeConsole,'conf/ipdb.xml')
    p._url = 'http://166.40.231.124:8080/iddb-web/api/v4/xmlrpc'
    p._remoteInterval = 1
    p.onStartup()
    time.sleep(5)
    
    joe.connects(cid=1)
    simon.connects(cid=2)
    moderator.connects(cid=3)
    superadmin.connects(cid=4)
    time.sleep(5)
   
    moderator.says('!ipdb')
    time.sleep(2)
    superadmin.says('!ipdb')
    time.sleep(2)
    superadmin.says('!putgroup joe admin')
    
    #moderator.says('!link mod@sgmail.com.ar')
    #time.sleep(1)
    #superadmin.says('!link super@sgmail.com.ar')
    #time.sleep(1)
    #joe.says('!link joe@sgmail.com.ar')
