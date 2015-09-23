# Author: Nic Wolfe <nic@wolfeden.ca>
# URL: http://code.google.com/p/sickbeard/
#
# This file is part of Sick Beard.
#
# Sick Beard is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Sick Beard is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.

import sickbeard

from sickbeard import logger, common
from sickbeard.exceptions import ex

# parse_qsl moved to urlparse module in v2.6
try:
    from urlparse import parse_qsl  # @UnusedImport
except:
    from cgi import parse_qsl  # @Reimport

import lib.oauth2 as oauth
import lib.pythontwitter as twitter


class TwitterNotifier:

    consumer_key = "vHHtcB6WzpWDG6KYlBMr8g"
    consumer_secret = "zMqq5CB3f8cWKiRO2KzWPTlBanYmV0VYxSXZ0Pxds0E"

    REQUEST_TOKEN_URL = "https://api.twitter.com/oauth/request_token"
    ACCESS_TOKEN_URL = "https://api.twitter.com/oauth/access_token"
    AUTHORIZATION_URL = "https://api.twitter.com/oauth/authorize"
    SIGNIN_URL = "https://api.twitter.com/oauth/authenticate"

    def _get_authorization(self):

        signature_method_hmac_sha1 = oauth.SignatureMethod_HMAC_SHA1()  # @UnusedVariable
        oauth_consumer = oauth.Consumer(key=self.consumer_key, secret=self.consumer_secret)
        oauth_client = oauth.Client(oauth_consumer)

        logger.log(u'TWITTER: Requesting temp token from Twitter', logger.DEBUG)

        resp, content = oauth_client.request(self.REQUEST_TOKEN_URL, 'GET')

        if resp['status'] != '200':
            logger.log(u"TWITTER: Invalid respond from Twitter requesting temp token: %s" % resp['status'], logger.ERROR)
        else:
            request_token = dict(parse_qsl(content))

            sickbeard.TWITTER_USERNAME = request_token['oauth_token']
            sickbeard.TWITTER_PASSWORD = request_token['oauth_token_secret']

            return self.AUTHORIZATION_URL + "?oauth_token=" + request_token['oauth_token']

    def _get_credentials(self, key):
        request_token = {}

        request_token['oauth_token'] = sickbeard.TWITTER_USERNAME
        request_token['oauth_token_secret'] = sickbeard.TWITTER_PASSWORD
        request_token['oauth_callback_confirmed'] = 'true'

        token = oauth.Token(request_token['oauth_token'], request_token['oauth_token_secret'])
        token.set_verifier(key)

        logger.log(u"TWITTER: Generating and signing request for an access token using key " + key, logger.DEBUG)

        signature_method_hmac_sha1 = oauth.SignatureMethod_HMAC_SHA1()  # @UnusedVariable
        oauth_consumer = oauth.Consumer(key=self.consumer_key, secret=self.consumer_secret)
        logger.log(u"TWITTER: oauth_consumer: " + str(oauth_consumer), logger.DEBUG)
        oauth_client = oauth.Client(oauth_consumer, token)
        logger.log(u"TWITTER: oauth_client: " + str(oauth_client), logger.DEBUG)
        resp, content = oauth_client.request(self.ACCESS_TOKEN_URL, method='POST', body='oauth_verifier=%s' % key)
        logger.log(u"TWITTER: resp, content: " + str(resp) + "," + str(content), logger.DEBUG)

        access_token = dict(parse_qsl(content))
        logger.log(u"TWITTER: access_token: " + str(access_token), logger.DEBUG)

        logger.log(u"TWITTER: resp[status] = " + str(resp['status']), logger.DEBUG)
        if resp['status'] != '200':
            logger.log(u"TWITTER: The request for a token with did not succeed: " + str(resp['status']), logger.ERROR)
            return False
        else:
            logger.log(u"TWITTER: Your Twitter Access Token key: %s" % access_token['oauth_token'], logger.DEBUG)
            logger.log(u"TWITTER: Access Token secret: %s" % access_token['oauth_token_secret'], logger.DEBUG)
            sickbeard.TWITTER_USERNAME = access_token['oauth_token']
            sickbeard.TWITTER_PASSWORD = access_token['oauth_token_secret']
            return True

    def _send_tweet(self, message=None):

        username = self.consumer_key
        password = self.consumer_secret
        access_token_key = sickbeard.TWITTER_USERNAME
        access_token_secret = sickbeard.TWITTER_PASSWORD

        logger.log(u"TWITTER: Sending tweet: " + message, logger.DEBUG)

        api = twitter.Api(username, password, access_token_key, access_token_secret)

        try:
            api.PostUpdate(message)
        except Exception, e:
            logger.log(u"TWITTER: Error Sending Tweet: " + ex(e), logger.ERROR)
            return False

        return True

    def _notify(self, message='', force=False):
        # suppress notifications if the notifier is disabled but the notify options are checked
        if not sickbeard.USE_TWITTER and not force:
            return False

        return self._send_tweet(sickbeard.TWITTER_PREFIX + ": " + message)

##############################################################################
# Public functions
##############################################################################

    def notify_snatch(self, ep_name):
        if sickbeard.TWITTER_NOTIFY_ONSNATCH:
            self._notify(common.notifyStrings[common.NOTIFY_SNATCH] + ': ' + ep_name)

    def notify_download(self, ep_name):
        if sickbeard.TWITTER_NOTIFY_ONDOWNLOAD:
            self._notify(common.notifyStrings[common.NOTIFY_DOWNLOAD] + ': ' + ep_name)

    def test_notify(self):
        return self._notify("This is a test notification from Sick Beard", force=True)

    def update_library(self, ep_obj):
        pass

notifier = TwitterNotifier
