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

import urllib

import sickbeard
from sickbeard.metadata import helpers

from sickbeard.common import *
from sickbeard import logger, exceptions
from sickbeard import encodingKludge as ek

from lib.tvdb_api import tvdb_api, tvdb_exceptions

def save_thumbnail(ep_obj, file_path):

    all_eps = [ep_obj] + ep_obj.relatedEps

    # get a TVDB object
    try:
        t = tvdb_api.Tvdb(actors=True, **sickbeard.TVDB_API_PARMS)
        tvdb_show_obj = t[ep_obj.show.tvdbid]
    except tvdb_exceptions.tvdb_shownotfound, e:
        raise exceptions.ShowNotFoundException(str(e))
    except tvdb_exceptions.tvdb_error, e:
        logger.log(u"Unable to connect to TVDB while creating meta files - skipping - "+str(e).decode('utf-8'), logger.ERROR)
        return

    # try all included episodes in case some have thumbs and others don't
    for cur_ep in all_eps:
        try:
            myEp = tvdb_show_obj[ep_obj.season][ep_obj.episode]
        except (tvdb_exceptions.tvdb_episodenotfound, tvdb_exceptions.tvdb_seasonnotfound):
            logger.log(u"Unable to find episode " + str(ep_obj.season) + "x" + str(ep_obj.episode) + " on tvdb... has it been removed? Should I delete from db?")
            return False

        thumb_url = myEp["filename"]
        
        if thumb_url:
            break

    # if we can't find one then give up
    if not thumb_url:
        logger.log("No thumb is available for this episode, not creating a thumb", logger.DEBUG)
        return False
    
    logger.log('Writing thumb to ' + file_path)
    try:
        ek.ek(urllib.urlretrieve, thumb_url, file_path)
    except IOError:
        logger.log(u"Unable to download thumbnail from "+thumb_url, logger.ERROR)
        return False

    #TODO: check that it worked
    
    for cur_ep in all_eps:
        cur_ep.hastbn = True

    return True

# originally written by matt schick
def save_poster(show_obj, file_path, which=None):

    try:
        t = tvdb_api.Tvdb(banners=True, **sickbeard.TVDB_API_PARMS)
        tvdb_show_obj = t[show_obj.tvdbid]
    except (tvdb_exceptions.tvdb_error, IOError), e:
        logger.log(u"Unable to look up show on TVDB, not downloading images: "+str(e).decode('utf-8'), logger.ERROR)
        return False

    poster_url = tvdb_show_obj['poster']

    # get the image data
    if ek.ek(os.path.isfile, file_path):
        logger.log("Poster already exists, not downloading", logger.DEBUG)
        return False
        
    posterData = None
    if which != None:
        posterData = helpers.getShowImage(poster_url, which)

    # if we had a custom image number that failed OR we had no custom number then get the default one
    if posterData == None:
        posterData = helpers.getShowImage(poster_url)

    if posterData == None:
        logger.log(u"Unable to retrieve poster, skipping", logger.WARNING)
        return False
    else:
        try:
            outFile = ek.ek(open, file_path, 'wb')
            outFile.write(posterData)
            outFile.close()
        except IOError, e:
            logger.log(u"Unable to write poster to "+file_path+" - are you sure the show folder is writable? "+str(e).decode('utf-8'), logger.ERROR)

    return True

# originally written by matt schick
def save_fanart(show_obj, file_path, which=None):

    try:
        t = tvdb_api.Tvdb(banners=True, **sickbeard.TVDB_API_PARMS)
        tvdb_show_obj = t[show_obj.tvdbid]
    except (tvdb_exceptions.tvdb_error, IOError), e:
        logger.log(u"Unable to look up show on TVDB, not downloading images: "+str(e).decode('utf-8'), logger.ERROR)
        return False

    fanart_url = tvdb_show_obj['fanart']

    # get the image data
    if ek.ek(os.path.isfile, file_path):
        logger.log("Fanart already exists, not downloading", logger.DEBUG)
        return False
        
    # get the image data
    fanartData = None
    if which  != None:
        fanartData = helpers.getShowImage(fanart_url, which)

    # if we had a custom image number that failed OR we had no custom number then get the default one
    if fanartData == None:
        fanartData = helpers.getShowImage(fanart_url)

    if fanartData == None:
        logger.log(u"Unable to retrieve fanart, skipping", logger.WARNING)
        return False
    else:
        try:
            outFile = ek.ek(open, file_path, 'wb')
            outFile.write(fanartData)
            outFile.close()
        except IOError, e:
            logger.log(u"Unable to write fanart to "+file_path+" - are you sure the show folder is writable? "+str(e).decode('utf-8'), logger.ERROR)

    return True

# originally written by matt schick
def save_season_thumbs(show_obj, root_path):

    try:
        t = tvdb_api.Tvdb(banners=True, **sickbeard.TVDB_API_PARMS)
        tvdb_show_obj = t[show_obj.tvdbid]
    except (tvdb_exceptions.tvdb_error, IOError), e:
        logger.log(u"Unable to look up show on TVDB, not downloading images: "+str(e).decode('utf-8'), logger.ERROR)
        return False

    seasonData = None
    #  How many seasons?
    numOfSeasons = len(tvdb_show_obj)

    # if we have no season banners then just finish
    if 'season' not in tvdb_show_obj['_banners'] or 'season' not in tvdb_show_obj['_banners']['season']:
        return False

    # Give us just the normal poster-style season graphics
    seasonsArtObj = tvdb_show_obj['_banners']['season']['season']

    # This holds our resulting dictionary of season art
    seasonsDict = {}

    # Returns a nested dictionary of season art with the season
    # number as primary key. It's really overkill but gives the option
    # to present to user via ui to pick down the road.
    for seasonNum in range(numOfSeasons):
        # dumb, but we do have issues with types here so make it
        # strings for now
        seasonNum = str(seasonNum)
        seasonsDict[seasonNum] = {}
        for seasonArtID in seasonsArtObj.keys():
            seasonArtID = str(seasonArtID)
            if seasonsArtObj[seasonArtID]['season'] == seasonNum and seasonsArtObj[seasonArtID]['language'] == 'en':
                seasonsDict[seasonNum][seasonArtID] = seasonsArtObj[seasonArtID]['_bannerpath']
        
        if len(seasonsDict[seasonNum]) == 0:
            continue

        # Just grab whatever's there for now
        season, seasonURL = seasonsDict[seasonNum].popitem()

        # Our specials thumbnail is, well, special
        if seasonNum == '0':
            season_thumb_file_path = 'season-specials'
        else:
            season_thumb_file_path = 'season' + seasonNum.zfill(2)

        # Let's do the check before we pull the file
        if ek.ek(os.path.isfile, ek.ek(os.path.join, root_path, season_thumb_file_path+'.tbn')):
            logger.log(u"Season thumb "+season_thumb_file_path+" already exists, not generating it", logger.DEBUG)
            continue

        seasonData = helpers.getShowImage(seasonURL)

        if seasonData == None:
            logger.log(u"Unable to retrieve season poster, skipping", logger.ERROR)
        else:
            try:
                outFile = ek.ek(open, ek.ek(os.path.join, root_path, season_thumb_file_path+'.tbn'), 'wb')
                outFile.write(seasonData)
                outFile.close()
            except IOError, e:
                logger.log(u"Unable to write fanart - are you sure the show folder is writable? "+str(e).decode('utf-8'), logger.ERROR)

    return True
