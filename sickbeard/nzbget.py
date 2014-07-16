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
import urllib
import urlparse

import sickbeard

from base64 import standard_b64encode
import xmlrpclib

from sickbeard.exceptions import ex
from sickbeard.providers.generic import GenericProvider
from sickbeard import config
from sickbeard import logger
from common import Quality


def sendNZB(nzb):

    if not sickbeard.NZBGET_HOST:
        logger.log(u"No NZBGet host found in configuration. Please configure it.", logger.ERROR)
        return False

    nzb_filename = nzb.name + ".nzb"

    try:
        url = config.clean_url(sickbeard.NZBGET_HOST)

        scheme, netloc, path, query, fragment = urlparse.urlsplit(url)  # @UnusedVariable

        if sickbeard.NZBGET_USERNAME or sickbeard.NZBGET_PASSWORD:
            netloc = urllib.quote_plus(sickbeard.NZBGET_USERNAME.encode("utf-8", 'ignore')) + u":" + urllib.quote_plus(sickbeard.NZBGET_PASSWORD.encode("utf-8", 'ignore')) + u"@" + netloc

        url = urlparse.urlunsplit((scheme, netloc, u"/xmlrpc", "", ""))

        logger.log(u"Sending NZB to NZBGet")
        logger.log(u"NZBGet URL: " + url, logger.DEBUG)

        nzbGetRPC = xmlrpclib.ServerProxy(url.encode("utf-8", 'ignore'))

        if nzbGetRPC.writelog("INFO", "SickBeard connected to drop off " + nzb_filename + " any moment now."):
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
        logger.log(u"NZBGet sendNZB failed. URL: " + url + " Error: " + ex(e), logger.ERROR)
        return False

    # if it aired recently make it high priority and generate dupekey/dupescore
    add_to_top = False
    nzbgetprio = dupescore = 0
    dupekey = ""

    for curEp in nzb.episodes:
        if dupekey == "":
            dupekey = "SickBeard-" + str(curEp.show.tvdbid)

        dupekey += "-" + str(curEp.season) + "." + str(curEp.episode)

        if datetime.date.today() - curEp.airdate <= datetime.timedelta(days=7):
            add_to_top = True
            nzbgetprio = 100

    # tweak dupescore based off quality, higher score wins
    if nzb.quality != Quality.UNKNOWN:
        dupescore = nzb.quality * 100

    if nzb.quality == Quality.SNATCHED_PROPER:
        dupescore += 10

    nzbget_result = None
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
            if nzbcontent64:
                nzbget_result = nzbGetRPC.append(nzb_filename, sickbeard.NZBGET_CATEGORY, add_to_top, nzbcontent64)

            else:
                # appendurl not supported on older versions, so d/l nzb data from url ourselves
                if nzb.resultType == "nzb":
                    genProvider = GenericProvider("")
                    data = genProvider.getURL(nzb.url)

                    if data:
                        nzbcontent64 = standard_b64encode(data)
                        nzbget_result = nzbGetRPC.append(nzb_filename, sickbeard.NZBGET_CATEGORY, add_to_top, nzbcontent64)

        # v13+ has a new combined append method that accepts both (url and content)
        elif nzbget_version >= 13:
            if nzbcontent64:
                nzbget_result = nzbGetRPC.append(nzb_filename, nzbcontent64, sickbeard.NZBGET_CATEGORY, nzbgetprio, False, False, dupekey, dupescore, "score")
            else:
                nzbget_result = nzbGetRPC.append(nzb_filename, nzb.url, sickbeard.NZBGET_CATEGORY, nzbgetprio, False, False, dupekey, dupescore, "score")

            # the return value has changed from boolean to integer (Positive number representing NZBID of the queue item. 0 and negative numbers represent error codes.)
            if nzbget_result > 0:
                nzbget_result = True
            else:
                nzbget_result = False

        # v12 pass dupekey + dupescore
        elif nzbget_version == 12:
            if nzbcontent64:
                nzbget_result = nzbGetRPC.append(nzb_filename, sickbeard.NZBGET_CATEGORY, nzbgetprio, False, nzbcontent64, False, dupekey, dupescore, "score")
            else:
                nzbget_result = nzbGetRPC.appendurl(nzb_filename, sickbeard.NZBGET_CATEGORY, nzbgetprio, False, nzb.url, False, dupekey, dupescore, "score")

        # v9+ pass priority, no dupe info
        else:
            if nzbcontent64:
                nzbget_result = nzbGetRPC.append(nzb_filename, sickbeard.NZBGET_CATEGORY, nzbgetprio, False, nzbcontent64)
            else:
                nzbget_result = nzbGetRPC.appendurl(nzb_filename, sickbeard.NZBGET_CATEGORY, nzbgetprio, False, nzb.url)

        if nzbget_result:
            logger.log(u"NZB sent to NZBGet successfully", logger.DEBUG)
            return True
        else:
            logger.log(u"NZBGet could not add " + nzb_filename + " to the queue", logger.ERROR)
            return False

    except:
        logger.log(u"Connect Error to NZBGet: could not add " + nzb_filename + " to the queue", logger.ERROR)
        return False

    return False
