__all__ = ['generic', 'helpers', 'xbmc', 'mediabrowser']

import sys
import xbmc, mediabrowser

def available_generators():
    return filter(lambda x: x not in ('generic', 'helpers'), __all__)

def getMetadataModule(name):
    name = name.lower()
    prefix = "sickbeard.metadata."
    if name in __all__ and prefix+name in sys.modules:
        return sys.modules[prefix+name]
    else:
        return None

def getMetadataClass(name):

    module = getMetadataModule(name)
    
    if not module:
        return None
    
    return module.metadata_class()