import os
import os.path

from sickbeard import logger

# This module tries to deal with the apparently random behavior of python when dealing with unicode <-> utf-8
# encodings. It tries to just use unicode, but if that fails then it tries forcing it to utf-8. Any functions
# which return something should always return unicode.

def fixStupidEncodings(x):
    if type(x) == str:
        try:
            return x.decode('utf-8')
        except UnicodeDecodeError:
            logger.log(u"Unable to decode value: "+str(repr(x)), logger.ERROR)
            return None
    elif type(x) == unicode:
        return x
    else:
        logger.log(u"Unknown value passed in, ignoring it: "+str(type(x)), logger.ERROR)
        return None

    return None
    
def fixListEncodings(x):
    if type(x) != list:
        return x
    else:
        return filter(lambda x: x != None, map(fixStupidEncodings, x))


def ek(func, *args):
    result = None

    if os.name == 'nt':
        result = func(*args)
    else:
        result = func(*[x.encode('UTF-8') for x in args])
    
    if type(result) == list:
        return fixListEncodings(result)
    elif type(result) == str:
        return fixStupidEncodings(result)
    else:
        return result
