# -*- coding: utf-8 -*-
""" This module parses and generates contentlines as defined in RFC 2445
(iCalendar), but will probably work for other MIME types with similar syntax.
Eg. RFC 2426 (vCard)

It is stupid in the sense that it treats the content purely as strings. No type
conversion is attempted.

Copyright, 2005: Max M <maxm@mxm.dk>
"""

import re
import icalendar.tools
from types import TupleType, ListType
from icalendar.caselessdict import CaselessDict
SequenceTypes = [TupleType, ListType]


def foldline(text, lenght=75, newline='\r\n'):
    """Make a string folded per RFC5545 (each line must be less than 75 octets)

    >>> from icalendar.parser import foldline
    >>> foldline('foo')
    'foo'

    >>> longtext = ("Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
    ...             "Vestibulum convallis imperdiet dui posuere.")
    >>> foldline(longtext)
    ... # doctest: +NORMALIZE_WHITESPACE
    'Lorem ipsum dolor sit amet, consectetur adipiscing elit. Vestibulum \\r\\n
    convallis imperdiet dui posuere.'

#    >>> uuu = u'alfdkadäääüüaskd'
#    >>> foldline(uuu, length=3)
#    u'alf\ndka\nd\xe4\xe4\n\xe4\xfc\xfc\nask\nd'

    """
    return newline.join(
            icalendar.tools.wrap(text, lenght,
                subsequent_indent=' ',
                drop_whitespace=False,
                break_long_words=True,
                replace_whitespace=False
                )
            )

#################################################################
# Property parameter stuff

def paramVal(val):
    "Returns a parameter value"
    if type(val) in SequenceTypes:
        return q_join(val)
    return dQuote(val)

# Could be improved
NAME = re.compile('[\w-]+')
UNSAFE_CHAR = re.compile('[\x00-\x08\x0a-\x1f\x7F",:;]')
QUNSAFE_CHAR = re.compile('[\x00-\x08\x0a-\x1f\x7F"]')
FOLD = re.compile('([\r]?\n)+[ \t]{1}')
NEWLINE = re.compile(r'\r?\n')

DEFAULT_ENCODING = 'utf-8'

def validate_token(name):
    match = NAME.findall(name)
    if len(match) == 1 and name == match[0]:
        return
    raise ValueError, name

def validate_param_value(value, quoted=True):
    validator = UNSAFE_CHAR
    if quoted:
        validator = QUNSAFE_CHAR
    if validator.findall(value):
        raise ValueError, value

QUOTABLE = re.compile('[,;:].')
def dQuote(val):
    """
    Parameter values containing [,;:] must be double quoted
    >>> dQuote('Max')
    'Max'
    >>> dQuote('Rasmussen, Max')
    '"Rasmussen, Max"'
    >>> dQuote('name:value')
    '"name:value"'
    """
    if QUOTABLE.search(val):
        return '"%s"' % val
    return val

# parsing helper
def q_split(st, sep=','):
    """
    Splits a string on char, taking double (q)uotes into considderation
    >>> q_split('Max,Moller,"Rasmussen, Max"')
    ['Max', 'Moller', '"Rasmussen, Max"']
    """
    result = []
    cursor = 0
    length = len(st)
    inquote = 0
    for i in range(length):
        ch = st[i]
        if ch == '"':
            inquote = not inquote
        if not inquote and ch == sep:
            result.append(st[cursor:i])
            cursor = i + 1
        if i + 1 == length:
            result.append(st[cursor:])
    return result

def q_join(lst, sep=','):
    """
    Joins a list on sep, quoting strings with QUOTABLE chars
    >>> s = ['Max', 'Moller', 'Rasmussen, Max']
    >>> q_join(s)
    'Max,Moller,"Rasmussen, Max"'
    """
    return sep.join([dQuote(itm) for itm in lst])

class Parameters(CaselessDict):
    """
    Parser and generator of Property parameter strings. It knows nothing of
    datatypes. It's main concern is textual structure.


    Simple parameter:value pair
    >>> p = Parameters(parameter1='Value1')
    >>> p.to_ical()
    'PARAMETER1=Value1'


    keys are converted to upper
    >>> p.keys()
    ['PARAMETER1']


    Parameters are case insensitive
    >>> p['parameter1']
    'Value1'
    >>> p['PARAMETER1']
    'Value1'


    Parameter with list of values must be seperated by comma
    >>> p = Parameters({'parameter1':['Value1', 'Value2']})
    >>> p.to_ical()
    'PARAMETER1=Value1,Value2'


    Multiple parameters must be seperated by a semicolon
    >>> p = Parameters({'RSVP':'TRUE', 'ROLE':'REQ-PARTICIPANT'})
    >>> p.to_ical()
    'ROLE=REQ-PARTICIPANT;RSVP=TRUE'


    Parameter values containing ',;:' must be double quoted
    >>> p = Parameters({'ALTREP':'http://www.wiz.org'})
    >>> p.to_ical()
    'ALTREP="http://www.wiz.org"'


    list items must be quoted seperately
    >>> p = Parameters({'MEMBER':['MAILTO:projectA@host.com', 'MAILTO:projectB@host.com', ]})
    >>> p.to_ical()
    'MEMBER="MAILTO:projectA@host.com","MAILTO:projectB@host.com"'

    Now the whole sheebang
    >>> p = Parameters({'parameter1':'Value1', 'parameter2':['Value2', 'Value3'],\
                          'ALTREP':['http://www.wiz.org', 'value4']})
    >>> p.to_ical()
    'ALTREP="http://www.wiz.org",value4;PARAMETER1=Value1;PARAMETER2=Value2,Value3'

    We can also parse parameter strings
    >>> Parameters.from_ical('PARAMETER1=Value 1;param2=Value 2')
    Parameters({'PARAMETER1': 'Value 1', 'PARAM2': 'Value 2'})

    Including empty strings
    >>> Parameters.from_ical('param=')
    Parameters({'PARAM': ''})

    We can also parse parameter strings
    >>> Parameters.from_ical('MEMBER="MAILTO:projectA@host.com","MAILTO:projectB@host.com"')
    Parameters({'MEMBER': ['MAILTO:projectA@host.com', 'MAILTO:projectB@host.com']})

    We can also parse parameter strings
    >>> Parameters.from_ical('ALTREP="http://www.wiz.org",value4;PARAMETER1=Value1;PARAMETER2=Value2,Value3')
    Parameters({'PARAMETER1': 'Value1', 'ALTREP': ['http://www.wiz.org', 'value4'], 'PARAMETER2': ['Value2', 'Value3']})
    """


    def params(self):
        """
        in rfc2445 keys are called parameters, so this is to be consitent with
        the naming conventions
        """
        return self.keys()

### Later, when I get more time... need to finish this off now. The last majot thing missing.
###    def _encode(self, name, value, cond=1):
###        # internal, for conditional convertion of values.
###        if cond:
###            klass = types_factory.for_property(name)
###            return klass(value)
###        return value
###
###    def add(self, name, value, encode=0):
###        "Add a parameter value and optionally encode it."
###        if encode:
###            value = self._encode(name, value, encode)
###        self[name] = value
###
###    def decoded(self, name):
###        "returns a decoded value, or list of same"

    def __repr__(self):
        return 'Parameters(' + dict.__repr__(self) + ')'


    def to_ical(self):
        result = []
        items = self.items()
        items.sort() # To make doctests work
        for key, value in items:
            value = paramVal(value)
            result.append('%s=%s' % (key.upper(), value))
        return ';'.join(result)


    def from_ical(st, strict=False):
        "Parses the parameter format from ical text format"

        # parse into strings
        result = Parameters()
        for param in q_split(st, ';'):
            try:
                key, val =  q_split(param, '=')
                validate_token(key)
                param_values = [v for v in q_split(val, ',')]
                # Property parameter values that are not in quoted
                # strings are case insensitive.
                vals = []
                for v in param_values:
                    if v.startswith('"') and v.endswith('"'):
                        v = v.strip('"')
                        validate_param_value(v, quoted=True)
                        vals.append(v)
                    else:
                        validate_param_value(v, quoted=False)
                        if strict:
                            vals.append(v.upper())
                        else:
                            vals.append(v)
                if not vals:
                    result[key] = val
                else:
                    if len(vals) == 1:
                        result[key] = vals[0]
                    else:
                        result[key] = vals
            except ValueError, e:
                raise ValueError, '%r is not a valid parameter string: %s' % (param, e)
        return result
    from_ical = staticmethod(from_ical)


#########################################
# parsing and generation of content lines

class Contentline(str):
    """
    A content line is basically a string that can be folded and parsed into
    parts.

    >>> c = Contentline('Si meliora dies, ut vina, poemata reddit')
    >>> c.to_ical()
    'Si meliora dies, ut vina, poemata reddit'

    A long line gets folded
    >>> c = Contentline(''.join(['123456789 ']*10))
    >>> c.to_ical()
    '123456789 123456789 123456789 123456789 123456789 123456789 123456789 \\r\\n 123456789 123456789 123456789 '

    A folded line gets unfolded
    >>> c = Contentline.from_ical(c.to_ical())
    >>> c
    '123456789 123456789 123456789 123456789 123456789 123456789 123456789 123456789 123456789 123456789 '

    Newlines in a string get need to be preserved
    >>> c = Contentline('1234\\n\\n1234')
    >>> c.to_ical()
    '1234\\n\\n1234'

    We do not fold within a UTF-8 character:
    >>> c = Contentline('This line has a UTF-8 character where it should be folded. Make sure it g\xc3\xabts folded before that character.')
    >>> '\xc3\xab' in c.to_ical()
    True

    Another test of the above
    >>> c = Contentline('x' * 73 + '\xc3\xab' + '\\n ' + 'y' * 10)
    >>> c.to_ical().count('\xc3')
    1

    Don't fail if we fold a line that is exactly X times 74 characters long:
    >>> c = Contentline(''.join(['x']*148)).to_ical()

    It can parse itself into parts. Which is a tuple of (name, params, vals)

    >>> c = Contentline('dtstart:20050101T120000')
    >>> c.parts()
    ('dtstart', Parameters({}), '20050101T120000')

    >>> c = Contentline('dtstart;value=datetime:20050101T120000')
    >>> c.parts()
    ('dtstart', Parameters({'VALUE': 'datetime'}), '20050101T120000')

    >>> c = Contentline('ATTENDEE;CN=Max Rasmussen;ROLE=REQ-PARTICIPANT:MAILTO:maxm@example.com')
    >>> c.parts()
    ('ATTENDEE', Parameters({'ROLE': 'REQ-PARTICIPANT', 'CN': 'Max Rasmussen'}), 'MAILTO:maxm@example.com')
    >>> c.to_ical()
    'ATTENDEE;CN=Max Rasmussen;ROLE=REQ-PARTICIPANT:MAILTO:maxm@example.com'

    and back again
    >>> parts = ('ATTENDEE', Parameters({'ROLE': 'REQ-PARTICIPANT', 'CN': 'Max Rasmussen'}), 'MAILTO:maxm@example.com')
    >>> Contentline.from_parts(parts)
    'ATTENDEE;CN=Max Rasmussen;ROLE=REQ-PARTICIPANT:MAILTO:maxm@example.com'

    and again
    >>> parts = ('ATTENDEE', Parameters(), 'MAILTO:maxm@example.com')
    >>> Contentline.from_parts(parts)
    'ATTENDEE:MAILTO:maxm@example.com'

    A value can also be any of the types defined in PropertyValues
    >>> from icalendar.prop import vText
    >>> parts = ('ATTENDEE', Parameters(), vText('MAILTO:test@example.com'))
    >>> Contentline.from_parts(parts)
    'ATTENDEE:MAILTO:test@example.com'

    A value can also be unicode
    >>> from icalendar.prop import vText
    >>> parts = ('SUMMARY', Parameters(), vText(u'INternational char æ ø å'))
    >>> Contentline.from_parts(parts)
    'SUMMARY:INternational char \\xc3\\xa6 \\xc3\\xb8 \\xc3\\xa5'

    Traversing could look like this.
    >>> name, params, vals = c.parts()
    >>> name
    'ATTENDEE'
    >>> vals
    'MAILTO:maxm@example.com'
    >>> for key, val in params.items():
    ...     (key, val)
    ('ROLE', 'REQ-PARTICIPANT')
    ('CN', 'Max Rasmussen')

    And the traditional failure
    >>> c = Contentline('ATTENDEE;maxm@example.com')
    >>> c.parts()                                               #doctest: +ELLIPSIS
    Traceback (most recent call last):
        ...
    ValueError: Content line could not be parsed into parts...

    Another failure:
    >>> c = Contentline(':maxm@example.com')
    >>> c.parts()                                               #doctest: +ELLIPSIS
    Traceback (most recent call last):
        ...
    ValueError: Content line could not be parsed into parts...

    >>> c = Contentline('key;param=:value')
    >>> c.parts()
    ('key', Parameters({'PARAM': ''}), 'value')

    >>> c = Contentline('key;param="pvalue":value')
    >>> c.parts()
    ('key', Parameters({'PARAM': 'pvalue'}), 'value')

    Should bomb on missing param:
    >>> c = Contentline.from_ical("k;:no param")
    >>> c.parts()                                               #doctest: +ELLIPSIS
    Traceback (most recent call last):
        ...
    ValueError: Content line could not be parsed into parts...

    >>> c = Contentline('key;param=pvalue:value', strict=False)
    >>> c.parts()
    ('key', Parameters({'PARAM': 'pvalue'}), 'value')

    If strict is set to True, uppercase param values that are not
    double-quoted, this is because the spec says non-quoted params are
    case-insensitive.

    >>> c = Contentline('key;param=pvalue:value', strict=True)
    >>> c.parts()
    ('key', Parameters({'PARAM': 'PVALUE'}), 'value')

    >>> c = Contentline('key;param="pValue":value', strict=True)
    >>> c.parts()
    ('key', Parameters({'PARAM': 'pValue'}), 'value')

    """

    def __new__(cls, value, strict=False):
        if isinstance(value, unicode):
            value = value.encode(DEFAULT_ENCODING)
        self = super(Contentline, cls).__new__(cls, value)
        setattr(self, 'strict', strict)
        return self

    def from_parts(parts):
        "Turns a tuple of parts into a content line"
        (name, params, values) = parts
        try:
            if values and not isinstance(values, basestring):
                if hasattr(values, 'to_ical'):
                    values = values.to_ical()
            if params:
                return Contentline('%s;%s:%s' % (name, params.to_ical(), values))
            return Contentline('%s:%s' %  (name, values))
        except:
            raise ValueError(
                'Property: %s Wrong values "%s" or "%s"' % (repr(name),
                                                            repr(params),
                                                            repr(values)))
    from_parts = staticmethod(from_parts)

    def parts(self):
        """ Splits the content line up into (name, parameters, values) parts
        """
        try:
            name_split = None
            value_split = None
            inquotes = 0
            for i in range(len(self)):
                ch = self[i]
                if not inquotes:
                    if ch in ':;' and not name_split:
                        name_split = i
                    if ch == ':' and not value_split:
                        value_split = i
                if ch == '"':
                    inquotes = not inquotes
            name = self[:name_split]
            if not name:
                raise ValueError, 'Key name is required'
            validate_token(name)
            if name_split+1 == value_split:
                raise ValueError, 'Invalid content line'
            params = Parameters.from_ical(self[name_split+1:value_split],
                                            strict=self.strict)
            values = self[value_split+1:]
            return (name, params, values)
        except ValueError, e:
            raise ValueError, "Content line could not be parsed into parts: %r: %s" % (self, e)

    def from_ical(st, strict=False):
        """ Unfolds the content lines in an iCalendar into long content lines.

        """
        try:
            # a fold is carriage return followed by either a space or a tab
            return Contentline(FOLD.sub('', st), strict=strict)
        except:
            raise ValueError, 'Expected StringType with content line'
    from_ical = staticmethod(from_ical)

    def to_ical(self):
        """ Long content lines are folded so they are less than 75 characters
        wide.

        """
        return foldline(self, newline='\r\n')



class Contentlines(list):
    """
    I assume that iCalendar files generally are a few kilobytes in size. Then
    this should be efficient. for Huge files, an iterator should probably be
    used instead.

    >>> c = Contentlines([Contentline('BEGIN:VEVENT\\r\\n')])
    >>> c.to_ical()
    'BEGIN:VEVENT\\r\\n\\r\\n'

    Lets try appending it with a 100 charater wide string
    >>> c.append(Contentline(''.join(['123456789 ']*10)+'\\r\\n'))
    >>> c.to_ical()
    'BEGIN:VEVENT\\r\\n\\r\\n123456789 123456789 123456789 123456789 123456789 123456789 123456789 \\r\\n 123456789 123456789 123456789 \\r\\n\\r\\n'

    Notice that there is an extra empty string in the end of the content lines.
    That is so they can be easily joined with: '\r\n'.join(contentlines)).
    >>> Contentlines.from_ical('A short line\\r\\n')
    ['A short line', '']
    >>> Contentlines.from_ical('A faked\\r\\n  long line\\r\\n')
    ['A faked long line', '']
    >>> Contentlines.from_ical('A faked\\r\\n  long line\\r\\nAnd another lin\\r\\n\\te that is folded\\r\\n')
    ['A faked long line', 'And another line that is folded', '']
    """

    def to_ical(self):
        "Simply join self."
        return '\r\n'.join(l.to_ical() for l in self if l) + '\r\n'

    def from_ical(st):
        "Parses a string into content lines"
        try:
            # a fold is carriage return followed by either a space or a tab
            unfolded = FOLD.sub('', st)
            lines = [Contentline(line) for line in unfolded.splitlines() if line]
            lines.append('') # we need a '\r\n' in the end of every content line
            return Contentlines(lines)
        except:
            raise ValueError, 'Expected StringType with content lines'
    from_ical = staticmethod(from_ical)


# ran this:
#    sample = open('./samples/test.ics', 'rb').read() # binary file in windows!
#    lines = Contentlines.from_ical(sample)
#    for line in lines[:-1]:
#        print line.parts()

# got this:
#('BEGIN', Parameters({}), 'VCALENDAR')
#('METHOD', Parameters({}), 'Request')
#('PRODID', Parameters({}), '-//My product//mxm.dk/')
#('VERSION', Parameters({}), '2.0')
#('BEGIN', Parameters({}), 'VEVENT')
#('DESCRIPTION', Parameters({}), 'This is a very long description that ...')
#('PARTICIPANT', Parameters({'CN': 'Max M'}), 'MAILTO:maxm@mxm.dk')
#('DTEND', Parameters({}), '20050107T160000')
#('DTSTART', Parameters({}), '20050107T120000')
#('SUMMARY', Parameters({}), 'A second event')
#('END', Parameters({}), 'VEVENT')
#('BEGIN', Parameters({}), 'VEVENT')
#('DTEND', Parameters({}), '20050108T235900')
#('DTSTART', Parameters({}), '20050108T230000')
#('SUMMARY', Parameters({}), 'A single event')
#('UID', Parameters({}), '42')
#('END', Parameters({}), 'VEVENT')
#('END', Parameters({}), 'VCALENDAR')
