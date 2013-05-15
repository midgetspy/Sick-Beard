# -*- coding: utf-8 -*-
# Copyright 2012 Mr_Orange <mr_orange@hotmail.it>
#
# This file is part of subliminal.
#
# subliminal is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# subliminal is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with subliminal.  If not, see <http://www.gnu.org/licenses/>.
from . import ServiceBase
from ..cache import cachedmethod
from ..language import language_set, Language
from ..subtitles import get_subtitle_path, ResultSubtitle
from ..utils import get_keywords
from ..videos import Episode
from bs4 import BeautifulSoup
import logging
import re
import requests

from sickbeard.common import Quality

logger = logging.getLogger("subliminal")


class Itasa(ServiceBase):
    server_url = 'http://www.italiansubs.net/'
    site_url = 'http://www.italiansubs.net/'
    api_based = False
    languages = language_set(['it'])
    videos = [Episode]
    require_video = False
    required_features = ['permissive']
    quality_dict = {Quality.SDTV : '',
                    Quality.SDDVD : 'dvdrip',
                    Quality.RAWHDTV : '1080i',
                    Quality.HDTV : '720p',                    
                    Quality.FULLHDTV : '720p',
                    Quality.HDWEBDL :  'web-dl',
                    Quality.FULLHDWEBDL : 'web-dl',
                    Quality.HDBLURAY  : 'bluray',
                    Quality.FULLHDBLURAY  : 'bluray'
                    }
    
    def init(self):
       
        super(Itasa, self).init()
        username = 'sickbeard'
        password = 'subliminal'
        login_pattern = '<input type="hidden" name="return" value="([^\n\r\t ]+?)" /><input type="hidden" name="([^\n\r\t ]+?)" value="([^\n\r\t ]+?)" />'

        response = requests.get(self.server_url + 'index.php')
        if response.status_code != 200:
            raise ServiceError('Initiate failed')
        
        match = re.search(login_pattern, response.content, re.IGNORECASE | re.DOTALL)
        if not match:
            raise ServiceError('Can not find unique id parameter on page')
        
        log_parameter = {'username': 'mr_orange',
                         'passwd': '121176',
                         'remember': 'yes',
                         'Submit': 'Login',
                         'remember': 'yes',
                         'option': 'com_user',
                         'task': 'login',
                         'silent': 'true',
                         'return': match.group(1), match.group(2): match.group(3)
                         }

        self.session = requests.session()
        r = self.session.post(self.server_url + 'index.php', data=log_parameter)
        if not re.search('logouticon.png', r.content, re.IGNORECASE | re.DOTALL):
            raise ServiceError('Itasa Login Failed')
        
    @cachedmethod
    def get_series_id(self, name):
        """Get the show page and cache every show found in it"""
        r = self.session.get(self.server_url + 'index.php?option=com_remository&Itemid=9')
        soup = BeautifulSoup(r.content, self.required_features)
        all_series = soup.find('div', attrs = {'id' : 'remositorycontainerlist'})
        for tv_series in all_series.find_all(href=re.compile('func=select')):
            series_name = tv_series.text.lower().strip()
            match = re.search('&id=([0-9]+)', tv_series['href'])
            if match is None:
                continue
            series_id = int(match.group(1))
            self.cache_for(self.get_series_id, args=(series_name,), result=series_id)
        return self.cached_value(self.get_series_id, args=(name,))
    
    def get_episode_id(self, series, series_id, season, episode, quality):
        """Get the episode subtitle with the given quality"""

        season_link = None
        quality_link = None
        episode_id = None

        r = self.session.get(self.server_url + 'index.php?option=com_remository&Itemid=6&func=select&id=' + str(series_id))
        soup = BeautifulSoup(r.content, self.required_features)
        all_seasons = soup.find('div', attrs = {'id' : 'remositorycontainerlist'})
        for seasons in all_seasons.find_all(href=re.compile('func=select')):
            if seasons.text.lower().strip() == 'stagione %s' % str(season):
                season_link = seasons['href']
                break
        
        if not season_link:
            logger.debug(u'Could not find season %s for series %s' % (series, str(season)))
            return None
        
        r = self.session.get(season_link)
        soup = BeautifulSoup(r.content, self.required_features)
        
        all_qualities = soup.find('div', attrs = {'id' : 'remositorycontainerlist'})
        for qualities in all_qualities.find_all(href=re.compile('func=select')):
            if qualities.text.lower().strip() == self.quality_dict[quality]:
                quality_link = qualities['href']
                r = self.session.get(qualities['href'])
                soup = BeautifulSoup(r.content, self.required_features)
                break
                
        if not quality == Quality.SDTV and not quality_link:
            logger.debug(u'Could not find a subtitle with required quality for series %s season %s' % (series, str(season)))
            return None
        
        all_episodes = soup.find('div', attrs = {'id' : 'remositoryfilelisting'})
        for episodes in all_episodes.find_all(href=re.compile('func=fileinfo')):
            ep_string = "%(seasonnumber)dx%(episodenumber)02d" % {'seasonnumber': season, 'episodenumber': episode}
            if re.search(ep_string, episodes.text):
                match = re.search('&id=([0-9]+)', episodes['href'])
                if match:
                    episode_id = match.group(1)
                    return episode_id
                
        return episode_id
 
    def list_checked(self, video, languages):
        return self.query(video.path or video.release, languages, get_keywords(video.guess), video.series, video.season, video.episode)
            
    def query(self, filepath, languages, keywords, series, season, episode):

        logger.debug(u'Getting subtitles for %s season %d episode %d with languages %r' % (series, season, episode, languages))
        self.init_cache()
        try:
            series_id = self.get_series_id(series.lower())
        except KeyError:
            logger.debug(u'Could not find series id for %s' % series)
            return []
        
        episode_id = self.get_episode_id(series.lower(), series_id, season, episode, Quality.nameQuality(filepath))
        if not episode_id:
            logger.debug(u'Could not find subtitle for series %s' % series)
            return []

        r = self.session.get(self.server_url + 'index.php?option=com_remository&Itemid=6&func=fileinfo&id=' + episode_id)
        soup = BeautifulSoup(r.content)

        sub_link = soup.find('div', attrs = {'id' : 'remositoryfileinfo'}).find(href=re.compile('func=download'))['href']
        sub_language = self.get_language('it')
        path = get_subtitle_path(filepath, sub_language, self.config.multi)
        subtitle = ResultSubtitle(path, sub_language, self.__class__.__name__.lower(), sub_link)
        
        return [subtitle]

    def download(self, subtitle):
        self.download_zip_file(subtitle.link, subtitle.path)
        return subtitle


Service = Itasa        