import json
import os
import requests

from urlparse import parse_qs

from requests_oauthlib import OAuth1

# HIDE
from private_credentials import API_KEY, API_KEY_SECRET

OAUTH_ORIGIN      = 'https://secure.smugmug.com'
REQUEST_TOKEN_URL = OAUTH_ORIGIN + '/services/oauth/1.0a/getRequestToken'
ACCESS_TOKEN_URL  = OAUTH_ORIGIN + '/services/oauth/1.0a/getAccessToken'
AUTHORIZE_URL     = OAUTH_ORIGIN + '/services/oauth/1.0a/authorize'

API_ORIGIN = 'https://api.smugmug.com'
BASE_URL = API_ORIGIN + '/api/v2'

TOKEN_FILE = 'access_token.json'

# Check if we already have access token and secret
if not os.path.exists(TOKEN_FILE):
   # 1) Obtain Request token
   oauth = OAuth1(API_KEY, client_secret=API_KEY_SECRET, callback_uri='oob')
   r = requests.post(url=REQUEST_TOKEN_URL, auth=oauth)
   credentials = parse_qs(r.content)
   resource_owner_key    = credentials.get('oauth_token')[0]
   resource_owner_secret = credentials.get('oauth_token_secret')[0]

   # 2) Obtain authorization for the user to access resources
   # Redirect the user to /authorize and get the callback
   authorize_url = AUTHORIZE_URL + '?oauth_token=' + resource_owner_key + '&oauth_consumer_key=' + API_KEY
   authorize_url += "&Access=Full&Permissions=Modify"

   print 'Please go here and authorize,', authorize_url
   verifier = raw_input('Please enter the six-digit PIN code: ')

   # 3) Obtain final access token
   oauth = OAuth1(API_KEY, client_secret=API_KEY_SECRET,
                           resource_owner_key=resource_owner_key,
                           resource_owner_secret=resource_owner_secret,
                           verifier=verifier)
   r = requests.post(url=ACCESS_TOKEN_URL, auth=oauth)

   credentials         = parse_qs(r.content)
   access_token        = credentials.get('oauth_token')[0]
   access_token_secret = credentials.get('oauth_token_secret')[0]

   # Store access token so we can use it later
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
                        resource_owner_secret=access_token_secret,
                        signature_type='auth_header')

# Get authuser details
url = BASE_URL + '!authuser'
r = requests.get(url=url, auth=oauth, headers={"Accept": 'application/json'})
print "Authuser"
print json.dumps(r.json(), indent = 2)

# get known user details
url = API_ORIGIN + '/api/v2/user/cmac'
r = requests.get(url=url, auth=oauth, headers={"Accept": 'application/json'})
print "cmac user"
print json.dumps(r.json(), indent = 2)

