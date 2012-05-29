import sickbeard
import httplib
import urllib
import json

from sickbeard import logger, common

class LN_Notifier:
    
    def test_notify(self, ln_api, ln_device, ln_image_url):
        return self._sendLN(ln_api, ln_device, ln_image_url, event="Test", message="Testing LiveNotify settings from Sick Beard", force=True)

    def notify_snatch(self, ep_name):
        if sickbeard.LN_NOTIFY_ONSNATCH:
            self._sendLN(ln_api=None, ln_device=None, ln_image_url=None, event=common.notifyStrings[common.NOTIFY_SNATCH], message=ep_name)

    def notify_download(self, ep_name):
        if sickbeard.LN_NOTIFY_ONDOWNLOAD:
            self._sendLN(ln_api=None, ln_device=None, ln_image_url=None, event=common.notifyStrings[common.NOTIFY_DOWNLOAD], message=ep_name)
        
    def _sendLN(self, ln_api=None, ln_device=None, ln_image_url=None, event=None, message=None, force=False):
        
        if not sickbeard.USE_LN and not force:
            return False
        
        #Sanitize messages for use as URL parameters
        title = urllib.quote_plus("Sick-Beard: " + event)
        message = urllib.quote_plus(message)
        
        #Load API and device variables from sickbeard
        if ln_api == None:
            ln_api = sickbeard.LN_API
            
        if ln_device == None:
            ln_device = sickbeard.LN_DEVICE
            
        if ln_image_url == None:
            ln_image_url = urllib.quote_plus(sickbeard.LN_IMAGE_URL)
    
        logger.log(u"LiveNotify event: " + event, logger.DEBUG)
        logger.log(u"LiveNotify message: " + message, logger.DEBUG)

        #Split up the api keys
        api_keys = ln_api.split(',')
        
        success = True
        #send notification to each api key
        for api_key in range(0, len(api_keys), 1):
            #build up the url for the notification
            http_query = "/notify?apikey=" + api_keys[api_key] + "&title=" + title + "&message=" + message + "&imgurl=" + ln_image_url + "&dest=" + ln_device
            
            #send the query
            notification = httplib.HTTPConnection("api.livenotifier.net")
            notification.request("GET", http_query)
            
            #get the JSON response
            response = json.loads(notification.getresponse().read())
            
            if response["status"] != "OK":
                logger.log(u'Could not send notification ' + str(api_key + 1) + '/' + str(len(api_keys)) + ' to LiveNotify for reason: ' + response["errmsg"], logger.ERROR)
                success = False
        
        return success
                        
notifier = LN_Notifier