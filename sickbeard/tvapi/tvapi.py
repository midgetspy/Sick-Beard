import os.path
import xml.etree.cElementTree as etree

from storm.locals import Store

from tvapi_classes import TVShowData, TVEpisodeData

from sickbeard import logger, common, exceptions
from sickbeard import encodingKludge as ek
from sickbeard import tvapi

from sickbeard.tvclasses import TVShow, TVEpisode

from lib.tvnamer.utils import FileParser
from lib.tvnamer import tvnamer_exceptions

def findTVShow(name):
    store = Store(tvapi.database)
    return store.find(TVShow, TVShow.tvdb_id == TVShowData.tvdb_id, TVShowData.name == name).one()

def getTVShow(tvdb_id):
    store = Store(tvapi.database)
    result = store.find(TVShow, TVShow.tvdb_id == tvdb_id)
    return result.one()

def createTVShow(tvdb_id):
    curShowObj = getTVShow(tvdb_id)
    if curShowObj:
        return curShowObj
    
    store = Store(tvapi.database)

    # make the show
    showObj = TVShow(tvdb_id)
    store.add(showObj)
    store.commit()
    
    # get the metadata
    showObj.update()
    
    # make a TVEpisode for any TVEpisodeData objects that don't already have one
    for epData in store.find(TVEpisodeData, TVEpisodeData.show_id == tvdb_id):
        if not epData.ep_obj:
            epObj = TVEpisode(showObj)
            epObj.addEp(ep=epData)
            #store.add(epObj)
            #store.commit()
    
    #store.add(showObj)
    store.commit()
    
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

    if not os.path.isdir(dir):
        logger.log("Show dir doesn't exist, can't load NFO")
        raise exceptions.NoNFOException("The show dir doesn't exist, no NFO could be loaded")
    
    logger.log("Loading show info from NFO")

    xmlFile = os.path.join(dir, "tvshow.nfo")
    
    try:
        xmlFileObj = open(xmlFile, 'r')
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
