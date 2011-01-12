__all__ = ['generic', 'helpers', 'xbmc', 'mediabrowser', 'ps3']

import sys
import xbmc, mediabrowser, ps3

def available_generators():
    return filter(lambda x: x not in ('generic', 'helpers'), __all__)

def _getMetadataModule(name):
    name = name.lower()
    prefix = "sickbeard.metadata."
    if name in __all__ and prefix+name in sys.modules:
        return sys.modules[prefix+name]
    else:
        return None

def _getMetadataClass(name):

    module = _getMetadataModule(name)
    
    if not module:
        return None
    
    return module.metadata_class()

def get_metadata_generator_dict():
    result = {}
    for cur_generator_id in available_generators():
        cur_generator = _getMetadataClass(cur_generator_id)
        if not cur_generator:
            continue
        result[cur_generator.name] = cur_generator
    
    return result
        
