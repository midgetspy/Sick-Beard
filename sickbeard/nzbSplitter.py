import urllib

import xml.etree.cElementTree as etree
import xml.etree
import re

from lib.tvnamer.utils import FileParser 
from lib.tvnamer import tvnamer_exceptions

from sickbeard import logger, classes
from sickbeard.common import *

def getSeasonNZBs(name, fileObj, season):

    try:
        showXML = etree.ElementTree(file = fileObj)
    except SyntaxError:
        logger.log("Unable to parse the XML of "+name+", not splitting it", logger.ERROR)
        return ({},'')

    filename = name.replace(".nzb", "")

    nzbElement = showXML.getroot()
    
    regex = '([\w\._\ ]+)[\. ]S%02d[\. ]([\w\._\-\ ]+)[\- ]([\w_\-\ ]+?)' % season
    
    sceneNameMatch = re.search(regex, filename, re.I)
    if sceneNameMatch: 
        showName, qualitySection, groupName = sceneNameMatch.groups()
    else:
        logger.log("Unable to parse "+name+" into a scene name. If it's a valid one log a bug.", logger.ERROR)
        return ({},'')
    
    regex = '(' + re.escape(showName) + '\.S%02d(?:[E0-9]+)\.[\w\._]+\-\w+' % season + ')'
    regex = regex.replace(' ', '.')

    epFiles = {}
    xmlns = None
    
    for curFile in nzbElement.getchildren():
        xmlnsMatch = re.match("\{(http:\/\/[A-Za-z0-9_\.\/]+\/nzb)\}file", curFile.tag)
        if not xmlnsMatch:
            continue
        else:
            xmlns = xmlnsMatch.group(1)
        match = re.search(regex, curFile.get("subject"), re.I)
        if not match:
            #print curFile.get("subject"), "doesn't match", regex
            continue
        curEp = match.group(1)
        if curEp not in epFiles:
            epFiles[curEp] = [curFile]
        else:
            epFiles[curEp].append(curFile)

    return (epFiles, xmlns) 

def createNZBString(fileElements, xmlns):

    rootElement = etree.Element("nzb")
    if xmlns:
        rootElement.set("xmlns", xmlns)
    
    for curFile in fileElements:
        rootElement.append(stripNS(curFile, xmlns))

    return xml.etree.ElementTree.tostring(rootElement, 'utf-8')


def saveNZB(nzbName, nzbString):

    nzb_fh = open(nzbName+".nzb", 'w')
    nzb_fh.write(nzbString)
    nzb_fh.close()

def stripNS(element, ns):
    element.tag = element.tag.replace("{"+ns+"}", "")
    for curChild in element.getchildren():
        stripNS(curChild, ns)
    
    return element


def splitResult(result):
    
    fileObj = urllib.urlopen(result.url)
    
    # parse the season ep name
    try:
        fp = FileParser(result.name)
        epInfo = fp.parse()
    except tvnamer_exceptions.InvalidFilename:
        logger.log("Unable to parse the filename "+result.name+" into a valid episode", logger.WARNING)
        return False

    # bust it up
    season = epInfo.seasonnumber
    separateNZBs, xmlns = getSeasonNZBs(result.name, fileObj, season)

    resultList = []
    
    for newNZB in separateNZBs:

        logger.log("Split out "+newNZB+" from "+result.name, logger.DEBUG)

        # parse the name
        try:
            fp = FileParser(newNZB)
            epInfo = fp.parse()
        except tvnamer_exceptions.InvalidFilename:
            logger.log("Unable to parse the filename "+newNZB+" into a valid episode", logger.WARNING)
            return False

        # make sure the result is sane
        if epInfo.seasonnumber != season:
            logger.log("Found "+newNZB+" inside "+result.name+" but it doesn't seem to belong to the same season, ignoring it", logger.WARNING)
            continue
        elif len(epInfo.episodenumbers) == 0:
            logger.log("Found "+newNZB+" inside "+result.name+" but it doesn't seem to be a valid episode NZB, ignoring it", logger.WARNING)
            continue

        wantEp = True
        for epNo in epInfo.episodenumbers:
            if epNo == -1:
                continue
            if not result.extraInfo[0].wantEpisode(season, epNo, result.quality):
                logger.log("Ignoring result "+newNZB+" because we don't want an episode that is "+Quality.qualityStrings[result.quality], logger.DEBUG)
                wantEp = False
                break
        if not wantEp:
            continue

        # get all the associated episode objects
        epObjList = []
        for curEp in epInfo.episodenumbers:
            epObjList.append(result.extraInfo[0].getEpisode(season, curEp))

        # make a result
        curResult = classes.NZBDataSearchResult(epObjList)
        curResult.name = newNZB
        curResult.provider = result.provider
        curResult.quality = result.quality
        curResult.extraInfo = [createNZBString(separateNZBs[newNZB], xmlns)]

        resultList.append(curResult)

    return resultList