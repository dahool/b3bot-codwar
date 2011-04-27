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

__author__  = 'SGT'
__version__ = '1.1.0'

import b3, time, thread, threading, xmlrpclib, re
import b3.events
import b3.plugin
import b3.cron
from b3.functions import minutesStr
import random, datetime

try:
    import hashlib
    hash = hashlib.sha1
except ImportError:
    import sha
    hash = sha.new
    
#--------------------------------------------------------------------------------------------------
class Ipdb2Plugin(b3.plugin.Plugin):
    _url = 'https://ipdburt.appspot.com/xmlrpc2'
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
    _skip = 100
    _banqueue = []
    
    _EVENT_CONNECT = "connect"
    _EVENT_DISCONNECT = "disconnect"
    _EVENT_UPDATE = "update"
    _EVENT_BAN = "banned"
    _EVENT_ADDNOTE = "addnote"
    _EVENT_DELNOTE = "delnote"
    _EVENT_UNBAN = "unbanned"
    
    _BAN_QUERY = "SELECT c.id as client_id, p.id as id, p.duration as duration, p.reason as reason, p.time_add as time_add "\
    "FROM penalties p INNER JOIN clients c ON p.client_id = c.id "\
    "WHERE (p.type='Ban' OR p.type='TempBan') AND (p.time_expire=-1 OR p.time_expire > %(now)d) "\
    "AND p.time_edit >= %(since)d AND p.inactive=0 AND keyword <> 'ipdb'"
        
    _ALL_C_QUERY = "SELECT id, guid, name, ip, time_edit FROM clients WHERE auto_login = 1 and time_edit BETWEEN %(fromdate)d AND %(todate)d LIMIT 30"
    
    def onStartup(self):
        self._rpc_proxy = xmlrpclib.ServerProxy(self._url)
        
        self._eventqueue = []
        self._banqueue = []
        self._onlinePlayers = []
        
        self.registerEvent(b3.events.EVT_CLIENT_AUTH)
        self.registerEvent(b3.events.EVT_CLIENT_DISCONNECT)
        self.registerEvent(b3.events.EVT_CLIENT_NAME_CHANGE)
        self.registerEvent(b3.events.EVT_CLIENT_BAN)
        self.registerEvent(b3.events.EVT_CLIENT_BAN_TEMP)
        
        try:
            self.registerEvent(b3.events.EVT_CLIENT_UNBAN)
        except:
            self.warn('Unban event not available')
        
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
        self._cronTab.append(b3.cron.PluginCronTab(self, self.validateOnlinePlayers, minute='*/30'))
        if self._banInfoInterval > 0:
            self._delta = datetime.timedelta(hours=self._banInfoInterval, minutes=15)
            self._cronTab.append(b3.cron.PluginCronTab(self, self.updateBanInfo, 0, rmin, '*/%s' % self._banInfoInterval, '*', '*', '*'))
        if self._banInfoDumpTime >= 0:
            self._cronTab.append(b3.cron.PluginCronTab(self, self.dumpBanInfo, 0, rmin, self._banInfoDumpTime, '*', '*', '*'))
        if self._autoUpdate:
            self._cronTab.append(b3.cron.PluginCronTab(self, self.checkNewVersion, 0, rmin, '*/12', '*', '*', '*'))
        
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
            self._skip = self.config.getboolean('settings', 'skip')
        except:
            pass
            
    def onEvent(self, event):
        if event.type == b3.events.EVT_CLIENT_AUTH:
            b = threading.Timer(5, self.onClientConnect, (event.client,))
            b.start()
        elif event.type == b3.events.EVT_CLIENT_NAME_CHANGE:
            self.onClientUpdate(event.client)
        elif event.type == b3.events.EVT_CLIENT_DISCONNECT:
            self.onClientDisconnect(event.data)
        elif event.type == b3.events.EVT_CLIENT_BAN or event.type == b3.events.EVT_CLIENT_BAN_TEMP:
            self.onClientBanned(event.client)
        else:
            try:
                if event.type == b3.events.EVT_CLIENT_UNBAN:
                    self.onClientUnban(event.client)
            except:
                pass
                

    def _hash(self, text):
        return hash('%s%s' % (text, self._key)).hexdigest()
        
    def _buildEventInfo(self, event, client, timeEdit = None):
        guid = self._hash(client.guid)
        if not timeEdit:
            timeEdit = datetime.datetime.now()
        return [event, client.name, guid, client.id, client.ip, client.maxLevel, timeEdit]
          
    def validateOnlinePlayers(self):
        clients = self.console.clients.getList()
        for client in self._onlinePlayers:
            if client not in clients:
                self._eventqueue.append(self._buildEventInfo(self._EVENT_DISCONNECT, client))
        
    def onClientConnect(self, client):
        if not client or \
            not client.id or \
            client.cid == None or \
            client.pbid == 'WORLD' or \
            not client.connected:
            return
    
        self._onlinePlayers.append(client)
        
        if client.maxLevel < self._skip:
            self._eventqueue.append(self._buildEventInfo(self._EVENT_CONNECT, client))
        
        if self._updated:
            if client.maxLevel >= self._notifyUpdateLevel:
                if not client.var(self, 'ipdb_warn') or not client.var(self, 'ipdb_warn').value:
                    b = threading.Timer(30, self.notifyUpdate, (client,))
                    b.start()                
        
    def onClientBanned(self, client):
        self._banqueue.append(client)
            
    def onClientDisconnect(self, cid):
        client = self.console.clients.getByCID(cid)

        if client and client.maxLevel < self._skip:
            self._eventqueue.append(self._buildEventInfo(self._EVENT_DISCONNECT, client))
            
        try:
            if client in self._onlinePlayers:            
                self._onlinePlayers.remove(client)
        except Exception, e:
            self.error(e)

    def onClientUpdate(self, client):
        if client.maxLevel < self._skip:
            self._eventqueue.append(self._buildEventInfo(self._EVENT_UPDATE, client))

    def onClientUnban(self, client):
        timeEdit = datetime.datetime.fromtimestamp(client.timeEdit)
        self._eventqueue.append(self._buildEventInfo(self._EVENT_UNBAN, client, timeEdit))
            
    def updateBanQueue(self):
        while len(self._banqueue) > 0:
            client = self._banqueue.pop()
            lastBan = client.lastBan
            if lastBan:
                timeAdd = datetime.datetime.fromtimestamp(lastBan.timeAdd)
                if lastBan.duration == -1 or lastBan.duration == 0:
                    reason = 'Permanent banned since %s. Reason: %s' % (timeAdd.strftime("%d/%m/%Y"), lastBan.reason)
                else:
                    reason = 'Temp banned since %s for %s. Reason: %s' % (timeAdd.strftime("%d/%m/%Y"), minutesStr(lastBan.duration), lastBan.reason)
                timeEdit = datetime.datetime.fromtimestamp(client.timeEdit)
                status = self._buildEventInfo(self._EVENT_BAN, client, timeEdit)
                status.append(reason)
                self._eventqueue.append(status)
                                            
    def notifyUpdate(self, client):
        client.message('^7A new version of ^5IPDB ^7has been installed. Please restart the bot.')
        client.setvar(self, 'ipdb_warn', True)        

    def updateName(self):
        try:
            self.debug('Update server name')
            self._rpc_proxy.server.updateName(self._key, self._hostname, __version__)
        except Exception, e:
            self.error("Error updating server name. %s" % str(e))
            if self.increaseFail():
                self.console.cron + b3.cron.OneTimeCronTab(self.updateName, '*/30')
        else:
            self.enable()
            
    def update(self):
        if not self._running:
            self._running = True
            last = len(self._eventqueue)-1
            status = self._eventqueue[0:last]
            try:
                if len(status) > 0:
                    self.debug("Updating")
                    self._rpc_proxy.server.update(self._key, status)
                    del self._eventqueue[0:last]
            except Exception, e:
                self.error("Error updating ipdb. %s" % str(e))
                self.increaseFail()
            finally:
                self._running = False
        else:
            self.debug("Already running")
                    
    def enable(self):
        self._failureCount = 0
        self._enabled = True
        for ct in self._cronTab:
            self.console.cron + ct
            
    def disable(self):
        self._enabled = False
        for ct in self._cronTab:
            self.console.cron - ct
        
    def increaseFail(self):
        self._failureCount += 1
        if self._failureCount >= self._failureMax:
            self.disable()
            next = (datetime.datetime.now() + datetime.timedelta(hours=4)).hour
            self.console.cron + b3.cron.OneTimeCronTab(self.updateName, second=0, minute=0, hour=next)
            self._failureCount = 0
            return False
        return True
        
    def updateBanInfo(self, sendAll = False):
        self.debug('Collect ban info')
        now = int(time.time())
        if sendAll:
            since = 1262314800
            q = self._BAN_QUERY + " LIMIT 30"
        else:
            since = int(time.mktime((datetime.datetime.now() - self._delta).timetuple()))
            q = self._BAN_QUERY
        cursor = self.console.storage.query(q % {'now': now,
                                                'since': since})
                                                                  
        list = []
        keys = []
        while not cursor.EOF:
            r = cursor.getRow()
            client = self.console.clients.getByDB("@%s" % r['client_id'])
            if client:
                keys.append(str(r['id']))
                timeAdd = datetime.datetime.fromtimestamp(r['time_add'])
                if r['duration'] == -1 or r['duration'] == 0:
                    reason = 'Permanent banned since %s. Reason: %s' % (timeAdd.strftime("%d/%m/%Y"), r['reason'])
                else:
                    reason = 'Temp banned since %s for %s. Reason: %s' % (timeAdd.strftime("%d/%m/%Y"), minutesStr(r['duration']), r['reason'])
                timeEdit = datetime.datetime.fromtimestamp(client.timeEdit)
                status = self._buildEventInfo(self._EVENT_BAN, client, timeEdit)
                status.append(reason)
                list.append(status)
            cursor.moveNext()
        
        if len(list) > 0:
            self.debug('Update ban info')
            try:
                self._rpc_proxy.server.update(self._key, list)
            except Exception, e:
                self.error("Error updating ipdb. %s" % str(e))
                self.increaseFail()
            else:
                cursor = self.console.storage.query("UPDATE penalties SET keyword = 'ipdb' WHERE id IN (%s)" % ",".join(keys))
        else:
            self.debug('No ban info to send')
                
    def dumpBanInfo(self):
        self.debug('Collect all ban info')
        self.updateBanInfo(True)

    def checkNewVersion(self):
        p = PluginUpdater(__version__, self)
        self._updated = p.verifiy()

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
        
        timeEdit = datetime.datetime.fromtimestamp(sclient.timeEdit)
        status = self._buildEventInfo(self._EVENT_ADDNOTE, sclient, timeEdit)
        status.append(input[1])
        self._eventqueue.append(status)
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
        
        timeEdit = datetime.datetime.fromtimestamp(sclient.timeEdit)
        status = self._buildEventInfo(self._EVENT_DELNOTE, sclient, timeEdit)
        self._eventqueue.append(status)
        client.message('^7Done.')

    def cmd_dbclearban(self ,data , client, cmd=None):
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
        
        timeEdit = datetime.datetime.fromtimestamp(sclient.timeEdit)
        status = self._buildEventInfo(self._EVENT_UNBAN, sclient, timeEdit)
        self._eventqueue.append(status)
        client.message('^7Done.')
                                
import urllib2, urllib
try:
    from b3.lib.elementtree import ElementTree
except:
    from xml.etree import ElementTree
from distutils import version
import shutil, os

class PluginUpdater(object):
    _update_url = 'http://update.ipdburt.com.ar/update.xml'
    _timeout = 5
    _currentVersion = None
    _path = None
    _parent = None
    
    def __init__(self, current, plugin):
        self._currentVersion = current
        #self._path = os.path.normpath(os.path.abspath(os.path.dirname(__file__)))
        self._path = os.getcwd()
        self._parent = plugin
        
    def verifiy(self):
        import socket
        original_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(self._timeout)
        errorMessage = None
        updated = False
        try:
            self._parent.debug("Checking new version...")
            f = urllib2.urlopen(self._update_url)
            _xml = ElementTree.parse(f)
            latestVersion = _xml.getroot().find('version').text
            _lver = version.LooseVersion(latestVersion)
            _cver = version.LooseVersion(self._currentVersion)
            if _cver < _lver:
                self._parent.bot("New version available")
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
        finally:
            socket.setdefaulttimeout(original_timeout)
        if errorMessage:
            self._parent.warning(errorMessage)
        return updated
    
    def _doUpdate(self, files):
        for elem in files:
            temp = self._getFile(elem.text, elem.attrib['hash'])
            fname = os.path.join(self._path,elem.attrib['dst'], elem.attrib['name'])
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
