########################
#
# B3 Bitchslap Command
#
########################

##
# CHANGELOG
##

# 27-07-2008 v0.0.1 - Written for Decoy to bitchslap people, nuff said. Slap code modified from poweradminurt by xlr8or. - Pyranwolf.
# 28-07-2008 v0.0.2 - Added possibility to provide a number of slaps and extra check on syntax for !mslap
__author__ = 'HSO Clan Development http://www.hsoclan.co.uk'
__version__ = '0.0.2'

import b3, b3.plugin, b3.events, re

class UrtbslapPlugin(b3.plugin.Plugin):

    minlevel=0
    safeLevel=90
    _adminPlugin = None
    
    def onLoadConfig(self):
        try:
            self.minlevel = self.config.getint('settings', 'minlevel')    
        except:
            self.minlevel = 80
        try:
            self.safeLevel = self.config.getint('settings', 'safelevel')
        except:
            self.safeLevel = 90
            
    def onStartup(self):
        self._adminPlugin = self.console.getPlugin('admin')
        if self._adminPlugin:
            self._adminPlugin.registerCommand(self, 'mslap', self.minlevel, self.cmd_mslap, 'f')
            self._adminPlugin.registerCommand(self, 'bitchslap', self.minlevel, self.cmd_bitchslap, 'f')

    def cmd_mslap(self, data, client=None, cmd=None):
        """\
        <name> <number> - Slap a player for <number> times.
        """     
        input = self._adminPlugin.parseUserCmd(data)
        if not data:
            client.message('^7command is !mslap <playername or partialname> <number of slaps>')
            return False
        else:
            if  len([x for x in data if x.isspace()]) < 1:
                client.message('^7 correct syntax is !mslap <playername or part> <number of slaps>')
            else:
                input = data.split(' ',1)
                cname = input[0]
                creps = input[1]
                sclient = self._adminPlugin.findClientPrompt(cname, client)
                if not sclient: return False
                
                if sclient.maxLevel >= self.safeLevel and client.maxLevel < 90:
                    client.message('^7You don\'t have enought privileges to slap an Admin')
                    return False
                    
                self.console.write('say ^7Smackdown!')
                reps = int(creps)
                while reps > 0:
                    self.console.write('slap %s' % (sclient.cid))
                    reps-=1 
        return True 
        
    def cmd_bitchslap(self, data, client=None, cmd=None):
        """\
        <name> - Slap a player to death (use it wisely)
        """     
        input = self._adminPlugin.parseUserCmd(data)
        if input:
            sclient = self._adminPlugin.findClientPrompt(input[0], client)
            if not sclient: return False

            if sclient.maxLevel >= self.safeLevel and client.maxLevel < 80:
                client.message('^7You don\'t have enought privileges to slap an Admin')
                return False
                                    
            self.console.write('say ^7Smackdown to Death!')
            reps = 20
            while reps > 0:
                self.console.write('slap %s' % (sclient.cid))
                reps-=1
        else:
            client.message('^7Slap who???')
            return False
