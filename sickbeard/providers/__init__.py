__all__ = ['eztv','newzbin','nzbmatrix','nzbs','tvbinz','tvnzb']

import sickbeard

from os import sys

def getAllModules():
    sortedModuleList = []
    
    # add all the modules in our priority list, in order
    for curModule in sickbeard.PROVIDER_ORDER:
        if curModule in __all__:
            sortedModuleList.append(curModule)
    
    # add any modules that are missing from that list
    for curModule in __all__:
        if curModule not in sortedModuleList:
            sortedModuleList.append(curModule)

    return filter(lambda x: x != None, [getProviderModule(y) for y in sortedModuleList])

def getProviderModule(name):
    name = name.lower()
    prefix = "sickbeard.providers."
    if name in __all__ and prefix+name in sys.modules:
        return sys.modules[prefix+name]
    else:
        return None