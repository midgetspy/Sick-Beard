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


import httplib
import datetime
import urlparse

import sickbeard

from base64 import standard_b64encode
import xmlrpclib

from sickbeard import encodingKludge as ek
from sickbeard.exceptions import ex
from sickbeard.providers.generic import GenericProvider
from sickbeard import config
from sickbeard import logger
from common import Quality


def sendNZB(nzb):

    if sickbeard.NZBGET_HOST == None:
        logger.log(u"No NZBGet host found in configuration. Please configure it.", logger.ERROR)
        return False

    nzbFileName = nzb.name + ".nzb"
    try:
        url = config.clean_url(sickbeard.NZBGET_HOST)

        if sickbeard.NZBGET_USERNAME or sickbeard.NZBGET_PASSWORD:
            scheme, netloc, path, query, fragment = urlparse.urlsplit(url)
            netloc = sickbeard.NZBGET_USERNAME + ":" + sickbeard.NZBGET_PASSWORD + "@" + netloc
            url = urlparse.urlunsplit((scheme, netloc, path, query, fragment))

        url = urlparse.urljoin(url, u"/xmlrpc")
        url = url.encode('utf-8', 'ignore')

        logger.log(u"Sending NZB to NZBGet")
        logger.log(u"NZBGet URL: " + url, logger.DEBUG)

        nzbGetRPC = xmlrpclib.ServerProxy(url)

        if nzbGetRPC.writelog("INFO", "SickBeard connected to drop off " + nzbFileName + " any moment now."):
            logger.log(u"Successful connected to NZBGet", logger.DEBUG)
        else:
            logger.log(u"Successful connected to NZBGet, but unable to send a message", logger.ERROR)

    except httplib.socket.error:
        logger.log(u"Please check if NZBGet is running. NZBGet is not responding.", logger.ERROR)
        return False

    except xmlrpclib.ProtocolError, e:
        if (e.errmsg == "Unauthorized"):
            logger.log(u"NZBGet username or password is incorrect.", logger.ERROR)
        else:
            logger.log(u"NZBGet protocol error: " + e.errmsg, logger.ERROR)
        return False

    except Exception, e:
        logger.log(u"NZBGet sendNZB failed. Error: " + ex(e), logger.ERROR)
        return False

    # if it aired recently make it high priority and generate dupekey/dupescore
    addToTop = False
    nzbgetprio = dupescore = 0
    dupekey = ""

    for curEp in nzb.episodes:
        if dupekey == "":
            dupekey = "Sickbeard-" + str(curEp.show.tvdbid)
        dupekey += "-" + str(curEp.season) + "." + str(curEp.episode)
        if datetime.date.today() - curEp.airdate <= datetime.timedelta(days=7):
            addToTop = True
            nzbgetprio = 100

    # tweak dupescore based off quality, higher score wins
    if nzb.quality != Quality.UNKNOWN:
        dupescore = nzb.quality * 100
    if nzb.quality == Quality.SNATCHED_PROPER:
        dupescore += 10

    nzbcontent64 = None
    # if we get a raw data result we encode contents and pass that
    if nzb.resultType == "nzbdata":
        data = nzb.extraInfo[0]
        nzbcontent64 = standard_b64encode(data)

    logger.log(u"Attempting to send NZB to NZBGet (" + sickbeard.NZBGET_CATEGORY + ")", logger.DEBUG)
    try:
        # find out nzbget version to branch logic, 0.8.x and older will return 0
        nzbget_version_str = nzbGetRPC.version()
        nzbget_version = config.to_int(nzbget_version_str[:nzbget_version_str.find(".")])

        # v8 and older, no priority or dupe info
        if nzbget_version == 0:
            if nzbcontent64 is not None:
                nzbget_result = nzbGetRPC.append(nzbFileName, sickbeard.NZBGET_CATEGORY, addToTop, nzbcontent64)
            else:
                # appendurl not supported on older versions, so d/l nzb data from url ourselves
                if nzb.resultType == "nzb":
                    genProvider = GenericProvider("")
                    data = genProvider.getURL(nzb.url)
                    if data == None:
                        return False
                    nzbcontent64 = standard_b64encode(data)
                nzbget_result = nzbGetRPC.append(nzbFileName, sickbeard.NZBGET_CATEGORY, addToTop, nzbcontent64)

        # v12+ pass dupekey + dupescore
        elif nzbget_version >= 12:
            if nzbcontent64 is not None:
                nzbget_result = nzbGetRPC.append(nzbFileName, sickbeard.NZBGET_CATEGORY, nzbgetprio, False, nzbcontent64, False, dupekey, dupescore, "score")
            else:
                nzbget_result = nzbGetRPC.appendurl(nzbFileName, sickbeard.NZBGET_CATEGORY, nzbgetprio, False, nzb.url, False, dupekey, dupescore, "score")

        # v9+ pass priority, no dupe info
        else:
            if nzbcontent64 is not None:
                nzbget_result = nzbGetRPC.append(nzbFileName, sickbeard.NZBGET_CATEGORY, nzbgetprio, False, nzbcontent64)
            else:
                nzbget_result = nzbGetRPC.appendurl(nzbFileName, sickbeard.NZBGET_CATEGORY, nzbgetprio, False, nzb.url)

        if nzbget_result:
            logger.log(u"NZB sent to NZBGet successfully", logger.DEBUG)
            return True
        else:
            logger.log(u"NZBGet could not add %s to the queue" % (nzbFileName), logger.ERROR)
            return False
    except:
        logger.log(u"Connect Error to NZBGet: could not add %s to the queue" % (nzbFileName), logger.ERROR)
        return False
