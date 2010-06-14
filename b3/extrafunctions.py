# Copyright (C) 2010 Sergio Gabriel Teves
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
# CHANGELOG
# 2010-02-05
# Initial version

# simple quick sort implementation.
def partition(obj, list, start, end):
    pivot = list[end]
    bottom = start-1 
    top = end
    done = 0
    if not pivot.isvar(obj,'last_score'):
        pivot.setvar(obj,'last_score', 0)    
    while not done:
        while not done:
            bottom = bottom+1
            if bottom == top:
                done = 1
                break
            if not list[bottom].isvar(obj,'last_score'):
                list[bottom].setvar(obj,'last_score', 0)
            if list[bottom].var(obj,'last_score').value > pivot.var(obj,'last_score').value:
                list[top] = list[bottom]
                break
        while not done:
            top = top-1
            if top == bottom:
                done = 1
                break
            if not list[top].isvar(obj,'last_score'):
                list[top].setvar(obj,'last_score', 0)                
            if list[top].var(obj,'last_score').value < pivot.var(obj,'last_score').value:
                list[bottom] = list[top]
                break
    list[top] = pivot
    return top

def quicksort(obj,list, start, end):
    if start < end:
        split = partition(obj,list, start, end)
        quicksort(obj,list, start, split-1)
        quicksort(obj,list, split+1, end)
    else:
        return
        
class ShuffleMaster(object):
    
    def __init__(self, console):
        self.console = console
        
    def compute_players(self):
        clients = self.console.clients.getList()  
        scoreList = self.console.getPlayerScores()         
        # add scores to players
        for c in clients:
            c.setvar(self,'last_score', scoreList[c.cid])
            
    def perform(self):
        self.console.debug("performing shuffle")
        # get players list again (in case someone disconnected)
        clients = self.console.clients.getList()  
        # now sort by score
        quicksort(self,clients, 0, len(clients)-1)
        # build the teams
        team = 'blue'
        for c in clients:
            self.console.debug("%s with %s points goes to team %s" % (c.name,c.var(self,'last_score').value,team))
            self.console.write('forceteam %s %s' % (c.cid,team))
            if team == 'blue': team = 'red'
            else: team = 'blue'
        self.console.debug("shuffle completed")
