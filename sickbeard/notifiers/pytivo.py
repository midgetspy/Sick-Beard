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
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.



import os
import subprocess
import urllib
import urllib2

import sickbeard

from sickbeard import logger
from sickbeard import encodingKludge as ek
from sickbeard.exceptions import ex

from httplib import HTTPSConnection
#from urllib import urlencode

class pyTivoNotifier:

    def notify_snatch(self, ep_name):
        pass

    def notify_download(self, ep_name):
        pass

    def update_library(self, ep_obj):
        logger.log(u"pyTivo update_library called")


		# Values from config
        
        # Hard Coded for now.                
        #host="http://media:9032/"
        #tsn="Tee Vee"
        #shareName = "Media/"
        
        host = sickbeard.PYTIVO_HOST
        shareName = sickbeard.PYTIVO_SHARE_NAME
        tsn = sickbeard.PYTIVO_TIVO_NAME
        
        
        # Calculated values

        showPath = ep_obj.show.location
        showName = ep_obj.show.name
        rootShowAndSeason = ek.ek(os.path.dirname, ep_obj.location)      
        absPath = ep_obj.location
        
        
        logger.log(u"showPath:          " + showPath )
        logger.log(u"showName:          " + showName )
        logger.log(u"rootShowAndSeason: " + rootShowAndSeason )
        logger.log(u"absPath:           " + absPath )

                
        root = showPath.replace(showName, "")
  
        showAndSeason = rootShowAndSeason.replace(root, "")
        container = shareName + "/" + showAndSeason

        file = "/" + absPath.replace(root, "")
        
        
        # Finally create the url and make request
        
        requestUrl = "http://" + host + "/TiVoConnect?" + urllib.urlencode( {'Command':'Push', 'Container':container, 'File':file, 'tsn':tsn} )
               
        logger.log(u"request: " + requestUrl )
        
        request = urllib2.Request( requestUrl )
        response = urllib2.urlopen(request)

		
		# Parse response

        logger.log(u"response.status: " + response.status);

        request_status = response.status

        if request_status == 200:
            logger.log(u"pyTivo notifications sent.", logger.DEBUG)
            return True
        else:
            logger.log(u"pyTivo notification failed.", logger.ERROR)
            return False

notifier = pyTivoNotifier
