from b3.functions import soundex, levenshteinDistance
import string
import os

def locateMap(maplist, mapname):
    data = mapname.strip()

    soundex1 = soundex(string.replace(string.replace(data, 'ut4_',''), 'ut_',''))

    match = []
    if data in maplist:
        match = [data]
    else:
        for m in maplist:
            s = soundex(string.replace(string.replace(m, 'ut4_',''), 'ut_',''))
            if s == soundex1:
               match.append(m)

    if len(match) == 0:
        # suggest closest spellings
        shortmaplist = []
        for m in maplist:
            if m.find(data) != -1:
                shortmaplist.append(m)
        if len(shortmaplist) > 0:
            shortmaplist.sort(key=lambda map: levenshteinDistance(data, string.replace(string.replace(map.strip(), 'ut4_',''), 'ut_','')))
            match = shortmaplist[:3]
        else:
            maplist.sort(key=lambda map: levenshteinDistance(data, string.replace(string.replace(map.strip(), 'ut4_',''), 'ut_','')))
            match = maplist[:3]
    
    if len(match) > 1:
        raise Exception('do you mean : %s' % string.join(match,', '))
    if len(match) == 1:
        mapname = match[0]
    else:
        raise Exception('^7cannot find any map like [^4%s^7].' % data)

    return mapname
  
def listCycleMaps(console):
    mapcycle = console.getCvar('g_mapcycle').getString()

    try:
        mapfile = console.game.fs_basepath + '/' + console.game.fs_game + '/' + mapcycle
        if not os.path.isfile(mapfile):
            mapfile = console.game.fs_homepath + '/' + console.game.fs_game + '/' + mapcycle
    except Exception,e:
      console.error(e)
      return None
      
    cyclelist = []
    mapstring = open(mapfile, 'r')
    maps = mapstring.read().strip('\n').split('\n')

    if maps:
        _settings = False
        for m in maps:
            m = m.strip()                
            if m == '}':
                _settings = False
                continue
            elif m == '{':
                _settings = True
            if not _settings:
                if m != '':
                    cyclelist.append(m)
    return cyclelist

def installedMap(console, mapname):
    maplist = installedMapList(console)
    return locateMap(maplist, mapname)
    
def installedMapList(console):
    if hasattr(console, 'installedMaps'):
        console.debug("getting installed maps")
        maplist = console.installedMaps()
    else:
        console.debug("using standard map list")
        maplist = console.getMaps()
    return maplist
            
def findMap(console, mapname):
    return locateMap(listCycleMaps(console), mapname)
