import socket
import os
import sys
import sickbeard

from sickbeard import logger

# parse_qsl moved to urlparse module in v2.6
try:
  from urlparse import parse_qsl
except:
  from cgi import parse_qsl

import lib.oauth2 as oauth
import lib.pythontwitter as twitter

consumer_key = "vHHtcB6WzpWDG6KYlBMr8g"
consumer_secret = "zMqq5CB3f8cWKiRO2KzWPTlBanYmV0VYxSXZ0Pxds0E"

REQUEST_TOKEN_URL = 'https://api.twitter.com/oauth/request_token'
ACCESS_TOKEN_URL  = 'https://api.twitter.com/oauth/access_token'
AUTHORIZATION_URL = 'https://api.twitter.com/oauth/authorize'
SIGNIN_URL        = 'https://api.twitter.com/oauth/authenticate'

def get_authorization():

    signature_method_hmac_sha1 = oauth.SignatureMethod_HMAC_SHA1()
    oauth_consumer             = oauth.Consumer(key=consumer_key, secret=consumer_secret)
    oauth_client               = oauth.Client(oauth_consumer)

    logger.log('Requesting temp token from Twitter')

    resp, content = oauth_client.request(REQUEST_TOKEN_URL, 'GET')

    if resp['status'] != '200':
        logger.log('Invalid respond from Twitter requesting temp token: %s' % resp['status'])
    else:
        request_token = dict(parse_qsl(content))

        sickbeard.TWITTER_USERNAME = request_token['oauth_token']
        sickbeard.TWITTER_PASSWORD = request_token['oauth_token_secret']
    
        return AUTHORIZATION_URL+"?oauth_token="+ request_token['oauth_token']

def get_credentials(key):
    request_token = {}

    request_token['oauth_token'] = sickbeard.TWITTER_USERNAME
    request_token['oauth_token_secret'] = sickbeard.TWITTER_PASSWORD
    request_token['oauth_callback_confirmed'] = 'true'

    token = oauth.Token(request_token['oauth_token'], request_token['oauth_token_secret'])
    token.set_verifier(key)

    logger.log('Generating and signing request for an access token using key '+key)

    signature_method_hmac_sha1 = oauth.SignatureMethod_HMAC_SHA1()
    oauth_consumer             = oauth.Consumer(key=consumer_key, secret=consumer_secret)
    logger.log('oauth_consumer: '+str(oauth_consumer))
    oauth_client  = oauth.Client(oauth_consumer, token)
    logger.log('oauth_client: '+str(oauth_client))
    resp, content = oauth_client.request(ACCESS_TOKEN_URL, method='POST', body='oauth_verifier=%s' % key)
    logger.log('resp, content: '+str(resp)+','+str(content))

    access_token  = dict(parse_qsl(content))
    logger.log('access_token: '+str(access_token))

    logger.log('resp[status] = '+str(resp['status']))
    if resp['status'] != '200':
        logger.log('The request for a token with did not succeed: '+str(resp['status']), logger.ERROR)
        return False
    else:
        logger.log('Your Twitter Access Token key: %s' % access_token['oauth_token'])
        logger.log('Access Token secret: %s' % access_token['oauth_token_secret'])
        sickbeard.TWITTER_USERNAME = access_token['oauth_token']
        sickbeard.TWITTER_PASSWORD = access_token['oauth_token_secret']
        return True


def send_tweet(message=None):

    username=consumer_key
    password=consumer_secret
    access_token_key=sickbeard.TWITTER_USERNAME
    access_token_secret=sickbeard.TWITTER_PASSWORD

    logger.log("Sending tweet: "+message)

    api = twitter.Api(username, password, access_token_key, access_token_secret)

    try:
        status = api.PostUpdate(message)
    except Exception, e:
        logger.log("Error Sending Tweet: "+str(e), logger.ERROR)
        return False

    return True

def notifyTwitter(message='', force=False):
    prefix = sickbeard.TWITTER_PREFIX

    if not sickbeard.USE_TWITTER and not force:
        return False

    return send_tweet(prefix+": "+message)
