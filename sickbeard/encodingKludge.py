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

import os, traceback

from sickbeard import logger
import sickbeard

# This module tries to deal with the apparently random behavior of python when dealing with unicode <-> utf-8
# encodings. It tries to just use unicode, but if that fails then it tries forcing it to utf-8. Any functions
# which return something should always return unicode.

def fixStupidEncodings(x, silent=False):
    if type(x) == str:
        try:
            return x.decode(sickbeard.SYS_ENCODING)
        except UnicodeDecodeError:
            logger.log(u"Unable to decode value: "+repr(x), logger.ERROR)
            return None
    elif type(x) == unicode:
        return x
    else:
        logger.log(u"Unknown value passed in, ignoring it: "+str(type(x))+" ("+repr(x)+":"+repr(type(x))+")", logger.DEBUG if silent else logger.ERROR)
        return None

    return None

def fixListEncodings(x):
    if type(x) != list and type(x) != tuple:
        return x
    else:
        return filter(lambda x: x != None, map(fixStupidEncodings, x))


def ek(func, *args):

    def changeByteStringToUnicode(obj):
        if type(obj) == str:
            logger.log(u"A bytestring was used as an argument for function "+func.__name__+": "+repr(obj), logger.WARNING)
            logger.log(''.join(traceback.format_stack()), logger.DEBUG)
            return obj.decode(sickbeard.SYS_ENCODING)
        else:
            return obj

    args = map(changeByteStringToUnicode, args)

    return func(*args)
