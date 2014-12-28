import argparse
import dateutil.parser
import json
import os
import re
import requests

from urlparse import parse_qs
from requests_oauthlib import OAuth1

from private_credentials import API_KEY, API_KEY_SECRET

SM_API_ORIGIN = 'https://api.smugmug.com'
SM_BASE_URL   = SM_API_ORIGIN + '/api/v2'


def main():
   args = parseOptions()

   smugmug_auth = SmOAuth(API_KEY, API_KEY_SECRET)
   smugmug_auth.authenticate()

   s = smugmug_auth.getSession()

   # 1) Get the user logged in and ready to go
   r = s.get(smUrl("/api/v2!authuser"))
   r_obj = r.json()
   #printObj(r_obj)
   user_obj  = r_obj['Response']['User']
   user_uris = user_obj['Uris']
   print "First Attempt:"
   print "Authuser: ", user_obj['NickName']
   print "   ResponseLevel: ", user_obj['ResponseLevel']

   # Check if we have a password locking us out
   # NOTE: It appears that if the user account has a password we have
   #       to log in with a post to proceed to get more details.
   #       Not sure where this state is being stored (cookie?)
   if user_uris.has_key('UnlockUser'):
      print "Unlocking user... ",
      if args.password is None:
         raise AppError("password required")

      unlock_url = user_uris['UnlockUser']['Uri']
      r = s.post(smUrl(unlock_url), data = json.dumps({'Password': args.password}))
      if r.status_code == 200:
         print " unlocked."
      else:
         raise AppError("Unlocking user failed")

   # Try getting user details again (now that should be logged in)
   r = s.get(smUrl("/api/v2!authuser"))
   r_obj = r.json()
   user_obj  = r_obj['Response']['User']
   user_uris = user_obj['Uris']
   print "Authuser: ", user_obj['Name']
   print "   ResponseLevel: ", user_obj['ResponseLevel']

   # Loop through all recent images
   # - Look for images that need filename setup with date
   # - If we have a date value to use, then set it
   page_count_size = 3
   cull_results    = True

   assert user_uris.has_key('UserRecentImages'), "Can't find recent image URI"

   recent_images_uri = user_uris['UserRecentImages']['Uri']
   expand_params = {'_expand'      : 'ImageMetadata',
                    '_expandmethod': 'inline'}


   next_url = recent_images_uri + "?count=%s" % page_count_size

   if cull_results:
      # Limit returned data
      # note: have to put filterui in here because it ends up in the "NextUrl"
      # and if we don't do this way we end up adding it twice.
      next_url += "&_filteruri=ImageMetadata" \
               + "&_filter=Uri,Title,WebUri,DateTimeCreated,FileName,IsVideo"
   finished = False

   def is_already_date_named(fnameStr):
      return re.match('^\d{4,4}\-\D{3,3}',fnameStr) != None

   while not finished:
      r = s.get(smUrl(next_url), params = expand_params)
      r_obj = r.json()
      #printObj(r_obj)

      next_url = r_obj['Response']['Pages']['NextPage']
      last_url = r_obj['Response']['Pages']['LastPage']
      cur_url  = r_obj['Response']['Uri']

      total_items = r_obj['Response']['Pages']['Total']
      cur_start   = r_obj['Response']['Pages']['Start']

      if cur_url == last_url:
         finished = True

      image_objs = r_obj['Response']['Image']
      for image_obj in image_objs:
         metadata     = image_obj['Uris']['ImageMetadata']['ImageMetadata']
         title        = image_obj['Title']
         uri          = image_obj['Uri']
         weburi       = image_obj['WebUri']
         #is_video     = image_obj['IsVideo']
         if not metadata.has_key('DateTimeCreated'):
            print "WARNING: No DateTimeCreated for [%s]" % weburi
            continue

         date_created = metadata['DateTimeCreated']
         filename     = image_obj['FileName']
         #image_date   = image_obj['Date']
         #last_update  = image_obj['LastUpdated']
         #parsed_image_date = dateutil.parser.parse(image_date)
         #parsed_updated   = dateutil.parser.parse(last_update)

         parsed_created = dateutil.parser.parse(date_created.replace(':', ' ', 2))
         file_prefix    = parsed_created.strftime('%Y-%b-%d-%H:%M')

         if not is_already_date_named(filename):
            new_fname = "%s_%s" % (file_prefix, filename)
            print "  renaming: '%s' [%s] --> [%s] (%s)" % (title, filename,
                                                           new_fname, weburi)
            if not args.dry_run:
               r = s.patch(smUrl(uri), data = json.dumps({'FileName': new_fname}))
               printObj(r.json())
               if 200 != r.status_code:
                  print "Failure to patch:"
                  printObj(r.json())
                  raise AppError("Failed patch")
         else:
            print "  skipping: '%s' [%s]" % (title, filename)

      # Output the current progress
      pct_done = float(cur_start)/total_items
      prefix = "[%.1f] %s/%s" % (pct_done * 100.0, cur_start, total_items)
      print prefix



def parseOptions():
   parser = argparse.ArgumentParser(description = "smugmug renaming app")

   parser.add_argument("-d", "--dry-run", action = "store_true", default = False,
                       help = "Perform dryrun of operation but don't update")
   parser.add_argument("-p", "--password", default = None,
                       help = "Password (if required) to get user authenticated")

   args = parser.parse_args()

   return args


def printObj(obj):
   print json.dumps(obj, indent = 2)

def smUrl(path):
   """
   Return a smugmug url based upon prefix
   """
   return SM_API_ORIGIN + path


class AppError(RuntimeError):
   """
   Exception that is raised when the application has an error and should exit.
   """


class SmOAuth(object):
   """
   Wrapper around oauth login process for smugmug.
   """
   sOAUTH_ORIGIN      = 'https://secure.smugmug.com'
   sREQUEST_TOKEN_URL = sOAUTH_ORIGIN + '/services/oauth/1.0a/getRequestToken'
   sACCESS_TOKEN_URL  = sOAUTH_ORIGIN + '/services/oauth/1.0a/getAccessToken'
   sAUTHORIZE_URL     = sOAUTH_ORIGIN + '/services/oauth/1.0a/authorize'

   sTOKEN_FILE = "access_token.json"

   def __init__(self, apiKey, apiKeySecret):
      self.apiKey            = apiKey
      self.apiKeySecret      = apiKeySecret
      self.accessToken       = None
      self.accessTokenSecret = None


   def getAuthObj(self):
      """
      Return an auth object to use with requests.
      """
      if self.accessToken is None:
         self.authenticate()

      return OAuth1(self.apiKey, client_secret         = self.apiKeySecret,
                                 resource_owner_key    = self.accessToken,
                                 resource_owner_secret = self.accessTokenSecret,
                                 signature_type        = 'auth_header')

   def getSession(self):
      """
      Return a session that can talk with smugmug.
      """
      if self.accessToken is None:
         self.authenticate()

      s = requests.Session()
      s.auth = self.getAuthObj()
      s.headers = {"Accept": "application/json"}
      return s

   def authenticate(self):
      """
      Setup OAuth 1 authentication with smugmug site for our user details.
      """
      # Check if we already have access token and secret
      if not os.path.exists(self.sTOKEN_FILE):
         # 1) Obtain Request token
         oauth = OAuth1(self.apiKey, client_secret=self.apiKeySecret, callback_uri='oob')
         r = requests.post(url=self.sREQUEST_TOKEN_URL, auth=oauth)
         credentials = parse_qs(r.content)
         resource_owner_key    = credentials.get('oauth_token')[0]
         resource_owner_secret = credentials.get('oauth_token_secret')[0]

         # 2) Obtain authorization for the user to access resources
         # Redirect the user to /authorize and get the callback
         authorize_url = self.sAUTHORIZE_URL + '?oauth_token=' + resource_owner_key + \
                                               '&oauth_consumer_key=' + self.apiKey + \
                                               '&Access=Full&Permissions=Modify'

         print 'Please go here and authorize,', authorize_url
         verifier = raw_input('Please enter the six-digit PIN code: ')

         # 3) Obtain final access token
         oauth = OAuth1(self.apiKey, client_secret         = self.apiKeySecret,
                                     resource_owner_key    = resource_owner_key,
                                     resource_owner_secret = resource_owner_secret,
                                     verifier=verifier)
         r = requests.post(url=self.sACCESS_TOKEN_URL, auth=oauth)

         credentials         = parse_qs(r.content)
         access_token        = credentials.get('oauth_token')[0]
         access_token_secret = credentials.get('oauth_token_secret')[0]

         # Store access token so we can use it later
         with open(self.sTOKEN_FILE, 'w') as f:
            json.dump({'access_token': access_token,
                       'access_token_secret': access_token_secret}, f)

      else:
         with open(self.sTOKEN_FILE, 'r') as f:
            tokens = json.load(f)
            access_token        = tokens.get('access_token')
            access_token_secret = tokens.get('access_token_secret')

      # store the file access token details for use in other methods
      self.accessToken       = access_token
      self.accessTokenSecret = access_token_secret


# Startup main
if __name__ == '__main__':
   main()
