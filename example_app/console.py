#!/usr/bin/env python3

import json
from rauth import OAuth1Session
import sys

from common import *

def main():
    rt, rts = SERVICE.get_request_token(params={'oauth_callback': 'oob'})
    auth_url = add_auth_params(SERVICE.get_authorize_url(rt),
                     access='Full', permissions='Modify')
    print('Go to %s in a web browser.' % auth_url)
    sys.stdout.write('Enter the six-digit code: ')
    sys.stdout.flush()
    verifier = sys.stdin.readline().strip()
    at, ats = SERVICE.get_access_token(rt, rts,
                       params={'oauth_verifier': verifier})
    session = OAuth1Session(API_KEY, API_KEY_SECRET, access_token=at,
                                 access_token_secret=ats)
    print("Access Token: ", at)
    print("Access Token Secret: ", ats)

    print(session.get(API_ORIGIN + '/api/v2!authuser',
                    headers={'Accept': 'application/json'}).text)

    # Pick the first image in recent images and change the caption
    if 1:
        headers = {'Accept': 'application/json'}

        new_caption = "Test Caption"
        r = session.get(API_ORIGIN + '/api/v2!authuser', headers = headers)
        r_obj = r.json()

        user_obj = r_obj['Response']['User']
        user_uris = user_obj['Uris']
        recent_images_uri = user_uris['UserRecentImages']['Uri']

        r = session.get(API_ORIGIN + recent_images_uri, headers = headers)
        r_obj = r.json()
        image_objs = r_obj['Response']['Image']

        first_image = image_objs[0]
        image_uri = first_image['Uri']

        # change the image caption
        r = session.patch(API_ORIGIN + image_uri,
                        data = json.dumps({'Caption': new_caption}), headers = headers)
        print("Patch result")
        print(r.content)

if __name__ == '__main__':
    main()

