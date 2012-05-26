# 02/01/2010 - SGT - Add json import for python 2.6 compatibility
# 05/10/2010 - SGT - Add support for memcache
# 11/15/2010 - SGT - Add key as required for new ipinfodb API implementation
# 03/04/2012 - SGT - Add support for local dat file (requires pygeoip by maxmind)

from urllib import urlopen, quote
import pickle
try:   
    import json  
except ImportError:   
    try:
        import simplejson as json
    except ImportError:
        from b3 import xjson as json
try:
    import pygeoip
    from pygeoip import GeoIPError
except Exception, e:
    print e
try:
    import memcache # package   python-memcached
except ImportError:
    cache = False
else:
    cache = True

# REPLACE API_KEY WITH YOU KEY REGISTERING AT ipinfodb.com (YOU ARE FREE TO USE THE PROVIDED ONE THOUGH)
API_KEY = 'e664d347b9b5f0b506a599c73e2d9b76e3feea71a043abfb6a79eda09406e91f'
# TO ENABLE MEMCACHE SUPPORT INSTALL python-memcached AND REPLACE MEMCACHE_HOST WITH YOUR MEMCACHE HOST
# FOR EXAMPLE: MEMCACHE_HOST = '127.0.0.1:11211'
MEMCACHE_HOST = None
GEOIP_LOOKUP_URL = 'http://api.ipinfodb.com/v3/ip-city/?key=%(key)s&ip=%(ip)s&format=json'
GEOIP_DAT = None
DEBUG = False
geocity = None
CACHE_EXPIRE = 43200 # IN SECONDS

if GEOIP_DAT:
    try:
        geocity = pygeoip.GeoIP(GEOIP_DAT,pygeoip.MEMORY_CACHE)
    except Exception, e:
        print e
    
def debug(msg):
    if DEBUG:
        print msg

def geo_ip_lookup(ip_address):
    """
    Look up the geo information based on the IP address passed in
    """
    
    json_response = None
    value = None

    if cache and MEMCACHE_HOST:
        debug('Try cache')
        # try to locate the data in the cache first
        mc = memcache.Client([MEMCACHE_HOST], debug=0)
        key = "GIP_%s" % ip_address
        obj = mc.get(key)
        if obj:
            json_response = pickle.loads(obj)
            debug('Found in cache')
        
    if not json_response:
        if geocity:
            debug('Try Local DAT')
            try:
                value = geocity.record_by_addr(ip_address)
            except:
                return None
            debug(value)
            if value:
                json_response = {}
                if value.has_key('city'):
                    json_response['cityName'] = value['city']
                else:
                    json_response['cityName'] = ''
                json_response['countryCode'] = value['country_code']
                json_response['countryName'] = value['country_name']
                json_response['regionName'] = value['region_name']
                json_response['latitude'] = value['latitude']
                json_response['longitude'] = value['longitude']
        if not geocity or not value:
            lookup_url = GEOIP_LOOKUP_URL % {'key': API_KEY, 'ip': ip_address}
            try:
                debug('Try Service')
                json_response = json.loads(urlopen(lookup_url).read())
            except:
                return None
        
        if cache and MEMCACHE_HOST:
            key = "GIP_%s" % ip_address
            mc.set(key, pickle.dumps(json_response), CACHE_EXPIRE)
        
    return {
      'country_code': json_response['countryCode'],
      'country_name': json_response['countryName'].title(),
      'city': json_response['cityName'].title(),
      'region': json_response['regionName'].title(),
      'longitude': json_response['longitude'],
      'latitude': json_response['latitude']
    }

if __name__ == '__main__':
    DEBUG=True
    print geo_ip_lookup('74.125.67.103')
    # this time it should take it from cache
    print geo_ip_lookup('174.125.67.103')
