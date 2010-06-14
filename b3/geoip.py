# 02/01/2010 - SGT - Add json import for python 2.6 compatibility
from urllib import urlopen, quote
try:   
  import json  
except ImportError:   
  import simplejson as json 

GEOIP_LOOKUP_URL = 'http://ipinfodb.com/ip_query.php?ip=%s&output=json'
#GEOIP_LOOKUP_URL = 'http://ipinfodb.com/ip_query_country.php?ip=%s&output=json'

def geo_ip_lookup(ip_address):
  """
  Look up the geo information based on the IP address passed in
  """
  lookup_url = GEOIP_LOOKUP_URL % ip_address
  json_response = json.loads(urlopen(lookup_url).read())

  return {
      'country_code': json_response['CountryCode'],
      'country_name': json_response['CountryName'],
      'city': json_response['City'],
      'region': json_response['RegionName'],
      'longitude': json_response['Longitude'],
      'latitude': json_response['Latitude']
  }
