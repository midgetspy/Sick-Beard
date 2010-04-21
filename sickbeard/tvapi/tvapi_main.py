import os.path
import xml.etree.cElementTree as etree

from tvapi_classes import TVShowData, TVEpisodeData
import safestore, proxy

from sickbeard import logger, common, exceptions
from sickbeard import encodingKludge as ek

from sickbeard.tvclasses import TVShow, TVEpisode

import proxy

import sickbeard

from lib.tvnamer.utils import FileParser
from lib.tvnamer import tvnamer_exceptions

def findTVShow(name):
    result = sickbeard.storeManager.safe_store("find", TVShow, TVShow.tvdb_id == TVShowData.tvdb_id, TVShowData.name == name)
    return proxy._getProxy(sickbeard.storeManager.safe_store(result.one))

def getTVShow(tvdb_id):
    result = sickbeard.storeManager.safe_store("find", TVShow, TVShow.tvdb_id == tvdb_id)
    return proxy._getProxy(sickbeard.storeManager.safe_store(result.one))

def createTVShow(tvdb_id):
    curShowObj = getTVShow(tvdb_id)
    if curShowObj:
        return curShowObj
    
    # make the show
    showObj = proxy._getProxy(sickbeard.storeManager.safe_store(TVShow, tvdb_id))
    sickbeard.storeManager.safe_store("add", showObj.obj)
    sickbeard.storeManager.safe_store("commit")
    
    # get the metadata
    showObj.updateMetadata()
    
    # make a TVEpisode for any TVEpisodeData objects that don't already have one
    for epData in safestore.safe_list(sickbeard.storeManager.safe_store("find",
                                                                        TVEpisodeData,
                                                                        TVEpisodeData.tvdb_show_id == tvdb_id)):
        if not epData.ep_obj:
            epObj = proxy._getProxy(sickbeard.storeManager.safe_store(TVEpisode, showObj))
            sickbeard.storeManager.safe_store(epObj.addEp, ep=epData)
            sickbeard.storeManager.safe_store("add", epObj.obj)
            #store.commit()
    
    #store.add(showObj)
    sickbeard.storeManager.safe_store("commit")
    
    return showObj

def createEpFromName(name, tvdb_id=None):
    
    try:
        myParser = FileParser(name)
        epInfo = myParser.parse()
    except tvnamer_exceptions.InvalidFilename:
        #logger.log("Unable to parse the filename "+name+" into a valid episode", logger.ERROR)
        return None

    if not tvdb_id:
        # try looking the name up in the DB
        
        # if that fails try a TVDB lookup
        pass
    
    showObj = getTVShow(tvdb_id)
    epObj = showObj.getEp(epInfo.seasonnumber, epInfo.episodenumbers[0])
    
    if epObj:
        for anotherEpNum in epInfo.episodenumbers[1:]:
            epObj.addEp(epInfo.seasonnumber, anotherEpNum)
    
        if os.path.isfile(name):
            epObj.location = name
    
    return epObj


def TEMP_getTVDBIDFromNFO(dir):

    if not ek.ek(os.path.isdir, dir):
        logger.log("Show dir doesn't exist, can't load NFO")
        raise exceptions.NoNFOException("The show dir doesn't exist, no NFO could be loaded")
    
    logger.log("Loading show info from NFO")

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
        logger.log("There was an error parsing your existing tvshow.nfo file: " + str(e), logger.ERROR)
        logger.log("Attempting to rename it to tvshow.nfo.old", logger.DEBUG)

        try:
            xmlFileObj.close()
            ek.ek(os.rename, xmlFile, xmlFile + ".old")
        except Exception, e:
            logger.log("Failed to rename your tvshow.nfo file - you need to delete it or fix it: " + str(e), logger.ERROR)
        raise exceptions.NoNFOException("Invalid info in tvshow.nfo")

    return tvdb_id
