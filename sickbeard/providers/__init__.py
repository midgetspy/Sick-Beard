__all__ = ['eztv','ezrss','nzbmatrix','nzbs_org','tvbinz','nzbsrus','binreq','womble','newzbin']

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

        if curDefault.name not in providerDict:
            curDefault.default = True
            providerList.append(curDefault)
        else:
            providerDict[curDefault.name].default = True
            providerDict[curDefault.name].name = curDefault.name
            providerDict[curDefault.name].url = curDefault.url

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
    return 'NZB.su|http://www.nzb.su/||0'


def getProviderModule(name):
    name = name.lower()
    prefix = "sickbeard.providers."
    if name in __all__ and prefix+name in sys.modules:
        return sys.modules[prefix+name]
    else:
        return None

def getProviderClass(id):

    providerMatch = [x for x in sickbeard.providerList+sickbeard.newznabProviderList if x.getID() == id]

    if len(providerMatch) != 1:
        return None
    else:
        return providerMatch[0]
