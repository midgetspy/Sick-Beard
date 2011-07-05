# Author: Antoine Bertin <diaoulael@gmail.com>
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
import sickbeard
try:
    import subliminal
    SUBTITLES_SUPPORTED = True
except:
    SUBTITLES_SUPPORTED = False

def sortedPluginList():
    pluginsMapping = dict([(x.lower(), x) for x in subliminal.Subliminal.listExistingPlugins()])

    newList = []

    # add all plugins in the priority list, in order
    curIndex = 0
    for curPlugin in sickbeard.SUBTITLES_PLUGINS_LIST:
        if curPlugin in pluginsMapping:
            curPluginDict = {'id': curPlugin, 'image': curPlugin+'.png', 'name': pluginsMapping[curPlugin], 'enabled': sickbeard.SUBTITLES_PLUGINS_ENABLED[curIndex] == 1,
                'api_based': subliminal.Subliminal.isAPIBasedPlugin(pluginsMapping[curPlugin]), 'url': getattr(subliminal.plugins, pluginsMapping[curPlugin]).site_url}
            newList.append(curPluginDict)
        curIndex += 1

    # add any plugins that are missing from that list
    for curPlugin in pluginsMapping.keys():
        if curPlugin not in [x["id"] for x in newList]:
            curPluginDict = {'id': curPlugin, 'image': curPlugin+'.png', 'name': pluginsMapping[curPlugin], 'enabled': False,
                'api_based': subliminal.Subliminal.isAPIBasedPlugin(pluginsMapping[curPlugin]), 'url': getattr(subliminal.plugins, pluginsMapping[curPlugin]).site_url}
            newList.append(curPluginDict)

    return newList
    
def getEnabledPluginList():
    return [x['name'] for x in sortedPluginList() if x['enabled']]
    
def isValidLanguage(language):
    return subliminal.Subliminal.isValidLanguage(language)
