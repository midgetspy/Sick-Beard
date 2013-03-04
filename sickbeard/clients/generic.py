import re
import time
from hashlib import sha1

import sickbeard
from sickbeard import logger
from sickbeard.exceptions import ex
from lib.bencode import bencode, bdecode
from lib import requests

class GenericClient(object):
    
    def __init__(self, name, host=None, username=None, password=None):

        self.name = name
        self.username = sickbeard.TORRENT_USERNAME if username is None else username
        self.password = sickbeard.TORRENT_PASSWORD if password is None else password
        self.host = sickbeard.TORRENT_HOST if host is None else host
        
        self.url = None
        self.response = None
        self.auth = None
        self.last_time = time.time()
        self.session = requests.session(auth=(self.username, self.password),timeout=60)

    def _request(self, method='get', params={}, data=None, files=None):

        if time.time() > self.last_time + 1800 or not self.auth:
            self.last_time = time.time()
            self._get_auth()
        
        logger.log(self.name + u': Requested a ' + method.upper() + ' connection to url '+ self.url + ' with Params= ' + str(params) + ' Data=' + str(data), logger.DEBUG)
        
        if not self.auth:
            logger.log(self.name + u': Autenthication Failed' , logger.ERROR)
            return False
        
        try:
            self.response = self.session.__getattribute__(method)(self.url, params=params, data=data, files=files)
        except requests.exceptions.ConnectionError, e:
            logger.log(self.name + u': Unable to connect ' +ex(e), logger.ERROR)
            return False
        except (requests.exceptions.MissingSchema, requests.exceptions.InvalidURL):
            logger.log(self.name + u': Invalid Host', logger.ERROR)
            return False
        except requests.exceptions.HTTPError, e:
            logger.log(self.name + u': Invalid HTTP Request ' + ex(e), logger.ERROR)
            return False
        except Exception, e:
            logger.log(self.name + u': Unknown exception raised when send torrent to ' + self.name + ': ' + ex(e), logger.ERROR)
            return False
        
        if self.response.status_code == 401:
            logger.log(self.name + u': Invalid Username or Password, check your config', logger.ERROR)    
            return False

        if self.response.status_code == 301:
            logger.log(self.name + u': HTTP Timeout ', logger.DEBUG)        
            return False
        
        logger.log(self.name + u': Response to '+ method.upper() + ' request is ' + self.response.text, logger.DEBUG)
        
        return True

    def _get_auth(self):
        """
        This should be overridden and should return the auth_id needed for the client
        """
        return None
    
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
        """
        This should be overridden should return the True/False from the client 
        when a torrent is set with path
        """        
        return True
    
    def _set_torrent_pause(self, result):
        """
        This should be overridden should return the True/False from the client 
        when a torrent is set with pause
        """
        return True
    
    def _get_torrent_hash(self, result):
        
        if result.url.startswith('magnet'):
            torrent_hash = re.findall('urn:btih:([\w]{32,40})', result.url)[0]
        else:
            info = bdecode(result.content)["info"]
            torrent_hash = sha1(bencode(info)).hexdigest()
        
        return torrent_hash
        
    def sendTORRENT(self, result):
        
        r_code = False

        logger.log(u'Calling ' + self.name + ' Client', logger.DEBUG)

        if not self._get_auth():
            logger.log(self.name + u': Autenthication Failed' , logger.ERROR)
            return r_code
        
        result.hash = self._get_torrent_hash(result)
        
        try:
            if result.url.startswith('magnet'):
                r_code = self._add_torrent_uri(result)
            else:
                r_code = self._add_torrent_file(result)
                
            if not self._set_torrent_pause(result):
                logger.log(self.name + u': Unable to set the pause for Torrent', logger.ERROR)
            
            if not self._set_torrent_label(result):
                logger.log(self.name + u': Unable to set the label for Torrent', logger.ERROR)
            
            if not self._set_torrent_ratio(result):
                logger.log(self.name + u': Unable to set the ratio for Torrent', logger.ERROR)
                
            if not self._set_torrent_path(result):
                logger.log(self.name + u': Unable to set the path for Torrent', logger.ERROR)

        except Exception, e:
            logger.log(self.name + u': Failed Sending Torrent ', logger.ERROR)
            logger.log(self.name + u': Exception raised when sending torrent: ' + ex(e), logger.DEBUG)
            return r_code
        
        return r_code

    def testAuthentication(self):
        
        try:
            self.response = self.session.get(self.url)
        except requests.exceptions.ConnectionError:
            return False, 'Error: ' + self.name + ' Connection Error'
        except (requests.exceptions.MissingSchema, requests.exceptions.InvalidURL):
            return False,'Error: Invalid ' + self.name + ' host'    

        if self.response.status_code == 401:                                            
            return False, 'Error: Invalid ' + self.name + ' Username or Password, check your config!'           
                                                    
        try:                                             
            self._get_auth()                                            
            if self.response.status_code == 200 and self.auth:                                          
                return True, 'Success: Connected and Authenticated'                                     
            else:                                            
                return False, 'Error: Unable to get ' + self.name + ' Authentication, check your config!'             
        except Exception:                                                
            return False, 'Error: Unable to connect to '+ self.name                                            
                                            