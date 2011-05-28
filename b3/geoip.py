# 02/01/2010 - SGT - Add json import for python 2.6 compatibility
# 05/10/2010 - SGT - Add support for memcache
# 11/15/2010 - SGT - Add key as required for new ipinfodb API implementation
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
GEOIP_LOOKUP_URL = 'http://api.ipinfodb.com/v2/ip_query.php?key=%(key)s&ip=%(ip)s&timezone=false&output=json'
#GEOIP_LOOKUP_URL = 'http://ipinfodb.com/ip_query.php?ip=%s&output=json'
#GEOIP_LOOKUP_URL = 'http://ipinfodb.com/ip_query_country.php?ip=%s&output=json'
DEBUG = False

def debug(msg):
    if DEBUG:
        print msg

def geo_ip_lookup(ip_address):
    """
    Look up the geo information based on the IP address passed in
    """
    
    json_response = None

    if cache and MEMCACHE_HOST:
	debug('Try cache')
        # try to locate the data in the cache first
        mc = memcache.Client([MEMCACHE_HOST], debug=0)
        key = "IP_%s" % ip_address
        obj = mc.get(key)
        if obj:
            json_response = pickle.loads(obj)
	    debug('Found in cache')
        
    if not json_response:
        lookup_url = GEOIP_LOOKUP_URL % {'key': API_KEY, 'ip': ip_address}

        try:
	    debug('Try Service')
            json_response = json.loads(urlopen(lookup_url).read())
        except:
            return None
      
        if cache and MEMCACHE_HOST:
            key = "IP_%s" % ip_address
            mc.set(key, pickle.dumps(json_response))
        
    return {
      'country_code': json_response['CountryCode'],
      'country_name': json_response['CountryName'],
      'city': json_response['City'],
      'region': json_response['RegionName'],
      'longitude': json_response['Longitude'],
      'latitude': json_response['Latitude']
    }


if __name__ == '__main__':
    DEBUG=True
    print geo_ip_lookup('74.125.67.103')
    # this time it should take it from cache
    print geo_ip_lookup('74.125.67.103')
