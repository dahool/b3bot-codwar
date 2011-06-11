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

__author__  = 'SGT'
__version__ = '1.1.15'

import b3, time, threading, xmlrpclib, re, thread
import b3.events
import b3.plugin
import b3.cron
import random, datetime
import socket

try:
    import hashlib
    hash = hashlib.sha1
except ImportError:
    import sha
    hash = sha.new
    
#--------------------------------------------------------------------------------------------------
class Ipdb2Plugin(b3.plugin.Plugin):
    _url = 'http://www.ipdburt.com.ar/xmlrpc2'

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
    
    _updated = False
    _notifyUpdateLevel = 80
    _autoUpdate = True
    _running = False
    _onlinePlayers = []
    _banqueue = []
    _updateCrontab = None
    _showBanAdmin = True
    
    _clientCache = {}
    
    _EVENT_CONNECT = "connect"
    _EVENT_DISCONNECT = "disconnect"
    _EVENT_UPDATE = "update"
    _EVENT_BAN = "banned"
    _EVENT_ADDNOTE = "addnote"
    _EVENT_DELNOTE = "delnote"
    _EVENT_UNBAN = "unbanned"
    
    _BAN_QUERY = "SELECT c.id as client_id, p.id as id, p.duration as duration, p.reason as reason, p.time_add as time_add, p.admin_id as admin_id "\
    "FROM penalties p INNER JOIN clients c ON p.client_id = c.id "\
    "WHERE (p.type='Ban' OR p.type='TempBan') AND (p.time_expire=-1 OR p.time_expire > %(now)d) "\
    "AND p.time_edit >= %(since)d AND p.inactive=0 AND keyword <> 'ipdb2'"
        
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
            self._adminPlugin.registerCommand(self, 'ipdb', 1, self.cmd_showqueue, None)
            self._adminPlugin.registerCommand(self, 'ipdbup', 80, self.cmd_update, None)
            
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
        rmin = random.randint(5,59)
        self._cronTab.append(b3.cron.PluginCronTab(self, self.update, minute='*/%s' % self._interval))
        self._cronTab.append(b3.cron.PluginCronTab(self, self.updateBanQueue, minute='*/30'))
        self._cronTab.append(b3.cron.PluginCronTab(self, self.validateOnlinePlayers, minute='*/10'))
        if self._banInfoInterval > 0:
            self._delta = datetime.timedelta(hours=self._banInfoInterval, minutes=15)
            self._cronTab.append(b3.cron.PluginCronTab(self, self.updateBanInfo, 0, rmin, '*/%s' % self._banInfoInterval))
        if self._banInfoDumpTime >= 0:
            self._cronTab.append(b3.cron.PluginCronTab(self, self.dumpBanInfo, 0, rmin, self._banInfoDumpTime))
        if self._updateCrontab:
            self.console.cron - self._updateCrontab

        self._updateCrontab = b3.cron.PluginCronTab(self, self.checkNewVersion, 0, rmin, '*/12')
        self.console.cron + self._updateCrontab

    def onLoadConfig(self):
        self._hostname = self._color_re.sub('',self.console.getCvar('sv_hostname').getString())
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
        
        if command_name == 'cmd_notice':
            self.handleAddNoticeCommand(data, client)
        elif command_name == 'cmd_unban':
            self.handleUnbanCommand(data, client)

    def handleUnbanCommand(self, data, client):
        # if we are handling the event, discard
        try:
            ev = b3.events.EVT_CLIENT_UNBAN
        except:
            try:
                cid, reason = self._adminPlugin.parseUserCmd(data)
                sclient = self._adminPlugin.findClientPrompt(cid, None)
                if sclient and sclient.numBans == 0:
                    self.onClientUnban(sclient)
            except:
                pass
            
    def handleAddNoticeCommand(self, data, client):
        # we have no way to know if the notice was actually added
        # get the last notice from the database
        try:
            cid, notice = self._adminPlugin.parseUserCmd(data)
            sclient = self._adminPlugin.findClientPrompt(cid, None)
            if sclient:
                penalty = self.console.storage.getClientLastPenalty(sclient, 'Notice')
                if penalty and penalty.adminId == client.id: # check if is the same admin :)
                    self.add_notice(penalty.reason, sclient, client)
        except:
            pass
        
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
    def _hash(self, text):
        return hash('%s%s' % (text, self._key)).hexdigest()
        
    def _buildEventInfo(self, event, client, timeEdit = None):
        self.verbose('Queued event %s for %s' % (event, client.name))
        guid = self._hash(client.guid)
        if not timeEdit:
            timeEdit = int(time.time())
        else:
            try:
                timeEdit = self._formatTime(timeEdit)
            except:
                timeEdit = int(time.time())
        info = [event, client.name, guid, client.id, client.ip, client.maxLevel, timeEdit]
        self.verbose(info)
        return info
          
    def _formatTime(self, tm):
        return int(time.mktime(time.localtime(tm)))
    
    def cleanEvents(self):
        '''clean connect events in case of disabled.
        '''
        tempList = self._eventqueue[:]
        tempClients = []
        self._eventqueue = []
        for event in tempList:
            if event[0] in (self._EVENT_CONNECT, self._EVENT_UPDATE):
                if not event[2] in tempClients:
                    self._eventqueue.append(event)
        if len(self._eventqueue) > 50:
            self._eventqueue = self._eventqueue[:50:-1]
           
    # =============================== UPDATE ===============================
    def send_update(self, list):
        try:
            socket.setdefaulttimeout(self._timeout)
            self._rpc_proxy.server.update(self._key, list)
            self._failureCount = 0
        except xmlrpclib.ProtocolError, protocolError:
            self.error(str(protocolError))
            self.increaseFail()
            raise Exception()
        except xmlrpclib.Fault, applicationError:
            self.error(str(applicationError))
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
        if penalty and penalty.duration < 1 or penalty.duration > 30: # no tempban less than 30 minutes
            if penalty.duration == -1 or penalty.duration == 0:
                pType = "pb"
            else:
                pType = "tb"

            admin_id = 0
            if self._showBanAdmin:
                if penalty.adminId and penalty.adminId > 0:
                    admin = self._adminPlugin.findClientPrompt('@%s' % str(penalty.adminId), None)
                    if admin:
                        admin_id = self._hash(admin.guid)
                
            baninfo = [pType, self._formatTime(penalty.timeAdd), penalty.duration, penalty.reason, admin_id]
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
        try:
            self.debug('Update server name')
            socket.setdefaulttimeout(self._timeout)
            self._rpc_proxy.server.updateName(self._key, self._hostname, __version__)
        except Exception, e:
            self.error("Error updating server name. %s" % str(e))
            if self.increaseFail():
                self.console.cron + b3.cron.OneTimeCronTab(self.updateName, '*/30')
        else:
            self.do_enable()
        socket.setdefaulttimeout(None)
        
    def update(self):
        self.bot('Update')
        if not self._running:
            self._running = True
            last = len(self._eventqueue)-1
            if last > 20: last = 20
            status = self._eventqueue[0:last]
            if len(status) > 0:
                self.debug("Updating")
                try:
                    self.send_update(status)
                except:
                    pass
                else:
                    del self._eventqueue[0:last]
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
            since = int(time.mktime((datetime.datetime.now() - self._delta).timetuple()))
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
                list.append(status)
            cursor.moveNext()
        
        if len(list) > 0:
            self.debug('Update ban info')
            if self._running:
                time.sleep(self._timeout)
            try:
                self._running = True
                self.send_update(list)
            except:
                pass
            else:
                cursor = self.console.storage.query("UPDATE penalties SET keyword = 'ipdb2' WHERE id IN (%s)" % ",".join(keys))
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
        status.append([data, self._hash(admin.guid)])
        self._eventqueue.append(status)
                    
    def cmd_dbaddnote(self ,data , client, cmd=None):
        """\
        <player> <text>: Add/Update a notice on ipdb for given player
        """
        input = self._adminPlugin.parseUserCmd(data)
        if input:
            # input[0] is the player id
            sclient = self._adminPlugin.findClientPrompt(input[0], client)
            if not sclient:
                return False
        else:
            client.message('^7Invalid data, try !help addnote')
            return False

        if not len(input)==2:
            client.message('^7Missing data, try !help addnote')
            return False
        
        self.add_notice(input[1], sclient, client)
        client.message('^7Done.')
            
    def cmd_dbdelnote(self ,data , client, cmd=None):
        """\
        <player>: Remove a notice on ipdb for given player
        """
        input = self._adminPlugin.parseUserCmd(data)
        if input:
            # input[0] is the player id
            sclient = self._adminPlugin.findClientPrompt(input[0], client)
            if not sclient:
                return False
        else:
            client.message('^7Invalid data, try !help delnote')
            return False
        
        status = self._buildEventInfo(self._EVENT_DELNOTE, sclient, sclient.timeEdit)
        self._eventqueue.append(status)
        client.message('^7Done.')

    def cmd_dbclearban(self ,data , client, cmd=None):
        """\
        <player>: Remove baninfo on ipdb for given player
        """
        input = self._adminPlugin.parseUserCmd(data)
        if input:
            # input[0] is the player id
            sclient = self._adminPlugin.findClientPrompt(input[0], client)
            if not sclient:
                return False
        else:
            client.message('^7Invalid data, try !help delnote')
            return False
        
        status = self._buildEventInfo(self._EVENT_UNBAN, sclient, sclient.timeEdit)
        self._eventqueue.append(status)
        client.message('^7Done.')

    def cmd_update(self ,data , client, cmd=None):
        """\
        Force a check for new ipdb version
        """
        self.checkNewVersion(True)
        if self._updated:
            self.notifyUpdate(client)
        else:
            client.message('^7IPDB is up to date.')
            
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
    p.onStartup()
    time.sleep(2)
    
    p.checkNewVersion()
    
    time.sleep(10)
    
    superadmin.connects(cid=10)
