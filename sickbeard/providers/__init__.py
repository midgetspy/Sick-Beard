__all__ = ['eztv','newzbin','nzbmatrix','nzbs','tvbinz','tvnzb']

from os import sys

def getAllModules():
    return filter(lambda x: x != None, [getProviderModule(y) for y in __all__])

def getProviderModule(name):
    name = name.lower()
    prefix = "sickbeard.providers."
    if name in __all__ and prefix+name in sys.modules:
        return sys.modules[prefix+name]
    else:
        return None