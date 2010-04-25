import os.path
import xml.etree.cElementTree as etree

import tvapi_classes
import safestore, proxy

from sickbeard import logger, common, exceptions
from sickbeard import encodingKludge as ek
from sickbeard import tvclasses

import proxy

import sickbeard

def createTVShow(tvdb_id):
    curShowObj = tvclasses.TVShow.getTVShow(tvdb_id)
    if curShowObj:
        return curShowObj
    
    # make the show
    showObj = proxy._getProxy(sickbeard.storeManager.safe_store(tvclasses.TVShow, tvdb_id))
    sickbeard.storeManager.safe_store("add", showObj.obj)
    sickbeard.storeManager.safe_store("commit")
    
    # get the metadata
    showObj.updateMetadata()
    
    # make a TVEpisode for any tvapi_classes.TVEpisodeData objects that don't already have one
    for epData in safestore.safe_list(sickbeard.storeManager.safe_store("find",
                                                                        tvapi_classes.TVEpisodeData,
                                                                        tvapi_classes.TVEpisodeData.tvdb_show_id == tvdb_id)):

        if not epData.ep_obj:
            logger.log("Creating TVEpisode object for episode "+str(epData.season)+"x"+str(epData.episode), logger.DEBUG)
            epObj = proxy._getProxy(sickbeard.storeManager.safe_store(tvclasses.TVEpisode, showObj))
            sickbeard.storeManager.safe_store(epObj.addEp, ep=epData)
            sickbeard.storeManager.safe_store("add", epObj.obj)
            sickbeard.storeManager.safe_store("flush")
            logger.log("Added a TVEpisode to the TVEpisodeData: "+str(epData._eid)+" == "+str(epObj.eid)+" and "+str(epData.ep_obj)+" == "+str(epObj), logger.DEBUG)
            #store.commit()
    
    #store.add(showObj)
    sickbeard.storeManager.safe_store("commit")
    
    return showObj

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
