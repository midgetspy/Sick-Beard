from httplib import HTTPSConnection
from urllib import urlencode

import sickbeard

from sickbeard import logger, common
from lib.pynma import pynma

class NMA_Notifier:
    
    def test_notify(self, nma_api, nma_priority):
        return self._sendNMA(nma_api, nma_priority, event="Test", message="Testing NMA settings from Sick Beard", force=True)

    def notify_snatch(self, ep_name):
        if sickbeard.NMA_NOTIFY_ONSNATCH:
            self._sendNMA(nma_api=None, nma_priority=None, event=common.notifyStrings[common.NOTIFY_SNATCH], message=ep_name)

    def notify_download(self, ep_name):
        if sickbeard.NMA_NOTIFY_ONDOWNLOAD:
            self._sendNMA(nma_api=None, nma_priority=None, event=common.notifyStrings[common.NOTIFY_DOWNLOAD], message=ep_name)
        
    def _sendNMA(self, nma_api=None, nma_priority=None, event=None, message=None, force=False):
    
        title = 'Sick-Beard'
    
        if not sickbeard.USE_NMA and not force:
            return False
        
        if nma_api == None:
            nma_api = sickbeard.NMA_API
            
        if nma_priority == None:
            nma_priority = sickbeard.NMA_PRIORITY
    
        logger.log(u"NMA title: " + title, logger.DEBUG)
        logger.log(u"NMA event: " + event, logger.DEBUG)
        logger.log(u"NMA message: " + message, logger.DEBUG)
        
        batch = False
        
        p = pynma.PyNMA()
        keys = nma_api.split(',')
        p.addkey(keys)
        
        if len(keys) > 1: batch = True
        
        response = p.push(title, event, message, priority=nma_priority, batch_mode=batch)
               
        if not response[nma_api][u'code'] == u'200':
            logger.log(u'Could not send notification to NotifyMyAndroid', logger.ERROR)
            return False
        else:
            return True
                        
notifier = NMA_Notifier