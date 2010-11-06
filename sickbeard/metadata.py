import os
import os.path

import sickbeard

from sickbeard.common import *
from sickbeard import logger, exceptions, helpers
from sickbeard import encodingKludge as ek

import xml.etree.cElementTree as etree

from lib.tvdb_api import tvdb_api, tvdb_exceptions

def makeShowNFO(showID):

    t = tvdb_api.Tvdb(actors=True, **sickbeard.TVDB_API_PARMS)

    tvNode = etree.Element( "tvshow" )
    for ns in XML_NSMAP.keys():
        tvNode.set(ns, XML_NSMAP[ns])

    try:
        myShow = t[int(showID)]
    except tvdb_exceptions.tvdb_shownotfound:
        logger.log(u"Unable to find show with id " + str(showID) + " on tvdb, skipping it", logger.ERROR)
        raise

    except tvdb_exceptions.tvdb_error:
        logger.log(u"TVDB is down, can't use its data to add this show", logger.ERROR)
        raise

    # check for title and id
    try:
        if myShow["seriesname"] == None or myShow["seriesname"] == "" or myShow["id"] == None or myShow["id"] == "":
            logger.log(u"Incomplete info for show with id " + str(showID) + " on tvdb, skipping it", logger.ERROR)

            return False
    except tvdb_exceptions.tvdb_attributenotfound:
        logger.log(u"Incomplete info for show with id " + str(showID) + " on tvdb, skipping it", logger.ERROR)

        return False

    title = etree.SubElement( tvNode, "title" )
    if myShow["seriesname"] != None:
        title.text = myShow["seriesname"]

    rating = etree.SubElement( tvNode, "rating" )
    if myShow["rating"] != None:
        rating.text = myShow["rating"]

    plot = etree.SubElement( tvNode, "plot" )
    if myShow["overview"] != None:
        plot.text = myShow["overview"]

    episodeguide = etree.SubElement( tvNode, "episodeguide" )
    episodeguideurl = etree.SubElement( episodeguide, "url" )
    episodeguideurl2 = etree.SubElement( tvNode, "episodeguideurl" )
    if myShow["id"] != None:
        showurl = sickbeard.TVDB_BASE_URL + '/series/' + myShow["id"] + '/all/en.zip'
        episodeguideurl.text = showurl
        episodeguideurl2.text = showurl

    mpaa = etree.SubElement( tvNode, "mpaa" )
    if myShow["contentrating"] != None:
        mpaa.text = myShow["contentrating"]

    tvdbid = etree.SubElement( tvNode, "id" )
    if myShow["id"] != None:
        tvdbid.text = myShow["id"]

    genre = etree.SubElement( tvNode, "genre" )
    if myShow["genre"] != None:
        genre.text = " / ".join([x for x in myShow["genre"].split('|') if x])

    premiered = etree.SubElement( tvNode, "premiered" )
    if myShow["firstaired"] != None:
        premiered.text = myShow["firstaired"]

    studio = etree.SubElement( tvNode, "studio" )
    if myShow["network"] != None:
        studio.text = myShow["network"]

    for actor in myShow['_actors']:

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

    return tvNode


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