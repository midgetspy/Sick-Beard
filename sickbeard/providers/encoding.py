from string import ascii_letters, digits
from urllib import quote_plus
import re
import traceback
import unicodedata

env_encoding = 'UTF-8'

def toSafeString(original):
    valid_chars = "-_.() %s%s" % (ascii_letters, digits)
    cleanedFilename = unicodedata.normalize('NFKD', toUnicode(original)).encode('ASCII', 'ignore')
    return ''.join(c for c in cleanedFilename if c in valid_chars)

def simplifyString(original):
    string = stripAccents(original.lower())
    string = toSafeString(' '.join(re.split('\W+', string)))
    split = re.split('\W+|_', string.lower())
    return toUnicode(' '.join(split))

def toUnicode(original, *args):
    try:
        if isinstance(original, unicode):
            return original
        else:
            try:
                return unicode(original, *args)
            except:
                try:
                    return ek(original, *args)
                except:
                    raise
    except:
        ascii_text = str(original).encode('string_escape')
        return toUnicode(ascii_text)

def ss(original, *args):
    return toUnicode(original, *args).encode(env_encoding)

def ek(original, *args):
    if isinstance(original, (str, unicode)):
        try:
            return original.decode(env_encoding)
        except UnicodeDecodeError:
            raise

    return original

def isInt(value):
    try:
        int(value)
        return True
    except ValueError:
        return False

def stripAccents(s):
    return ''.join((c for c in unicodedata.normalize('NFD', toUnicode(s)) if unicodedata.category(c) != 'Mn'))

def tryUrlencode(s):
    new = u''
    if isinstance(s, (dict)):
        for key, value in s.iteritems():
            new += u'&%s=%s' % (key, tryUrlencode(value))

        return new[1:]
    else:
        for letter in ss(s):
            try:
                new += quote_plus(letter)
            except:
                new += letter

    return new
