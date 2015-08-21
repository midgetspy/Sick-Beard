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
#  GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.

import datetime, time
import generic
import sickbeard

from sickbeard import logger, common, ui
from datetime import timedelta
from time import gmtime

try:
    import json
except ImportError:
    from lib import simplejson as json

class NextPVRProvider(generic.PVRProvider):

    def __init__(self):

        generic.PVRProvider.__init__(self, "NextPVR")
        
        # urls for nextpvr json apis
        self.search_obj_url = '/public/SearchService/Get/SearchObj'
        self.search_url = '/public/SearchService/Search'
        self.schedule_obj_url = '/public/ScheduleService/Get/SchedSettingsObj'
        self.schedule_url = '/public/ScheduleService/Record'
        self.manage_obj_url = '/public/ManageService/Get/RecordingsSortFilterObj'
        self.manage_url = '/public/ManageService/Get/SortedFilteredList'
        self.cancel_recording_url = '/public/ScheduleService/CancelRec'
        self.delete_recording_url = '/public/ScheduleService/CancelDelRec'

        self.supportsBacklog = True
               

    def isEnabled(self):       
        return sickbeard.USE_NEXTPVR
           
    def _get_title_and_url(self, item):
        url = str(item['OID']) # unique identifier for this item
        return (self._getName(item), url)
    
    def _get_season_search_strings(self, show, season, episode=None):
        params = {}
        params['show'] = show
        params['show_name'] = show.name
        params['season'] = season
        
        seasonStr = "s0" if season < 10 else "s"
        seasonStr = seasonStr + str(season)   
    
        params['seasonStr'] = seasonStr    
        params['episodeStr'] = ''
               
        return [params]
    
    def _get_episode_search_strings(self, ep_obj):
        params = self._get_season_search_strings(ep_obj.show, ep_obj.season)

        p = params[0]
        p['episodeStr'] = self._get_episode_string(ep_obj.episode)
        
        return params
    
    def _get_episode_string(self, episode):
            epStr = "e0" if episode < 10 else "e"
            return epStr + str(episode) 
         
    def getQuality(self, item):       
        return self.determineQualityByChannel(int(item['FormattedChannelNumber']))
    
    def _getName(self, item):
        return item['Title'] + '.' + item['Subtitle']
            
    def _doSearch(self, params, show=None):
        logger.log("NEXTPVR PROVIDER: _doSearch called", logger.DEBUG)
        
        results = []
        
        searchObj = self._getEmptyObj(self.search_obj_url)
        
        if not searchObj:
            logger.log(u"No search object returned", logger.ERROR)
            return results
                
        searchObj["searchPhrase"] = params['show_name']
        season = params['season']
        now = datetime.datetime.now()
               
        searchObjJson = json.dumps(searchObj)
        
        data = self.getURL(sickbeard.NEXTPVR_URL + self.search_url, searchObjJson, {'Content-Type': 'application/json'})
        
        allResults = json.loads(data)
        
        scheduledOrRecordedNames, scheduledOrRecordedOids, scheduledOrRecordedStatus, recordedOriginalAirdate = self._getScheduledOrRecordedEps(params['show_name']) # @UnusedVariable
       
        # get air dates since not all subtitles have season.ep
        airDates = self.getAirDates(params['show'], season)
       
        # look through our guide data results
        for result in allResults['SearchResults']['EPGEvents']:
            epgEvent = result['epgEventJSONObject']['epgEvent']
            name = self._getName(epgEvent)
            subtitle = epgEvent['Subtitle']
            originalAirDate = datetime.datetime.strptime(epgEvent['OriginalAirdate'], "%Y-%m-%dT%H:%M:%S").date()
            startTime = self._adjustTimezone(datetime.datetime.strptime(epgEvent['StartTime'], "%Y-%m-%dT%H:%M:%SZ"))
                            
            # see if we want this ep 
            ep = params['seasonStr'] + params['episodeStr']
            if name not in scheduledOrRecordedNames and startTime > now:
                if ep in subtitle:
                    results.append(epgEvent) 
                elif originalAirDate in airDates.values():
                    # need to add season.ep into subtitle so parser can figure out later
                    # there may be multiple episodes with the same date and so lets add them all
                    for e, d in airDates.items():
                        if d == originalAirDate:
                            eStr = self._get_episode_string(e)
                            epgEvent['Subtitle'] = params['seasonStr'] + eStr + "." + subtitle 
                            results.append(epgEvent)
                            break
        
        return results        
    
    def _getScheduledOrRecordedEps(self, title):
        
        # TODO: refactor into array of dicts since I keep adding items to it
        recordedEpNames = []
        recordedEpOids = []
        recordedEpStatus = []
        recordedOriginalAirdate = []
        
        manageObj = self._getEmptyObj(self.manage_obj_url)
        manageObj['Completed'] = True
        manageObj['Pending'] = True
        manageObj['InProgress'] = True
        manageObj['FilterByName'] = True
        manageObj['NameFilter'] = title
        
        manageObjJson = json.dumps(manageObj)
        
        data = self.getURL(sickbeard.NEXTPVR_URL + self.manage_url, manageObjJson, {'Content-Type': 'application/json'})
        allResults = json.loads(data)
        
        for result in allResults['ManageResults']['EPGEvents']:
            epgEvent = result['epgEventJSONObject']['epgEvent']
            schedule = result['epgEventJSONObject']['schd']
            recordedEpNames.append(self._getName(epgEvent))
            recordedEpOids.append(schedule['OID'])
            recordedEpStatus.append(schedule['Status'])
            recordedOriginalAirdate.append(datetime.datetime.strptime(epgEvent['OriginalAirdate'], "%Y-%m-%dT%H:%M:%S").date())
                       
        return recordedEpNames, recordedEpOids, recordedEpStatus, recordedOriginalAirdate
    


        
    def snatchEpisode(self, item):
        logger.log(u"NEXTPVR snatching " + item.name, logger.DEBUG)
        
        snatchStatus = False
        
        scheduleObj = self._getEmptyObj(self.schedule_obj_url)
        
        if not scheduleObj:
            logger.log(u"No schedule object returned", logger.ERROR)
            return snatchStatus
        
        
        scheduleObj['epgeventOID'] = str(item.extraInfo['OID'])
        scheduleObjJson = json.dumps(scheduleObj)
        data = self.getURL(sickbeard.NEXTPVR_URL + self.schedule_url, scheduleObjJson, {'Content-Type': 'application/json'})   
        
        result = json.loads(data)
        epgEvent = result['epgEventJSONObject']['epgEvent']
        
        hasSchedule = bool(epgEvent['HasSchedule'])
        hasConflict = bool(epgEvent['ScheduleHasConflict'])
                        
        if(hasSchedule and not hasConflict):
            schedule = result['epgEventJSONObject']['schd']
            if(schedule['Status'] == 'Pending'):
                msgTitle = u"NEXTPVR successfully scheduled "
                msg = self._getName(epgEvent) + " on channel:" + epgEvent['FormattedChannelNumber']
                ui.notifications.message(msgTitle,msg)
                logger.log(msgTitle + msg, logger.MESSAGE)  
                   
        # TODO: maybe keep separate pvr/dl snatch status           
        # For now always return false so we attempt to dl too           
        return snatchStatus
     
    def postDownloadCleanup(self, ep_obj):
        
        resultMessage = None
        
        if sickbeard.PVR_POST_DOWNLOAD_ACTION == common.PVR_DO_NOTHING:
            return None
        
        params = self._get_episode_search_strings(ep_obj)[0]
        scheduledOrRecordedNames, scheduledOrRecordedOids, scheduledOrRecordedStatus, scheduledOrRecordedOriginalAirdate = self._getScheduledOrRecordedEps(params['show_name'])
        wanted_name = params['show_name'] + '.' + params['seasonStr'] + params['episodeStr']
        
        for name, oid, status, origAirdate in zip(scheduledOrRecordedNames, scheduledOrRecordedOids, scheduledOrRecordedStatus, scheduledOrRecordedOriginalAirdate):
            
            if wanted_name in name or ep_obj.airdate == origAirdate:
                if sickbeard.PVR_POST_DOWNLOAD_ACTION == common.PVR_DELETE_RECORDING and status == 'Completed':
                    url = self.delete_recording_url
                else:
                    url = self.cancel_recording_url
                
                url = sickbeard.NEXTPVR_URL + url + "/" + str(oid)
                
                # nextpvr sets a 404 if it can't find file to delete, this may not be a real error if
                # someone deleted file outside of nextpvr so catch and ignore
                try:
                    data = self.getURL(url)
                except:   
                    logger.log(u"NextPvr could not delete recording of " + name + " but this may not necessarily indicate an error.", logger.WARNING)
                   
                resultMessage = u"NextPvr finished cleanup of " + name   
                
                break
            
        return resultMessage
            
    
    def getRecordingDateTime(self, epgEvent):
        return self._adjustTimezone(datetime.datetime.strptime(epgEvent['StartTime'], "%Y-%m-%dT%H:%M:%SZ"))
    
    def _adjustTimezone(self, dt):
        offset = time.localtime()[3] - gmtime()[3]
        return dt + timedelta(hours=offset)
        
    def _getEmptyObj(self, typeUrl):
        
        # use nextpvr api to retrieve empty json object of specific type with default values
        # to be updated and used in subsequent call
        
        emptyObj = None
        
        data = self.getURL(sickbeard.NEXTPVR_URL + typeUrl)
        
        if not data:
            logger.log(u"No data returned from " + typeUrl, logger.ERROR)
        else:    
            emptyObj = json.loads(data) 
            
        return emptyObj
            
provider = NextPVRProvider()
        