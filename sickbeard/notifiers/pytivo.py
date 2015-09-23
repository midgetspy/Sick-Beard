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
import sickbeard

from urllib import urlencode
from urllib2 import Request, urlopen

from sickbeard import logger
from sickbeard.exceptions import ex
from sickbeard import encodingKludge as ek


class pyTivoNotifier:

##############################################################################
# Public functions
##############################################################################

    def notify_snatch(self, ep_name):
        pass

    def notify_download(self, ep_name):
        pass

    def update_library(self, ep_obj=None):

        if not sickbeard.USE_PYTIVO:
            return False

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

        # Calculated values
        showPath = ep_obj.show.location
        showName = ep_obj.show.name
        rootShowAndSeason = ek.ek(os.path.dirname, ep_obj.location)
        absPath = ep_obj.location

        # Some show names have colons in them which are illegal in a path location, so strip them out.
        # (Are there other characters?)
        showName = showName.replace(":", "")

        root = showPath.replace(showName, "")
        showAndSeason = rootShowAndSeason.replace(root, "")

        container = shareName + "/" + showAndSeason
        mediaFile = "/" + absPath.replace(root, "")

        # Finally create the url and make request
        requestUrl = "http://" + host + "/TiVoConnect?" + urlencode( {'Command': 'Push', 'Container': container, 'File': mediaFile, 'tsn': tsn})

        logger.log(u"PYTIVO: Requesting " + requestUrl, logger.DEBUG)

        request = Request(requestUrl)

        try:
            response = urlopen(request)  # @UnusedVariable
        except IOError, e:
            if hasattr(e, 'reason'):
                logger.log(u"PYTIVO: Failed to reach server '%s' - %s" % (host, e.reason), logger.WARNING)
            elif hasattr(e, 'code'):
                logger.log(u"PYTIVO: The server could not fulfill the request '%s' - %s" % (host, e.code), logger.WARNING)
            return False
        except Exception, e:
            logger.log(u"PYTIVO: Unknown exception: " + ex(e), logger.ERROR)
            return False
        else:
            logger.log(u"PYTIVO: Successfully requested transfer of file", logger.MESSAGE)
            return True

notifier = pyTivoNotifier
