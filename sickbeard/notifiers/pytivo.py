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
import sickbeard

from urllib import urlencode
from urllib2 import Request, urlopen, URLError

from sickbeard import logger
from sickbeard import encodingKludge as ek
from sickbeard.exceptions import ex

from httplib import HTTPSConnection

class pyTivoNotifier:

    def notify_snatch(self, ep_name):
        pass

    def notify_download(self, ep_name):
        pass

    def update_library(self, ep_obj):

        # only execute if configured
        if sickbeard.USE_PYTIVO:
        # Values from config
            host = sickbeard.PYTIVO_HOST
            shareName = sickbeard.PYTIVO_SHARE_NAME
            tsn = sickbeard.PYTIVO_TIVO_NAME
            
            # There are two more values required, the container and file.
            # 
            # container: The share name, show name and season
            #
            # file: The file name
            # 
            # Some slicing and dicing of variables is required to get at these values.
            #
            # There might be better ways to arrive at the values, but this is the best I have been able to 
            # come up with.
            #
            
            
            # Calculated values
            
            showPath = ep_obj.show.location
            showName = ep_obj.show.name
            rootShowAndSeason = ek.ek(os.path.dirname, ep_obj.location)      
            absPath = ep_obj.location
            
            # Some show names have colons in them which are illegal in a path location, so strip them out.
            # (Are there other characters?)
            showName = showName.replace(":","")
            
            root = showPath.replace(showName, "")
            showAndSeason = rootShowAndSeason.replace(root, "")
            
            
            #logger.log(u"showPath:          " + showPath )
            #logger.log(u"showName:          " + showName )
            #logger.log(u"rootShowAndSeason: " + rootShowAndSeason )
            #logger.log(u"absPath:           " + absPath )
            #logger.log(u"root:              " + root )


            container = shareName + "/" + showAndSeason
            file = "/" + absPath.replace(root, "")
            
            
            # Finally create the url and make request
            
            requestUrl = "http://" + host + "/TiVoConnect?" + urlencode( {'Command':'Push', 'Container':container, 'File':file, 'tsn':tsn} )
            
            logger.log(u"pyTivo notification: Requesting " + requestUrl)
        
            request = Request( requestUrl )

            try:
                response = urlopen(request)      
            except URLError, e:
                if hasattr(e, 'reason'):
                    logger.log(u"pyTivo notification: Error, failed to reach a server")
                    logger.log(u"'Error reason: " + e.reason)
                    return False
                elif hasattr(e, 'code'):
                    logger.log(u"pyTivo notification: Error, the server couldn't fulfill the request")
                    logger.log(u"Error code: " + e.code)
                    return False
            else:
                logger.log(u"pyTivo notification: Successfully requested transfer of file")
                return True

notifier = pyTivoNotifier
