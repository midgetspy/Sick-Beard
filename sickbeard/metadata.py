import os
import os.path

import sickbeard

from sickbeard import logger, exceptions
from sickbeard import encodingKludge as ek

import xml.etree.cElementTree as etree

from sickbeard import helpers


def makeShowNFO(showObj):
    
    tvNode = etree.Element( "tvshowObj" )
    for ns in sickbeard.XML_NSMAP.keys():
        tvNode.set(ns, sickbeard.XML_NSMAP[ns])

    title = etree.SubElement( tvNode, "title" )
    if showObj.show_data.name != None:
        title.text = showObj.show_data.name
        
    rating = etree.SubElement( tvNode, "rating" )
    if showObj.show_data.rating != None:
        rating.text = str(showObj.show_data.rating)

    plot = etree.SubElement( tvNode, "plot" )
    if showObj.show_data.plot != None:
        plot.text = showObj.show_data.plot

    episodeguideurl = etree.SubElement( tvNode, "episodeguideurl" )
    episodeguide = etree.SubElement( tvNode, "episodeguide" )
    if showObj.tvdb_id != None:
        showObjurl = sickbeard.TVDB_BASE_URL + '/series/' + str(showObj.tvdb_id) + '/all/en.zip'
        episodeguideurl.text = showObjurl
        episodeguide.text = showObjurl
        
    mpaa = etree.SubElement( tvNode, "mpaa" )
    if showObj.show_data.contentrating != None:
        mpaa.text = showObj.show_data.contentrating

    tvdbid = etree.SubElement( tvNode, "id" )
    if showObj.tvdb_id != None:
        tvdbid.text = str(showObj.tvdb_id)
        
    genre = etree.SubElement( tvNode, "genre" )
    if showObj.show_data._genres != None:
        genre.text = " / ".join(showObj.show_data._genres)
        
    premiered = etree.SubElement( tvNode, "premiered" )
    if showObj.show_data.firstaired != None:
        premiered.text = str(showObj.show_data.firstaired)
        
    studio = etree.SubElement( tvNode, "studio" )
    if showObj.show_data.network != None:
        studio.text = showObj.show_data.network

    for actor in showObj.show_data.actors:

        cur_actor = etree.SubElement( tvNode, "actor" )

        cur_actor_name = etree.SubElement( cur_actor, "name" )
        cur_actor_name.text = actor['name']
        cur_actor_role = etree.SubElement( cur_actor, "role" )
        cur_actor_role_text = actor['role']

        if cur_actor_role_text != None:
            cur_actor_role.text = cur_actor_role_text

        cur_actor_thumb = etree.SubElement( cur_actor, "thumb" )
        cur_actor_thumb_text = actor['image']

        if cur_actor_thumb_text != None:
            cur_actor_thumb.text = cur_actor_thumb_text

    # Make it purdy
    #helpers.indentXML( tvNode )

    return tvNode

def makeEpNFO(ep):

    episode = etree.Element( "episodedetails" )

    title = etree.SubElement( episode, "title" )
    title.text = ep.name if ep.name else None

    season = etree.SubElement( episode, "season" )
    season.text = str(ep.season)

    episodenum = etree.SubElement( episode, "episode" )
    episodenum.text = str(ep.episode)
    
    aired = etree.SubElement( episode, "aired" )
    aired.text = str(ep.aired)

    plot = etree.SubElement( episode, "plot" )
    plot.text = ep.description if ep.description else None

    displayseason = etree.SubElement( episode, "displayseason" )
    displayseason.text = str(ep.displayseason) if ep.displayseason else None

    displayepisode = etree.SubElement( episode, "displayepisode" )
    displayepisode.text = str(ep.displayepisode) if ep.displayepisode else None

    thumb = etree.SubElement( episode, "thumb" )
    thumb.text = ep.thumb if ep.thumb else None

    watched = etree.SubElement( episode, "watched" )
    watched.text = 'false'

    credits = etree.SubElement( episode, "credits" )
    credits.text = ep.writer if ep.writer else None

    director = etree.SubElement( episode, "director" )
    director.text = ep.director if ep.director else None

    for actor in ep.gueststars:
        cur_actor = etree.SubElement( episode, "actor" )
        cur_actor_name = etree.SubElement( cur_actor, "name" )
        cur_actor_name.text = actor

    for actor in ep.show_data.actors:

        cur_actor = etree.SubElement( episode, "actor" )

        cur_actor_name = etree.SubElement( cur_actor, "name" )
        cur_actor_name.text = actor['name']
        cur_actor_role = etree.SubElement( cur_actor, "role" )
        cur_actor_role_text = actor['role']

        if cur_actor_role_text != None:
            cur_actor_role.text = cur_actor_role_text

        cur_actor_thumb = etree.SubElement( cur_actor, "thumb" )
        cur_actor_thumb_text = actor['image']

        if cur_actor_thumb_text != None:
            cur_actor_thumb.text = cur_actor_thumb_text

    # Make it purdy
    helpers.indentXML( episode )

    return episode

def getTVDBIDFromNFO(dir):
    """
    Parses a tvshow.nfo file and attempts to read the TVDB ID from it. If it can't figure out
    the ID then it renames the tvshow.nfo to tvshow.nfo.old and raises a NoNFOException.
    """

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
