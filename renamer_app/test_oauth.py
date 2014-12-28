import requests
import json
import os

from requests_oauthlib import OAuth1

# HIDE
from private_credentials import API_KEY, API_KEY_SECRET

OAUTH_ORIGIN      = 'https://secure.smugmug.com'
REQUEST_TOKEN_URL = OAUTH_ORIGIN + '/services/oauth/1.0a/getRequestToken'
ACCESS_TOKEN_URL  = OAUTH_ORIGIN + '/services/oauth/1.0a/getAccessToken'
AUTHORIZE_URL     = OAUTH_ORIGIN + '/services/oauth/1.0a/authorize'

API_ORIGIN = 'http://api.smugmug.com'
BASE_URL = API_ORIGIN + '/api/v2'

TOKEN_FILE = 'access_token.json'

# Check if we already have access token and secret
if not os.path.exists(TOKEN_FILE):
   # Get the anonymous oauth_token and secret
   oauth = OAuth1(API_KEY, client_secret=API_KEY_SECRET, callback_uri='oob')
   r = requests.post(url=REQUEST_TOKEN_URL, auth=oauth)
   print "Content: ", r.content

   from urlparse import parse_qs
   credentials = parse_qs(r.content)
   resource_owner_key    = credentials.get('oauth_token')[0]
   resource_owner_secret = credentials.get('oauth_token_secret')[0]

   print "owner key: ", resource_owner_key
   print "owner secret: ", resource_owner_secret

   # Redirect the user to /authorize and get the callback
   authorize_url = AUTHORIZE_URL + '?oauth_token=' + resource_owner_key + '&oauth_consumer_key=' + API_KEY
   authorize_url += "&Access=Full&Permissions=Modify"

   print 'Please go here and authorize,', authorize_url
   verifier = raw_input('Please enter the six-digit PIN code: ')

   # Get the final oauth_token and secret
   oauth = OAuth1(API_KEY, client_secret=API_KEY_SECRET,
                           resource_owner_key=resource_owner_key,
                           resource_owner_secret=resource_owner_secret,
                           verifier=verifier)
   r = requests.post(url=ACCESS_TOKEN_URL, auth=oauth)
   print "Access content", r.content
   # OUT: 'oauth_token=2f227cce369edad1ff3880bb4dab84f2&oauth_token_secret=10e284c0ce48c2c2c6ce4f58fca358d6ff495a55&oauth_callback_confirmed=true'

   credentials         = parse_qs(r.content)
   access_token        = credentials.get('oauth_token')[0]
   access_token_secret = credentials.get('oauth_token_secret')[0]

   with open(TOKEN_FILE, 'w') as f:
      json.dump({'access_token': access_token,
                 'access_token_secret': access_token_secret}, f)

else:
   with open(TOKEN_FILE, 'r') as f:
      tokens = json.load(f)
      access_token        = tokens.get('access_token')
      access_token_secret = tokens.get('access_token_secret')

# TEST CALLS to API
# Make authenticated calls to the API
oauth = OAuth1(API_KEY, client_secret=API_KEY_SECRET,
                        resource_owner_key=access_token,
                        resource_owner_secret=access_token_secret)

url = BASE_URL + '!authuser'
r = requests.get(url=url, auth=oauth, headers={"Accept": 'application/json'})
#print r.content

print "Authuser"
print json.dumps(r.json(), indent = 2)

url = API_ORIGIN + '/api/v2/user/cmac'
r = requests.get(url=url, auth=oauth, headers={"Accept": 'application/json'})

print "cmac user"
print json.dumps(r.json(), indent = 2)

