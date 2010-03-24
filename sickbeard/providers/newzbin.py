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



import os.path
import re
import sys
import time
import urllib

import sickbeard

from sickbeard import exceptions, helpers, classes
from sickbeard.common import *
from sickbeard import logger

providerType = "nzb"
providerName = "Newzbin"

def isActive():
	return sickbeard.NEWZBIN and sickbeard.USE_NZB

class NewzbinDownloader(urllib.FancyURLopener):

	def __init__(self):
		urllib.FancyURLopener.__init__(self)
	
	def http_error_default(self, url, fp, errcode, errmsg, headers):
	
		# if newzbin is throttling us, wait 61 seconds and try again
		if errcode == 400:
		
			newzbinErrCode = int(headers.getheader('X-DNZB-RCode'))
		
			if newzbinErrCode == 450:
				rtext = str(headers.getheader('X-DNZB-RText'))
				result = re.search("wait (\d+) seconds", rtext)

			elif newzbinErrCode == 401:
				raise exceptions.AuthException("Newzbin username or password incorrect")
	
			elif newzbinErrCode == 402:
				raise exceptions.AuthException("Newzbin account not premium status, can't download NZBs")

				
			logger.log("Newzbin throttled our NZB downloading, pausing for " + result.group(1) + "seconds")
			
			time.sleep(int(result.group(1)))
		
			raise exceptions.NewzbinAPIThrottled()
		
def downloadNZB(nzb):

	logger.log("Downloading an NZB from newzbin at " + nzb.url)

	fileName = os.path.join(sickbeard.NZB_DIR, helpers.sanitizeFileName(nzb.fileName()))
	logger.log("Saving to " + fileName, logger.DEBUG)

	urllib._urlopener = NewzbinDownloader()

	params = urllib.urlencode({"username": sickbeard.NEWZBIN_USERNAME, "password": sickbeard.NEWZBIN_PASSWORD, "reportid": nzb.extraInfo[0]})
	try:
		urllib.urlretrieve("http://v3.newzbin.com/api/dnzb/", fileName, data=params)
	except exceptions.NewzbinAPIThrottled:
		logger.log("Done waiting for Newzbin API throttle limit, starting downloads again")
		downloadNZB(nzb)
	except (urllib.ContentTooShortError, IOError), e:
		logger.log("Error downloading NZB: " + str(sys.exc_info()) + " - " + str(e), logger.ERROR)
		return False
	
	#TODO: check for throttling, wait if needed

	return True
		
def findEpisode(episode, forceQuality=None):

	logger.log("Searching newzbin for " + episode.prettyName(True))

	if forceQuality != None:
		epQuality = forceQuality
	elif episode.show.quality == BEST:
		epQuality = ANY
	else:
		epQuality = episode.show.quality
		
	if epQuality == SD:
		qualAttrs = "(Attr:VideoF~XviD OR Attr:VideoF~DivX) NOT Attr:VideoF~720p NOT Attr:VideoF~1080p "
		# don't allow subtitles for SD content cause they'll probably be hard subs
		qualAttrs += "NOT (Attr:SubtitledLanguage~French OR Attr:SubtitledLanguage~Spanish OR Attr:SubtitledLanguage~German OR Attr:SubtitledLanguage~Italian OR Attr:SubtitledLanguage~Danish OR Attr:SubtitledLanguage~Dutch OR Attr:SubtitledLanguage~Japanese OR Attr:SubtitledLanguage~Chinese OR Attr:SubtitledLanguage~Korean OR Attr:SubtitledLanguage~Russian OR Attr:SubtitledLanguage~Polish OR Attr:SubtitledLanguage~Vietnamese OR Attr:SubtitledLanguage~Swedish OR Attr:SubtitledLanguage~Norwegian OR Attr:SubtitledLanguage~Finnish OR Attr:SubtitledLanguage~Turkish) "
	elif epQuality == HD:
		qualAttrs = "(Attr:VideoF~x264 OR Attr:VideoF~H.264) Attr:VideoF~720p "
	else:
		qualAttrs = "(Attr:VideoF~x264 OR Attr:VideoF~H.264 OR Attr:VideoF~XviD OR Attr:VideoF~DivX) "

	# require english for now
	qualAttrs += "Attr:Lang=Eng "

	# if it's in the disc backlog then limit the results to disc sources only 
	if episode.status == DISCBACKLOG:
		qualAttrs += "(Attr:VideoS=DVD OR Attr:VideoS=Blu OR Attr:VideoS=HD-DVD) "

	# this will be a list containing:
	# - tvdb name
	# - forced sick beard exceptions
	# - tvrage name
	# - country coded name if applicable
	showNames = helpers.allPossibleShowNames(episode.show)

	# these shouldn't be required now that we use TVRage names
	if episode.show.tvrname == None or episode.show.tvrname == "":
		if " and " in episode.show.name:
			showNames.append(episode.show.name.replace("and", "&"))
		if " & " in episode.show.name:
			showNames.append(episode.show.name.replace("&", "and"))

	# I guess using tvrage name doesn't negate the need for this case
	if episode.show.startyear > 1900 and not episode.show.name.endswith(")"):
		showNames.append(episode.show.name + " ("+str(episode.show.startyear)+")")

	# this strips the (XX) off the end of the show. we shouldn't need it anymore with the tvrage names
	#regex = "(.*)( \(.*\))"
	#result = re.match(regex, episode.show.name)
	#if result != None and result.group(2) != None:
	#	showNames += [episode.show.name.replace(result.group(2), "")]
		
	q = qualAttrs
	
	q += "(" + " OR ".join(["^\""+x+" - %ix%02i" % (int(episode.season), int(episode.episode))+"\"" for x in set(showNames)]) + ")"
	
	q += " AND NOT \"(Passworded)\" AND NOT \"(Password)\""
	
	newzbinURL = {
				  'hauth': 1,
				  'q': q.encode('utf-8'),
    		      'searchaction': 'Search',
        		  'fpn': 'p',
                  'category': 8,
                  'area':-1,
                  'u_nfo_posts_only': 0,
                  'u_url_posts_only': 0,
                  'u_comment_posts_only': 0,
                  'sort': 'ps_edit_date',
                  'order': 'desc',
                  'areadone':-1,
                  'feed': 'csv',
                  'u_v3_retention': sickbeard.USENET_RETENTION * 24 * 60 * 60}

	myOpener = classes.AuthURLOpener(sickbeard.NEWZBIN_USERNAME, sickbeard.NEWZBIN_PASSWORD)
	searchStr = "http://v3.newzbin.com/search/?%s" % urllib.urlencode(newzbinURL)
	logger.log("Search string: " + searchStr, logger.DEBUG)
	try:
		f = myOpener.openit(searchStr)
	except (urllib.ContentTooShortError, IOError), e:
		logger.log("Error loading search results: " + str(sys.exc_info()) + " - " + str(e), logger.ERROR)
		return []
	rawResults = [[y.strip("\"") for y in x.split(",")] for x in f.readlines()]
	
	#TODO: check for throttling, wait
	
	results = []
	
	logger.log("rawResults: " + str(rawResults), logger.DEBUG)
	
	for curResult in rawResults:
		
		if type(curResult) != list:
			continue

		if len(curResult) == 1:
			if curResult[0] == 'Error: Login Required - You need to login to access this feed.':
				raise exceptions.AuthException("Incorrect username/password for Newzbin")
			else:
				logger.log("Newzbin returned a malformed result, skipping it", logger.ERROR)
			continue
		
		if len(curResult) < 6:
			logger.log("Unknown error with Newzbin search, skipping this result", logger.ERROR)
			continue
		
		logger.log("Found report number " + str(curResult[2]) + " at " + curResult[4] + " (" + curResult[5] + ")")
		
		result = sickbeard.classes.NZBSearchResult(episode)
		result.provider = 'newzbin'
		result.url = curResult[4]
		result.extraInfo = [curResult[2], curResult[5]]
		result.quality = epQuality
		
		results.append(result)
	
	return results


def findPropers(date=None):
	return []