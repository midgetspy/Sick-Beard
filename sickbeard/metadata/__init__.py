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

def getMetadataGeneratorList():
    result = {}
    for cur_generator_id in available_generators():
        cur_module = getMetadataClass(cur_generator_id)
        if not cur_module:
            continue
        result[cur_generator_id] = cur_module.name
    
    return result
        