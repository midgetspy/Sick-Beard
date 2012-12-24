import sickbeard

from sickbeard import logger, common
from lib.pynma import pynma

from sickbeard.INotifierPlugin import INotifierPlugin
from sickbeard.config import CheckSection, check_setting_int, check_setting_str, ConfigMigrator

from sickbeard.webserve import Home
import cherrypy
import os

class NMA_Notifier(INotifierPlugin):
    
    def test_notify(self, nma_api, nma_priority):
        return self._sendNMA(nma_api, nma_priority, event="Test", message="Testing NMA settings from Sick Beard", force=True)

    def notify_snatch(self, ep_name):
        if self.NMA_NOTIFY_ONSNATCH:
            self._sendNMA(nma_api=None, nma_priority=None, event=common.notifyStrings[common.NOTIFY_SNATCH], message=ep_name)

    def notify_download(self, ep_name):
        if self.NMA_NOTIFY_ONDOWNLOAD:
            self._sendNMA(nma_api=None, nma_priority=None, event=common.notifyStrings[common.NOTIFY_DOWNLOAD], message=ep_name)
        
    def _sendNMA(self, nma_api=None, nma_priority=None, event=None, message=None, force=False):
    
        title = 'Sick-Beard'
    
        if not self.USE_NMA and not force:
            return False
        
        if nma_api == None:
            nma_api = self.NMA_API
            
        if nma_priority == None:
            nma_priority = self.NMA_PRIORITY
    
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

    def __init__(self):
        INotifierPlugin .__init__(self)
        
        self.USE_NMA = False
        self.NMA_NOTIFY_ONSNATCH = False
        self.NMA_NOTIFY_ONDOWNLOAD = False
        self.NMA_API = None
        self.NMA_PRIORITY = 0
        self.type = INotifierPlugin.NOTIFY_DEVICE
    
    def _addMethod(self):
        def testNMA(newself, nma_api=None, nma_priority=0):
            cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"
            
            result = self.test_notify(nma_api, nma_priority)
            if result:
                return "Test NMA notice sent successfully"
            else:
                return "Test NMA notice failed"
        
        testNMA.exposed = True
        Home.testNMA = testNMA

    def _addStatic(self):
        app = cherrypy.tree.apps[sickbeard.WEB_ROOT]
        app.merge({
             '/images/notifiers/nma.png': {
                'tools.staticfile.on': True,
                'tools.staticfile.filename': os.path.join(os.path.dirname(__file__), 'data/images/nma.png'),
             },
             '/js/configNMA.js': {
                'tools.staticfile.on': True,
                'tools.staticfile.filename': os.path.join(os.path.dirname(__file__), 'data/notification.js'),
             }
        })

    def _removeMethod(self):
        if hasattr(Home, 'testNMA'):
            del Home.testNMA

    def _removeStatic(self):
        pass

    def updateConfig(self, **kwargs):
        default = {
            'use_nma': 0,
            'nma_notify_onsnatch': 0,
            'nma_notify_ondownload' : 0,
            'nma_api' : None,
            'nma_priority' : 0
            }
        
        for key, defval in default.items():
            value = kwargs.get(key, defval)
            val = 1 if value == "on" else value
            
            if hasattr(self, key.upper()):
                setattr(self, key.upper(), val)
            else:
                logger.log("Unknown notification setting: " + key, logger.ERROR)
    
    def readConfig(self, config):
        CheckSection(config, 'NMA')
        self.USE_NMA = bool(check_setting_int(config, 'NMA', 'use_nma', 0))
        self.NMA_NOTIFY_ONSNATCH = bool(check_setting_int(config, 'NMA', 'nma_notify_onsnatch', 0))
        self.NMA_NOTIFY_ONDOWNLOAD = bool(check_setting_int(config, 'NMA', 'nma_notify_ondownload', 0))
        self.NMA_API = check_setting_str(config, 'NMA', 'nma_api', '')
        self.NMA_PRIORITY = check_setting_str(config, 'NMA', 'nma_priority', "0")
        
    def writeConfig(self, new_config):        
        new_config['NMA'] = {}
        new_config['NMA']['use_nma'] = int(self.USE_NMA)
        new_config['NMA']['nma_notify_onsnatch'] = int(self.NMA_NOTIFY_ONSNATCH)
        new_config['NMA']['nma_notify_ondownload'] = int(self.NMA_NOTIFY_ONDOWNLOAD)
        new_config['NMA']['nma_api'] = self.NMA_API
        new_config['NMA']['nma_priority'] = self.NMA_PRIORITY
    
        return new_config
    
    def activateHook(self):
        self._addMethod()
        self._addStatic()

    def deactivateHook(self):
        self._removeMethod()
        self._removeStatic()
