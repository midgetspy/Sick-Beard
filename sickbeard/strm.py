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

import urllib2

import re

import xml.etree.cElementTree as etree

from name_parser.parser import NameParser, InvalidNameException

from sickbeard import logger, helpers, ui, nzbSplitter, classes

from sickbeard.exceptions import ex

from sickbeard import encodingKludge as ek

def _getSeasonNZBs(name, urlData, season, showName):

    try:
        showXML = etree.ElementTree(etree.XML(urlData))
    except SyntaxError:
        logger.log(u"Unable to parse the XML of "+name+", not splitting it", logger.ERROR)
        return ({},'')

    filename = name.replace(".nzb", "")

    nzbElement = showXML.getroot()

    #regex = '([\w\._\ ]+)[\. ]S%02d[\. ]([\w\._\-\ ]+)[\- ]([\w_\-\ ]+?)' % season

    #sceneNameMatch = re.search(regex, filename, re.I)
    #if sceneNameMatch:
    #    showName, qualitySection, groupName = sceneNameMatch.groups() #@UnusedVariable
    #else:
    #    logger.log(u"Unable to parse "+name+" into a scene name. If it's a valid one log a bug.", logger.ERROR)
    #    return ({},'')

    epFiles = {}
    xmlns = None

    regex1 = '(' + re.escape(showName) + '\.S%02d(?:[E0-9]+)\.[\w\._]+\-\w+' % season + ')'
    regex2 = '(' + re.escape(showName) + '\.%dx(?:[0-9]+)\.[\w\._]+\-\w+' % season + ')'
    regex3 = '(' + re.escape(showName) + '\.%d(?:[0-9]+)' % season + ')'
    regex1 = regex1.replace(' ', '.')
    regex2 = regex2.replace(' ', '.')
    regex3 = regex3.replace(' ', '.')

    for curFile in nzbElement.getchildren():
        xmlnsMatch = re.match("\{(http:\/\/[A-Za-z0-9_\.\/]+\/nzb)\}file", curFile.tag)
        if not xmlnsMatch:
            continue
        else:
            xmlns = xmlnsMatch.group(1)
        tempFile = curFile.get("subject")
        tempFile = tempFile.replace(' ', '.')
        match = re.search(regex1, tempFile, re.I)
        if not match:
            match = re.search(regex2, tempFile, re.I)
            if not match:
                match = re.search(regex3, tempFile, re.I)
                if not match:
                    #print curFile.get("subject"), "doesn't match", regex
                    continue
        curEp = match.group(1)
        if curEp not in epFiles:
            epFiles[curEp] = [curFile]
        else:
            epFiles[curEp].append(curFile)

    return (epFiles, xmlns)

def _splitResult(result):

    try:
        urlData = helpers.getURL(result.url)
    except urllib2.URLError:
        logger.log(u"Unable to load url "+result.url+", can't download season NZB", logger.ERROR)
        return False

    # parse the season ep name
    try:
        np = NameParser(False)
        parse_result = np.parse(result.name)
    except InvalidNameException:
        logger.log(u"Unable to parse the filename "+result.name+" into a valid episode", logger.WARNING)
        return False

    # bust it up
    season = parse_result.season_number if parse_result.season_number != None else 1

    separateNZBs, xmlns = _getSeasonNZBs(result.name, urlData, season, parse_result.series_name)

    resultList = []

    if len(separateNZBs) > 1:
        for newNZB in separateNZBs:

            logger.log(u"Split out "+newNZB+" from "+result.name, logger.DEBUG)

            # parse the name
            try:
                np = NameParser(False)
                parse_result = np.parse(newNZB)
            except InvalidNameException:
                logger.log(u"Unable to parse the filename "+newNZB+" into a valid episode", logger.WARNING)
                return False

            # make sure the result is sane
            if (parse_result.season_number != None and parse_result.season_number != season) or (parse_result.season_number == None and season != 1):
                logger.log(u"Found "+newNZB+" inside "+result.name+" but it doesn't seem to belong to the same season, ignoring it", logger.WARNING)
                continue
            elif len(parse_result.episode_numbers) == 0:
                logger.log(u"Found "+newNZB+" inside "+result.name+" but it doesn't seem to be a valid episode NZB, ignoring it", logger.WARNING)
                continue

            wantEp = True
            for epNo in parse_result.episode_numbers:
                if not result.extraInfo[0].wantEpisode(season, epNo, result.quality):
                    logger.log(u"Ignoring result "+newNZB+" because we don't want an episode that is "+Quality.qualityStrings[result.quality], logger.DEBUG)
                    wantEp = False
                    break
            if not wantEp:
                continue

            # get all the associated episode objects
            epObjList = []
            for curEp in parse_result.episode_numbers:
                epObjList.append(result.extraInfo[0].getEpisode(season, curEp))

            # make a result
            curResult = classes.NZBDataSearchResult(epObjList)
            curResult.name = newNZB
            curResult.provider = result.provider
            curResult.quality = result.quality
            curResult.extraInfo = [nzbSplitter.createNZBString(separateNZBs[newNZB], xmlns)]

            resultList.append(curResult)

    return resultList

def _commitSTRM(strmName, strmContents):
    # get the final file path to the strm file
    destinationPath = ek.ek(os.path.join, sickbeard.TV_DOWNLOAD_DIR, strmName)
    helpers.makeDir(destinationPath)
    fileName = ek.ek(os.path.join, destinationPath, strmName + ".strm")

    logger.log(u"Saving STRM to " + fileName)

    # save the data to disk
    try:
        fileOut = open(fileName, "w")
        fileOut.write(strmContents)
        fileOut.close()
        helpers.chmodAsParent(fileName)
        return True
    except IOError, e:
        logger.log(u"Error trying to save STRM to TV downloader directory: "+ex(e), logger.ERROR)
        return False

def saveSTRM(nzb):

    if sickbeard.TV_DOWNLOAD_DIR is None:
        logger.log(u"No TV downloader directory found in configuration. Please configure it.", logger.ERROR)
        return False

    newResult = False

    episodeList = _splitResult(nzb)
    if len(episodeList) > 1:
        for episode in episodeList:
            sickbeard.search._downloadResult(episode)
            fileContents = "plugin://plugin.program.pneumatic/?mode=strm&type=add_file&nzb=" + sickbeard.PNEU_NZB_DIR + episode.name + ".nzb" + "&nzbname=" + episode.name
            newResult = _commitSTRM(episode.name, fileContents)
            nzbProvider = nzb.provider
            if newResult:
                ui.notifications.message('Episode snatched','<b>%s</b> snatched from <b>%s</b>' % (nzb.name, nzbProvider.name))
                newResult = False
    else:
        fileContents = "plugin://plugin.program.pneumatic/?mode=strm&type=add_file&nzb=" + sickbeard.PNEU_NZB_DIR + nzb.name + ".nzb" + "&nzbname=" + nzb.name
        sickbeard.search._downloadResult(nzb)
        newResult = _commitSTRM(nzb.name, fileContents)
        nzbProvider = nzb.provider
        if newResult:
            ui.notifications.message('Episode snatched','<b>%s</b> snatched from <b>%s</b>' % (nzb.name, nzbProvider.name))

    return newResult
