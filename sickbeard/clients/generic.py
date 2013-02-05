import re
import time
from hashlib import sha1

import sickbeard
from sickbeard import logger, helpers
from sickbeard.exceptions import ex
from sickbeard.encodingKludge import fixStupidEncodings
from lib.bencode import bencode, bdecode
from lib import requests

class GenericClient(object):
    
    def __init__(self, name=None, host=None, username=None, password=None):

        self.name = name
        
        self.url = ''
        self.username = sickbeard.TORRENT_USERNAME if username is None else username
        self.password = sickbeard.TORRENT_PASSWORD if password is None else password
        
        self.session = requests.session(auth=(self.username, self.password),timeout=10)
        self.response = None
        self.auth = None
        self.last_time = time.time()

    def _request(self, method='get', params={}, data=None, files=None):

        if time.time() > self.last_time + 1800 or not self.auth:
            self.last_time = time.time()
            self._get_auth()
        
        try:
            self.response = self.session.__getattribute__(method)(self.url, params=params, data=data, files=files)
        except requests.exceptions.ConnectionError, e:
            logger.log(u'Unable to connect to '+self.name+' : ' +ex(e), logger.ERROR)
            return False
        except requests.exceptions.MissingSchema, requests.exceptions.InvalidURL:
            logger.log(u'Invalid '+self.name+' host', logger.ERROR)
            return False
        
        if self.response.status_code == '401':
            logger.log(u'Invalid '+self.name+' Username or Password, check your config', logger.ERROR)    
            return False
        
        return True

    def _get_auth(self):
        """
        This should be overridden and should return the auth_id needed for the client
        """
        return False
    
    def _add_torrent_uri(self, result):
        """
        This should be overridden should return the True/False from the client 
        when a torrent is added via url (magnet or .torrent link)
        """
        return False    
    
    def _add_torrent_file(self, result):
        """
        This should be overridden should return the True/False from the client 
        when a torrent is added via result.content (only .torrent file)
        """
        return False    

    def _set_torrent_label(self, result):
        """
        This should be overridden should return the True/False from the client 
        when a torrent is set with label
        """
        return True
    
    def _set_torrent_ratio(self, result):
        """
        This should be overridden should return the True/False from the client 
        when a torrent is set with ratio
        """
        return True

    def _set_torrent_path(self, torrent_path):
        
        return False
    
    def _set_torrent_pause(self, result):

        return True
    
    def _get_torrent_hash(self, result):
        
        if result.url.startswith('magnet'):
            hash = re.findall('urn:btih:([\w]{32,40})', result.url)[0]
        else:
            info = bdecode(result.content)["info"]
            hash = sha1(bencode(info)).hexdigest().upper()
        
        return hash
        
    def sendTORRENT(self, result):
        
        logger.log(u'Calling ' + self.name + ' Client', logger.DEBUG)
        
        r_code = False
        
        result.hash = self._get_torrent_hash(result)
        
        try:
            if result.url.startswith('magnet'):
                r_code = self._add_torrent_uri(result)
            elif result.url.endswith('.torrent'):
                r_code = self._add_torrent_file(result)
            else:
                logger.log(self.name + u': Unknown result type: ' + result.url, logger.ERROR)    
                return False
                
            if not self._set_torrent_pause(result):
                logger.log(self.name + u': Unable to set the pause for Torrent', logger.ERROR)
            
            if not self._set_torrent_label(result):
                logger.log(self.name + u': Unable to set the label for Torrent', logger.ERROR)
            
            if not self._set_torrent_ratio(result):
                logger.log(self.name + u': Unable to set the ratio for Torrent', logger.ERROR)
                
            if not self._set_torrent_path(result):
                logger.log(self.name + u': Unable to set the path for Torrent', logger.ERROR)

        except Exception, e:
            logger.log(u'Unknown exception raised when send torrent to ' + self.name + ': ' + ex(e), logger.ERROR)
            return r_code
        
        return r_code

    def testAuthentication(self):
        
        try:
            self.response = self.session.get(self.url)
        except requests.exceptions.ConnectionError, e:
            return False, 'Unable to connect to '+ self.name
        except requests.exceptions.MissingSchema, requests.exceptions.InvalidURL:
            return False,'Error: Invalid ' + self.name + ' host'    

        if self.response.status_code == 401:
            return False, 'Invalid ' + self.name + 'Username or Password, check your config'        
        
        try: 
          self._get_auth()
          if self.auth:
              return True, 'Success: Connected and Authenticated'
          else:
              return False, 'Unable to connect to ' + self.name
        except Exception, e:    
            return False, 'Unable to connect to '+ self.name