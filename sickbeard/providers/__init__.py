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

__all__ = ['ezrss',
           'hdbits',
           'tvtorrents',
           'torrentleech',
           'womble',
           'btn',
           'omgwtfnzbs'
           ]

import sickbeard

from os import sys


def sortedProviderList():

    initialList = sickbeard.providerList + sickbeard.newznabProviderList
    providerDict = dict(zip([x.getID() for x in initialList], initialList))

    newList = []

    # add all modules in the priority list, in order
    for curModule in sickbeard.PROVIDER_ORDER:
        if curModule in providerDict:
            newList.append(providerDict[curModule])

    # add any modules that are missing from that list
    for curModule in providerDict:
        if providerDict[curModule] not in newList:
            newList.append(providerDict[curModule])

    return newList


def makeProviderList():

    return [x.provider for x in [getProviderModule(y) for y in __all__] if x]


def getNewznabProviderList(data):

    defaultList = [makeNewznabProvider(x) for x in getDefaultNewznabProviders().split('!!!')]
    providerList = filter(lambda x: x, [makeNewznabProvider(x) for x in data.split('!!!')])

    providerDict = dict(zip([x.name for x in providerList], providerList))

    for curDefault in defaultList:
        if not curDefault:
            continue

        # a 0 in the key spot indicates that no key is needed, so set this on the object
        if curDefault.key == '0':
            curDefault.key = ''
            curDefault.needs_auth = False

        if curDefault.name not in providerDict:
            curDefault.default = True
            providerList.append(curDefault)
        else:
            providerDict[curDefault.name].default = True
            providerDict[curDefault.name].name = curDefault.name
            providerDict[curDefault.name].url = curDefault.url
            providerDict[curDefault.name].needs_auth = curDefault.needs_auth

    return filter(lambda x: x, providerList)


def makeNewznabProvider(configString):

    if not configString:
        return None

    name, url, key, enabled = configString.split('|')

    newznab = sys.modules['sickbeard.providers.newznab']

    newProvider = newznab.NewznabProvider(name, url)
    newProvider.key = key
    newProvider.enabled = enabled == '1'

    return newProvider


def getDefaultNewznabProviders():
    return 'Sick Beard Index|http://lolo.sickbeard.com/|0|0!!!NZBs.org|http://nzbs.org/||0!!!Usenet-Crawler|http://www.usenet-crawler.com/||0'


def getProviderModule(name):
    name = name.lower()
    prefix = "sickbeard.providers."
    if name in __all__ and prefix + name in sys.modules:
        return sys.modules[prefix + name]
    else:
        raise Exception("Can't find " + prefix + name + " in " + repr(sys.modules))


def getProviderClass(providerID):

    providerMatch = [x for x in sickbeard.providerList + sickbeard.newznabProviderList if x.getID() == providerID]

    if len(providerMatch) != 1:
        return None
    else:
        return providerMatch[0]
