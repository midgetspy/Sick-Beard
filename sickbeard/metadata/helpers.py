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
import urllib2

import sickbeard

from sickbeard import logger, exceptions, helpers
from sickbeard import encodingKludge as ek
from sickbeard.exceptions import ex

from lib.tvdb_api import tvdb_api, tvdb_exceptions

import xml.etree.cElementTree as etree

def getTVDBIDFromNFO(dir):

    if not ek.ek(os.path.isdir, dir):
        logger.log(u"Show dir doesn't exist, can't load NFO")
        raise exceptions.NoNFOException("The show dir doesn't exist, no NFO could be loaded")

    logger.log(u"Loading show info from NFO")

    xmlFile = ek.ek(os.path.join, dir, "tvshow.nfo")

    try:
        xmlFileObj = ek.ek(open, xmlFile, 'r')
        showXML = etree.ElementTree(file = xmlFileObj)

        if showXML.findtext('title') == None or (showXML.findtext('tvdbid') == None and showXML.findtext('id') == None):
            raise exceptions.NoNFOException("Invalid info in tvshow.nfo (missing name or id):" \
                + str(showXML.findtext('title')) + " " \
                + str(showXML.findtext('tvdbid')) + " " \
                + str(showXML.findtext('id')))

        if showXML.findtext('tvdbid') != None:
            tvdb_id = int(showXML.findtext('tvdbid'))
        elif showXML.findtext('id'):
            tvdb_id = int(showXML.findtext('id'))
        else:
            raise exceptions.NoNFOException("Empty <id> or <tvdbid> field in NFO")

        try:
            t = tvdb_api.Tvdb(search_all_languages=True, **sickbeard.TVDB_API_PARMS)
            s = t[int(tvdb_id)]
            if not s  or not s['seriesname']:
                raise exceptions.NoNFOException("Show has no name on TVDB, probably the wrong language")
        except tvdb_exceptions.tvdb_exception, e:
            raise exceptions.NoNFOException("Unable to look up the show on TVDB, not using the NFO")

    except (exceptions.NoNFOException, SyntaxError, ValueError), e:
        logger.log(u"There was an error parsing your existing tvshow.nfo file: " + ex(e), logger.ERROR)
        logger.log(u"Attempting to rename it to tvshow.nfo.old", logger.DEBUG)

        try:
            xmlFileObj.close()
            ek.ek(os.rename, xmlFile, xmlFile + ".old")
        except Exception, e:
            logger.log(u"Failed to rename your tvshow.nfo file - you need to delete it or fix it: " + ex(e), logger.ERROR)
        raise exceptions.NoNFOException("Invalid info in tvshow.nfo")

    return tvdb_id

def getShowImage(url, imgNum=None):

    image_data = None

    if url == None:
        return None

    # if they provided a fanart number try to use it instead
    if imgNum != None:
        tempURL = url.split('-')[0] + "-" + str(imgNum) + ".jpg"
    else:
        tempURL = url

    logger.log(u"Getting show image at "+tempURL, logger.DEBUG)

    image_data = helpers.getURL(tempURL)

    if image_data is None:
        logger.log(u"There was an error trying to retrieve the image, aborting", logger.ERROR)
        return None

    return image_data


