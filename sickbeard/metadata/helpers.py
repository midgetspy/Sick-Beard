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
import os.path
import urllib2

import sickbeard

from sickbeard.common import *
from sickbeard import logger, exceptions, helpers
from sickbeard import encodingKludge as ek

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

        name = showXML.findtext('title')
        if showXML.findtext('tvdbid') != None:
            tvdb_id = int(showXML.findtext('tvdbid'))
        elif showXML.findtext('id'):
            tvdb_id = int(showXML.findtext('id'))
        else:
            raise exceptions.NoNFOException("Empty <id> or <tvdbid> field in NFO")

    except (exceptions.NoNFOException, SyntaxError), e:
        logger.log(u"There was an error parsing your existing tvshow.nfo file: " + str(e), logger.ERROR)
        logger.log(u"Attempting to rename it to tvshow.nfo.old", logger.DEBUG)

        try:
            xmlFileObj.close()
            ek.ek(os.rename, xmlFile, xmlFile + ".old")
        except Exception, e:
            logger.log(u"Failed to rename your tvshow.nfo file - you need to delete it or fix it: " + str(e), logger.ERROR)
        raise exceptions.NoNFOException("Invalid info in tvshow.nfo")

    return tvdb_id

def getShowImage(url, imgNum=None):

    imgFile = None
    imgData = None

    if url == None:
        return None

    # if they provided a fanart number try to use it instead
    if imgNum != None:
        tempURL = url.split('-')[0] + "-" + str(imgNum) + ".jpg"
    else:
        tempURL = url

    logger.log(u"Getting show image at "+tempURL, logger.DEBUG)
    try:
        req = urllib2.Request(tempURL, headers={'User-Agent': USER_AGENT})
        imgFile = urllib2.urlopen(req)
    except urllib2.URLError, e:
        logger.log(u"There was an error trying to retrieve the image, aborting", logger.ERROR)
        return None
    except urllib2.HTTPError, e:
        logger.log(u"Unable to access image at "+tempURL+", assuming it doesn't exist: "+str(e).decode('utf-8'), logger.ERROR)
        return None

    if imgFile == None:
        logger.log(u"Something bad happened and we have no URL data somehow", logger.ERROR)
        return None

    # get the image
    try:
        imgData = imgFile.read()
    except (urllib2.URLError, urllib2.HTTPError), e:
        logger.log(u"There was an error trying to retrieve the image, skipping download: " + str(e), logger.ERROR)
        return None

    return imgData


