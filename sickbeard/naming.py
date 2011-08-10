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
#  GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.

from sickbeard import tv

from common import Quality, DOWNLOADED

dir_presets = ('Season %0S',
               '%RN',
               )

name_presets = ('%SN - %Sx%0E - %EN',
                '%S.N.S%0SE%0E.%E.N',
                '%Sx%0E - %EN',
                'S%0SE%0E - %EN')

def test_name(pattern, multi=False):

    class TVShow():
        def __init__(self):
            self.name = "Show Name"
            self.genre = "Comedy"
            self.air_by_date = 0

    # fake a TVShow (hack since new TVShow is coming anyway)
    class TVEpisode(tv.TVEpisode):
        def __init__(self, season, episode, name):
            self.relatedEps = []
            self._name = name
            self._season = season
            self._episode = episode
            self.show = TVShow()
            self._release_name = 'Show.Name.S01E02.HDTV.XviD-RLSGROUP'

    # make a fake episode object
    ep = TVEpisode(1,2,"Ep Name")
    ep._status = Quality.compositeStatus(DOWNLOADED, Quality.HDTV)

    if multi:
        ep._name = "Ep Name (1)"
        secondEp = TVEpisode(1,3,"Ep Name (2)")
        secondEp._status = Quality.compositeStatus(DOWNLOADED, Quality.HDTV)
        ep.relatedEps.append(secondEp)

    return {'name': ep.formatted_filename(pattern, multi), 'dir': ep.formatted_dir(pattern, multi)}
