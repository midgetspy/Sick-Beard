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

import urllib

from sickbeard import logger, helpers, ui

from sickbeard.exceptions import ex

from sickbeard import encodingKludge as ek

def saveSTRM(nzb):

    newResult = False

    nzbProvider = nzb.provider

    if sickbeard.TV_DOWNLOAD_DIR == None:
        logger.log(u"No TV downloader directory found in configuration. Please configure it.", logger.ERROR)
        return False

    fileContents = "plugin://plugin.program.pneumatic/?mode=strm&nzb=" + urllib.quote_plus(nzb.url) + "&nzbname=" + nzb.name

    # get the final file path to the strm file
    destinationPath = ek.ek(os.path.join, sickbeard.TV_DOWNLOAD_DIR, nzb.name)
    helpers.makeDir(destinationPath)
    fileName = ek.ek(os.path.join, destinationPath, nzb.name + ".strm")

    logger.log(u"Saving STRM to " + fileName)

    newResult = True

    # save the data to disk
    try:
        fileOut = open(fileName, "w")
        fileOut.write(fileContents)
        fileOut.close()
        helpers.chmodAsParent(fileName)
    except IOError, e:
        logger.log(u"Error trying to save STRM to TV downloader directory: "+ex(e), logger.ERROR)
        newResult = False

    if newResult:
        ui.notifications.message('Episode snatched','<b>%s</b> snatched from <b>%s</b>' % (nzb.name, nzbProvider.name))

    return newResult
