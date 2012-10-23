# -*- coding: utf-8 -*-
"""This module contains the parser/generators (or coders/encoders if you
prefer) for the classes/datatypes that are used in iCalendar:

###########################################################################
# This module defines these property value data types and property parameters

4.2 Defined property parameters are:

     ALTREP, CN, CUTYPE, DELEGATED-FROM, DELEGATED-TO, DIR, ENCODING, FMTTYPE,
     FBTYPE, LANGUAGE, MEMBER, PARTSTAT, RANGE, RELATED, RELTYPE, ROLE, RSVP,
     SENT-BY, TZID, VALUE

4.3 Defined value data types are:

    BINARY, BOOLEAN, CAL-ADDRESS, DATE, DATE-TIME, DURATION, FLOAT, INTEGER,
    PERIOD, RECUR, TEXT, TIME, URI, UTC-OFFSET

###########################################################################

iCalendar properties has values. The values are strongly typed. This module
defines these types, calling val.to_ical() on them, Will render them as defined
in rfc2445.

If you pass any of these classes a Python primitive, you will have an object
that can render itself as iCalendar formatted date.

Property Value Data Types starts with a 'v'. they all have an to_ical() and
from_ical() method. The to_ical() method generates a text string in the
iCalendar format. The from_ical() method can parse this format and return a
primitive Python datatype. So it should allways be true that:

    x == vDataType.from_ical(VDataType(x).to_ical())

These types are mainly used for parsing and file generation. But you can set
them directly.

"""

import pytz
import re
import time as _time
import binascii
from datetime import (
    datetime,
    timedelta,
    time,
    date,
    tzinfo,
)
from types import TupleType, ListType
from icalendar.caselessdict import CaselessDict
from icalendar.parser import Parameters


SequenceTypes = [TupleType, ListType]

DEFAULT_ENCODING = 'utf-8'

DATE_PART = r'(\d+)D'
TIME_PART = r'T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
DATETIME_PART = '(?:%s)?(?:%s)?' % (DATE_PART, TIME_PART)
WEEKS_PART = r'(\d+)W'
DURATION_REGEX = re.compile(r'([-+]?)P(?:%s|%s)$'
                            % (WEEKS_PART, DATETIME_PART))
WEEKDAY_RULE = re.compile('(?P<signal>[+-]?)(?P<relative>[\d]?)'
                          '(?P<weekday>[\w]{2})$')


class vBinary:
    """Binary property values are base 64 encoded.

    >>> b = vBinary('This is gibberish')
    >>> b.to_ical()
    'VGhpcyBpcyBnaWJiZXJpc2g='
    >>> b = vBinary.from_ical('VGhpcyBpcyBnaWJiZXJpc2g=')
    >>> b
    'This is gibberish'

    The roundtrip test
    >>> x = 'Binary data \x13 \x56'
    >>> vBinary(x).to_ical()
    'QmluYXJ5IGRhdGEgEyBW'
    >>> vBinary.from_ical('QmluYXJ5IGRhdGEgEyBW')
    'Binary data \\x13 V'

    >>> b = vBinary('txt')
    >>> b.params
    Parameters({'VALUE': 'BINARY', 'ENCODING': 'BASE64'})

    Long data should not have line breaks, as that would interfere
    >>> x = 'a'*99
    >>> vBinary(x).to_ical() == 'YWFh' * 33
    True
    >>> vBinary.from_ical('YWFh' * 33) == 'a' * 99
    True
    """

    def __init__(self, obj):
        self.obj = obj
        self.params = Parameters(encoding='BASE64', value="BINARY")

    def __repr__(self):
        return "vBinary(%s)" % str.__repr__(self.obj)

    def to_ical(self):
        return binascii.b2a_base64(self.obj)[:-1]

    def from_ical(ical):
        "Parses the data format from ical text format"
        try:
            return ical.decode('base-64')
        except UnicodeError:
            raise ValueError, 'Not valid base 64 encoding.'

    from_ical = staticmethod(from_ical)


class vBoolean(int):
    """Returns specific string according to state.

    >>> bin = vBoolean(True)
    >>> bin.to_ical()
    'TRUE'
    >>> bin = vBoolean(0)
    >>> bin.to_ical()
    'FALSE'

    The roundtrip test
    >>> x = True
    >>> x == vBoolean.from_ical(vBoolean(x).to_ical())
    True
    >>> vBoolean.from_ical('true')
    True
    """

    def __new__(cls, *args, **kwargs):
        self = super(vBoolean, cls).__new__(cls, *args, **kwargs)
        self.params = Parameters()
        return self

    def to_ical(self):
        if self:
            return 'TRUE'
        return 'FALSE'

    bool_map = CaselessDict(true=True, false=False)

    def from_ical(ical):
        "Parses the data format from ical text format"
        try:
            return vBoolean.bool_map[ical]
        except:
            raise ValueError, "Expected 'TRUE' or 'FALSE'. Got %s" % ical

    from_ical = staticmethod(from_ical)


class vCalAddress(str):
    """This just returns an unquoted string.

    >>> a = vCalAddress('MAILTO:maxm@mxm.dk')
    >>> a.params['cn'] = 'Max M'
    >>> a.to_ical()
    'MAILTO:maxm@mxm.dk'
    >>> a.params
    Parameters({'CN': 'Max M'})
    >>> vCalAddress.from_ical('MAILTO:maxm@mxm.dk')
    'MAILTO:maxm@mxm.dk'
    """

    def __new__(cls, value):
        if isinstance(value, unicode):
            value = value.encode(DEFAULT_ENCODING)
        self = super(vCalAddress, cls).__new__(cls, value)
        self.params = Parameters()
        return self

    def __repr__(self):
        return u"vCalAddress(%s)" % str.__repr__(self)

    def to_ical(self):
        return str(self)

    def from_ical(ical):
        "Parses the data format from ical text format"
        try:
            return str(ical)
        except:
            raise ValueError, 'Expected vCalAddress, got: %s' % ical

    from_ical = staticmethod(from_ical)


####################################################
# handy tzinfo classes you can use.
#

ZERO = timedelta(0)
HOUR = timedelta(hours=1)
STDOFFSET = timedelta(seconds = -_time.timezone)
if _time.daylight:
    DSTOFFSET = timedelta(seconds = -_time.altzone)
else:
    DSTOFFSET = STDOFFSET
DSTDIFF = DSTOFFSET - STDOFFSET


class FixedOffset(tzinfo):
    """Fixed offset in minutes east from UTC.
    """

    def __init__(self, offset, name):
        self.__offset = timedelta(minutes = offset)
        self.__name = name

    def utcoffset(self, dt):
        return self.__offset

    def tzname(self, dt):
        return self.__name

    def dst(self, dt):
        return ZERO


class LocalTimezone(tzinfo):
    """Timezone of the machine where the code is running.
    """

    def utcoffset(self, dt):
        if self._isdst(dt):
            return DSTOFFSET
        else:
            return STDOFFSET

    def dst(self, dt):
        if self._isdst(dt):
            return DSTDIFF
        else:
            return ZERO

    def tzname(self, dt):
        return _time.tzname[self._isdst(dt)]

    def _isdst(self, dt):
        tt = (dt.year, dt.month, dt.day,
              dt.hour, dt.minute, dt.second,
              dt.weekday(), 0, -1)
        stamp = _time.mktime(tt)
        tt = _time.localtime(stamp)
        return tt.tm_isdst > 0


class vFloat(float):
    """Just a float.

    >>> f = vFloat(1.0)
    >>> f.to_ical()
    '1.0'
    >>> vFloat.from_ical('42')
    42.0
    >>> vFloat(42).to_ical()
    '42.0'
    """

    def __new__(cls, *args, **kwargs):
        self = super(vFloat, cls).__new__(cls, *args, **kwargs)
        self.params = Parameters()
        return self

    def to_ical(self):
        return str(self)

    def from_ical(ical):
        "Parses the data format from ical text format"
        try:
            return float(ical)
        except:
            raise ValueError, 'Expected float value, got: %s' % ical

    from_ical = staticmethod(from_ical)


class vInt(int):
    """Just an int.

    >>> f = vInt(42)
    >>> f.to_ical()
    '42'
    >>> vInt.from_ical('13')
    13
    >>> vInt.from_ical('1s3')
    Traceback (most recent call last):
        ...
    ValueError: Expected int, got: 1s3
    """

    def __new__(cls, *args, **kwargs):
        self = super(vInt, cls).__new__(cls, *args, **kwargs)
        self.params = Parameters()
        return self

    def to_ical(self):
        return str(self)

    def from_ical(ical):
        "Parses the data format from ical text format"
        try:
            return int(ical)
        except:
            raise ValueError, 'Expected int, got: %s' % ical

    from_ical = staticmethod(from_ical)


class vDDDLists:
    """A list of vDDDTypes values.

    >>> dt_list = vDDDLists.from_ical('19960402T010000Z')
    >>> type(dt_list)
    <type 'list'>

    >>> len(dt_list)
    1

    >>> type(dt_list[0])
    <type 'datetime.datetime'>

    >>> str(dt_list[0])
    '1996-04-02 01:00:00+00:00'

    >>> p = '19960402T010000Z,19960403T010000Z,19960404T010000Z'
    >>> dt_list = vDDDLists.from_ical(p)
    >>> len(dt_list)
    3

    >>> str(dt_list[0])
    '1996-04-02 01:00:00+00:00'
    >>> str(dt_list[2])
    '1996-04-04 01:00:00+00:00'

    >>> dt_list = vDDDLists('19960402T010000Z')
    Traceback (most recent call last):
        ...
    ValueError: Value MUST be a list (of date instances)

    >>> dt_list = vDDDLists([])
    >>> dt_list.to_ical()
    ''

    >>> dt_list = vDDDLists([datetime(2000,1,1)])
    >>> dt_list.to_ical()
    '20000101T000000'

    >>> dt_list = vDDDLists([datetime(2000,1,1), datetime(2000,11,11)])
    >>> dt_list.to_ical()
    '20000101T000000,20001111T000000'
    """

    def __init__(self, dt_list):
        if not isinstance(dt_list, list):
            raise ValueError('Value MUST be a list (of date instances)')
        vDDD = []
        for dt in dt_list:
            vDDD.append(vDDDTypes(dt))
        self.dts = vDDD

    def to_ical(self):
        '''Generates the text string in the iCalendar format.
        '''
        dts_ical = [dt.to_ical() for dt in self.dts]
        return ",".join(dts_ical)

    def from_ical(ical):
        '''Parses the list of data formats from ical text format.
        @param ical: ical text format
        '''
        out = []
        ical_dates = ical.split(",")
        for ical_dt in ical_dates:
            out.append(vDDDTypes.from_ical(ical_dt))
        return out

    from_ical = staticmethod(from_ical)


class vDDDTypes:
    """A combined Datetime, Date or Duration parser/generator. Their format
    cannot be confused, and often values can be of either types.
    So this is practical.

    >>> d = vDDDTypes.from_ical('20010101T123000')
    >>> type(d)
    <type 'datetime.datetime'>

    >>> repr(vDDDTypes.from_ical('20010101T123000Z'))[:65]
    'datetime.datetime(2001, 1, 1, 12, 30, tzinfo=<UTC>)'

    >>> d = vDDDTypes.from_ical('20010101')
    >>> type(d)
    <type 'datetime.date'>

    >>> vDDDTypes.from_ical('P31D')
    datetime.timedelta(31)

    >>> vDDDTypes.from_ical('-P31D')
    datetime.timedelta(-31)

    Bad input
    >>> vDDDTypes(42)
    Traceback (most recent call last):
        ...
    ValueError: You must use datetime, date or timedelta
    """

    def __init__(self, dt):
        "Returns vDate from"
        if type(dt) not in (datetime, date, timedelta):
            raise ValueError ('You must use datetime, date or timedelta')
        if isinstance(dt, datetime):
            self.params = Parameters(dict(value='DATE-TIME'))
        elif isinstance(dt, date): # isinstance(datetime_object, date) => True
            self.params = Parameters(dict(value='DATE'))
        self.dt = dt

    def to_ical(self):
        dt = self.dt
        if isinstance(dt, datetime):
            return vDatetime(dt).to_ical()
        elif isinstance(dt, date):
            return vDate(dt).to_ical()
        elif isinstance(dt, timedelta):
            return vDuration(dt).to_ical()
        else:
            raise ValueError('Unknown date type')

    def from_ical(ical, timezone=None):
        "Parses the data format from ical text format"
        if isinstance(ical, vDDDTypes):
            return ical.dt
        u = ical.upper()
        if u.startswith('-P') or u.startswith('P'):
            return vDuration.from_ical(ical)
        try:
            return vDatetime.from_ical(ical, timezone=timezone)
        except:
            return vDate.from_ical(ical)

    from_ical = staticmethod(from_ical)


class vDate:
    """Render and generates iCalendar date format.

    >>> d = date(2001, 1,1)
    >>> vDate(d).to_ical()
    '20010101'

    >>> d = date(1899, 1, 1)
    >>> vDate(d).to_ical()
    '18990101'

    >>> vDate.from_ical('20010102')
    datetime.date(2001, 1, 2)

    >>> vDate('d').to_ical()
    Traceback (most recent call last):
        ...
    ValueError: Value MUST be a date instance
    """

    def __init__(self, dt):
        if not isinstance(dt, date):
            raise ValueError('Value MUST be a date instance')
        self.dt = dt
        self.params = Parameters(dict(value='DATE'))

    def to_ical(self):
        return "%04d%02d%02d" % (self.dt.year, self.dt.month, self.dt.day)

    def from_ical(ical):
        "Parses the data format from ical text format"
        try:
            timetuple = map(int, ((
                ical[:4],     # year
                ical[4:6],    # month
                ical[6:8],    # day
                )))
            return date(*timetuple)
        except:
            raise ValueError, 'Wrong date format %s' % ical

    from_ical = staticmethod(from_ical)


class vDatetime:
    """Render and generates icalendar datetime format.

    vDatetime is timezone aware and uses the pytz library, an implementation of
    the Olson database in Python. When a vDatetime object is created from an
    ical string, the string must be a valid pytz timezone identifier. When and
    vDatetime object is created from a python datetime object, it uses the
    tzinfo component, if present. Otherwise an timezone-naive object is
    created. Be aware that there are certain limitations with timezone naive
    DATE-TIME components in the icalendar standard.

    >>> d = datetime(2001, 1,1, 12, 30, 0)

    >>> dt = vDatetime(d)
    >>> dt.to_ical()
    '20010101T123000'

    >>> vDatetime.from_ical('20000101T120000')
    datetime.datetime(2000, 1, 1, 12, 0)

    >>> dutc = datetime(2001, 1,1, 12, 30, 0, tzinfo=pytz.utc)
    >>> vDatetime(dutc).to_ical()
    '20010101T123000Z'

    >>> dutc = datetime(1899, 1,1, 12, 30, 0, tzinfo=pytz.utc)
    >>> vDatetime(dutc).to_ical()
    '18990101T123000Z'

    >>> vDatetime.from_ical('20010101T000000')
    datetime.datetime(2001, 1, 1, 0, 0)

    >>> vDatetime.from_ical('20010101T000000A')
    Traceback (most recent call last):
      ...
    ValueError: Wrong datetime format: 20010101T000000A

    >>> utc = vDatetime.from_ical('20010101T000000Z')
    >>> vDatetime(utc).to_ical()
    '20010101T000000Z'

    1 minute before transition to DST
    >>> dat = vDatetime.from_ical('20120311T015959', 'America/Denver')
    >>> dat.strftime('%Y%m%d%H%M%S %z')
    '20120311015959 -0700'

    After transition to DST
    >>> dat = vDatetime.from_ical('20120311T030000', 'America/Denver')
    >>> dat.strftime('%Y%m%d%H%M%S %z')
    '20120311030000 -0600'

    >>> dat = vDatetime.from_ical('20101010T000000', 'Europe/Vienna')
    >>> vDatetime(dat).to_ical()
    '20101010T000000'
    """

    def __init__(self, dt):
        self.dt = dt
        self.params = Parameters()

    def to_ical(self):
        dt = self.dt
        tzid = dt.tzinfo and dt.tzinfo.zone or None
        s = "%04d%02d%02dT%02d%02d%02d" % (
            self.dt.year,
            self.dt.month,
            self.dt.day,
            self.dt.hour,
            self.dt.minute,
            self.dt.second
        )
        if tzid == 'UTC':
            s += "Z"
        elif tzid:
            self.params.update({'TZID': tzid})
        return s

    def from_ical(ical, timezone=None):
        """ Parses the data format from ical text format.

        """
        tzinfo = None
        if timezone:
            try:
                tzinfo = pytz.timezone(timezone)
            except pytz.UnknownTimeZoneError:
                pass

        try:
            timetuple = map(int, ((
                ical[:4],       # year
                ical[4:6],      # month
                ical[6:8],      # day
                ical[9:11],     # hour
                ical[11:13],    # minute
                ical[13:15],    # second
                )))
            if tzinfo:
                return tzinfo.localize(datetime(*timetuple))
            elif not ical[15:]:
                return datetime(*timetuple)
            elif ical[15:16] == 'Z':
                return datetime(tzinfo=pytz.utc, *timetuple)
            else:
                raise ValueError, ical
        except:
            raise ValueError, 'Wrong datetime format: %s' % ical

    from_ical = staticmethod(from_ical)


class vDuration:
    """Subclass of timedelta that renders itself in the iCalendar DURATION
    format.

    >>> vDuration(timedelta(11)).to_ical()
    'P11D'
    >>> vDuration(timedelta(-14)).to_ical()
    '-P14D'
    >>> vDuration(timedelta(1, 7384)).to_ical()
    'P1DT2H3M4S'
    >>> vDuration(timedelta(1, 7380)).to_ical()
    'P1DT2H3M'
    >>> vDuration(timedelta(1, 7200)).to_ical()
    'P1DT2H'
    >>> vDuration(timedelta(0, 7200)).to_ical()
    'PT2H'
    >>> vDuration(timedelta(0, 7384)).to_ical()
    'PT2H3M4S'
    >>> vDuration(timedelta(0, 184)).to_ical()
    'PT3M4S'
    >>> vDuration(timedelta(0, 22)).to_ical()
    'PT22S'
    >>> vDuration(timedelta(0, 3622)).to_ical()
    'PT1H0M22S'

    >>> vDuration(timedelta(days=1, hours=5)).to_ical()
    'P1DT5H'
    >>> vDuration(timedelta(hours=-5)).to_ical()
    '-PT5H'
    >>> vDuration(timedelta(days=-1, hours=-5)).to_ical()
    '-P1DT5H'

    How does the parsing work?
    >>> vDuration.from_ical('PT1H0M22S')
    datetime.timedelta(0, 3622)

    >>> vDuration.from_ical('kox')
    Traceback (most recent call last):
        ...
    ValueError: Invalid iCalendar duration: kox

    >>> vDuration.from_ical('-P14D')
    datetime.timedelta(-14)

    >>> vDuration(11)
    Traceback (most recent call last):
        ...
    ValueError: Value MUST be a timedelta instance
    """

    def __init__(self, td):
        if not isinstance(td, timedelta):
            raise ValueError('Value MUST be a timedelta instance')
        self.td = td
        self.params = Parameters()

    def to_ical(self):
        sign = ""
        if self.td.days < 0:
            sign = "-"
            self.td = -self.td
        timepart = ""
        if self.td.seconds:
            timepart = "T"
            hours = self.td.seconds // 3600
            minutes = self.td.seconds % 3600 // 60
            seconds = self.td.seconds % 60
            if hours:
                timepart += "%dH" % hours
            if minutes or (hours and seconds):
                timepart += "%dM" % minutes
            if seconds:
                timepart += "%dS" % seconds
        if self.td.days == 0 and timepart:
            return "%sP%s" % (sign, timepart)
        else:
            return "%sP%dD%s" % (sign, abs(self.td.days), timepart)

    def from_ical(ical):
        """ Parses the data format from ical text format.

        """
        try:
            match = DURATION_REGEX.match(ical)
            sign, weeks, days, hours, minutes, seconds = match.groups()
            if weeks:
                value = timedelta(weeks=int(weeks))
            else:
                value = timedelta(days=int(days or 0),
                                  hours=int(hours or 0),
                                  minutes=int(minutes or 0),
                                  seconds=int(seconds or 0))
            if sign == '-':
                value = -value
            return value
        except:
            raise ValueError('Invalid iCalendar duration: %s' % ical)

    from_ical = staticmethod(from_ical)


class vPeriod:
    """A precise period of time.

    One day in exact datetimes
    >>> per = (datetime(2000,1,1), datetime(2000,1,2))
    >>> p = vPeriod(per)
    >>> p.to_ical()
    '20000101T000000/20000102T000000'

    >>> per = (datetime(2000,1,1), timedelta(days=31))
    >>> p = vPeriod(per)
    >>> p.to_ical()
    '20000101T000000/P31D'

    Roundtrip
    >>> p = vPeriod.from_ical('20000101T000000/20000102T000000')
    >>> p
    (datetime.datetime(2000, 1, 1, 0, 0), datetime.datetime(2000, 1, 2, 0, 0))
    >>> vPeriod(p).to_ical()
    '20000101T000000/20000102T000000'

    >>> vPeriod.from_ical('20000101T000000/P31D')
    (datetime.datetime(2000, 1, 1, 0, 0), datetime.timedelta(31))

    Roundtrip with absolute time
    >>> p = vPeriod.from_ical('20000101T000000Z/20000102T000000Z')
    >>> vPeriod(p).to_ical()
    '20000101T000000Z/20000102T000000Z'

    And an error
    >>> vPeriod.from_ical('20000101T000000/Psd31D')
    Traceback (most recent call last):
        ...
    ValueError: Expected period format, got: 20000101T000000/Psd31D

    Timezoned
    >>> import pytz
    >>> dk = pytz.timezone('Europe/Copenhagen')
    >>> start = datetime(2000,1,1, tzinfo=dk)
    >>> end = datetime(2000,1,2, tzinfo=dk)
    >>> per = (start, end)
    >>> vPeriod(per).to_ical()
    '20000101T000000/20000102T000000'
    >>> vPeriod(per).params['TZID']
    'Europe/Copenhagen'

    >>> p = vPeriod((datetime(2000,1,1, tzinfo=dk), timedelta(days=31)))
    >>> p.to_ical()
    '20000101T000000/P31D'
    """

    def __init__(self, per):
        start, end_or_duration = per
        if not (isinstance(start, datetime) or isinstance(start, date)):
            raise ValueError('Start value MUST be a datetime or date instance')
        if not (isinstance(end_or_duration, datetime) or
                isinstance(end_or_duration, date) or
                isinstance(end_or_duration, timedelta)):
            raise ValueError('end_or_duration MUST be a datetime, '
                             'date or timedelta instance')
        by_duration = 0
        if isinstance(end_or_duration, timedelta):
            by_duration = 1
            duration = end_or_duration
            end = start + duration
        else:
            end = end_or_duration
            duration = end - start
        if start > end:
            raise ValueError("Start time is greater than end time")

        self.params = Parameters()
        # set the timezone identifier
        tzid = start.tzinfo and start.tzinfo.zone or None
        if tzid:
            self.params['TZID'] = tzid

        self.start = start
        self.end = end
        self.by_duration = by_duration
        self.duration = duration

    def __cmp__(self, other):
        if not isinstance(other, vPeriod):
            raise NotImplementedError(
                'Cannot compare vPeriod with %s' % repr(other))
        return cmp((self.start, self.end), (other.start, other.end))

    def overlaps(self, other):
        if self.start > other.start:
            return other.overlaps(self)
        if self.start <= other.start < self.end:
            return True
        return False

    def to_ical(self):
        if self.by_duration:
            return '%s/%s' % (vDatetime(self.start).to_ical(),
                              vDuration(self.duration).to_ical())
        return '%s/%s' % (vDatetime(self.start).to_ical(),
                          vDatetime(self.end).to_ical())

    def from_ical(ical):
        "Parses the data format from ical text format"
        try:
            start, end_or_duration = ical.split('/')
            start = vDDDTypes.from_ical(start)
            end_or_duration = vDDDTypes.from_ical(end_or_duration)
            return (start, end_or_duration)
        except:
            raise ValueError, 'Expected period format, got: %s' % ical

    from_ical = staticmethod(from_ical)

    def __repr__(self):
        if self.by_duration:
            p = (self.start, self.duration)
        else:
            p = (self.start, self.end)
        return 'vPeriod(%s)' % repr(p)


class vWeekday(str):
    """This returns an unquoted weekday abbrevation.

    >>> a = vWeekday('mo')
    >>> a.to_ical()
    'MO'

    >>> a = vWeekday('erwer')
    Traceback (most recent call last):
        ...
    ValueError: Expected weekday abbrevation, got: erwer

    >>> vWeekday.from_ical('mo')
    'MO'

    >>> vWeekday.from_ical('+3mo')
    '+3MO'

    >>> vWeekday.from_ical('Saturday')
    Traceback (most recent call last):
        ...
    ValueError: Expected weekday abbrevation, got: Saturday

    >>> a = vWeekday('+mo')
    >>> a.to_ical()
    '+MO'

    >>> a = vWeekday('+3mo')
    >>> a.to_ical()
    '+3MO'

    >>> a = vWeekday('-tu')
    >>> a.to_ical()
    '-TU'
    """

    week_days = CaselessDict({"SU":0, "MO":1, "TU":2, "WE":3,
                              "TH":4, "FR":5, "SA":6})

    def __new__(cls, *args, **kwargs):
        self = super(vWeekday, cls).__new__(cls, *args, **kwargs)
        match = WEEKDAY_RULE.match(self)
        if match is None:
            raise ValueError, 'Expected weekday abbrevation, got: %s' % self
        match = match.groupdict()
        sign = match['signal']
        weekday = match['weekday']
        relative = match['relative']
        if not weekday in vWeekday.week_days or sign not in '+-':
            raise ValueError, 'Expected weekday abbrevation, got: %s' % self
        self.relative = relative and int(relative) or None
        self.params = Parameters()
        return self

    def to_ical(self):
        return self.upper()

    def from_ical(ical):
        "Parses the data format from ical text format"
        try:
            return vWeekday(ical.upper())
        except:
            raise ValueError, 'Expected weekday abbrevation, got: %s' % ical

    from_ical = staticmethod(from_ical)


class vFrequency(str):
    """A simple class that catches illegal values.

    >>> f = vFrequency('bad test')
    Traceback (most recent call last):
        ...
    ValueError: Expected frequency, got: bad test
    >>> vFrequency('daily').to_ical()
    'DAILY'
    >>> vFrequency('daily').from_ical('MONTHLY')
    'MONTHLY'
    """

    frequencies = CaselessDict({
        "SECONDLY":"SECONDLY",
        "MINUTELY":"MINUTELY",
        "HOURLY":"HOURLY",
        "DAILY":"DAILY",
        "WEEKLY":"WEEKLY",
        "MONTHLY":"MONTHLY",
        "YEARLY":"YEARLY",
    })

    def __new__(cls, *args, **kwargs):
        self = super(vFrequency, cls).__new__(cls, *args, **kwargs)
        if not self in vFrequency.frequencies:
            raise ValueError, 'Expected frequency, got: %s' % self
        self.params = Parameters()
        return self

    def to_ical(self):
        return self.upper()

    def from_ical(ical):
        "Parses the data format from ical text format"
        try:
            return vFrequency(ical.upper())
        except:
            raise ValueError, 'Expected weekday abbrevation, got: %s' % ical

    from_ical = staticmethod(from_ical)


class vRecur(CaselessDict):
    """Recurrence definition.

    Let's see how close we can get to one from the rfc:
    FREQ=YEARLY;INTERVAL=2;BYMONTH=1;BYDAY=SU;BYHOUR=8,9;BYMINUTE=30

    >>> r = dict(freq='yearly', interval=2)
    >>> r['bymonth'] = 1
    >>> r['byday'] = 'su'
    >>> r['byhour'] = [8,9]
    >>> r['byminute'] = 30
    >>> r = vRecur(r)
    >>> r.to_ical()
    'FREQ=YEARLY;INTERVAL=2;BYMINUTE=30;BYHOUR=8,9;BYDAY=SU;BYMONTH=1'

    >>> r = vRecur(FREQ='yearly', INTERVAL=2)
    >>> r['BYMONTH'] = 1
    >>> r['BYDAY'] = 'su'
    >>> r['BYHOUR'] = [8,9]
    >>> r['BYMINUTE'] = 30
    >>> r.to_ical()
    'FREQ=YEARLY;INTERVAL=2;BYMINUTE=30;BYHOUR=8,9;BYDAY=SU;BYMONTH=1'

    >>> r = vRecur(freq='DAILY', count=10)
    >>> r['bysecond'] = [0, 15, 30, 45]
    >>> r.to_ical()
    'FREQ=DAILY;COUNT=10;BYSECOND=0,15,30,45'

    >>> r = vRecur(freq='DAILY', until=datetime(2005,1,1,12,0,0))
    >>> r.to_ical()
    'FREQ=DAILY;UNTIL=20050101T120000'

    How do we fare with regards to parsing?
    >>> r = vRecur.from_ical('FREQ=DAILY;INTERVAL=2;COUNT=10')
    >>> r
    {'COUNT': [10], 'FREQ': ['DAILY'], 'INTERVAL': [2]}
    >>> vRecur(r).to_ical()
    'FREQ=DAILY;COUNT=10;INTERVAL=2'

    >>> p = 'FREQ=YEARLY;INTERVAL=2;BYMONTH=1;BYDAY=-SU;BYHOUR=8,9;BYMINUTE=30'
    >>> r = vRecur.from_ical(p)
    >>> r
    ... # doctest: +NORMALIZE_WHITESPACE
    {'BYHOUR': [8, 9], 'BYDAY': ['-SU'], 'BYMINUTE': [30], 'BYMONTH': [1],
    'FREQ': ['YEARLY'], 'INTERVAL': [2]}

    >>> vRecur(r).to_ical()
    'FREQ=YEARLY;INTERVAL=2;BYMINUTE=30;BYHOUR=8,9;BYDAY=-SU;BYMONTH=1'

    Some examples from the spec

    >>> r = vRecur.from_ical('FREQ=MONTHLY;BYDAY=MO,TU,WE,TH,FR;BYSETPOS=-1')
    >>> vRecur(r).to_ical()
    'FREQ=MONTHLY;BYDAY=MO,TU,WE,TH,FR;BYSETPOS=-1'

    >>> p = 'FREQ=YEARLY;INTERVAL=2;BYMONTH=1;BYDAY=SU;BYHOUR=8,9;BYMINUTE=30'
    >>> r = vRecur.from_ical(p)
    >>> vRecur(r).to_ical()
    'FREQ=YEARLY;INTERVAL=2;BYMINUTE=30;BYHOUR=8,9;BYDAY=SU;BYMONTH=1'

    and some errors
    >>> r = vRecur.from_ical('BYDAY=12')
    Traceback (most recent call last):
        ...
    ValueError: Error in recurrence rule: BYDAY=12
    """

    frequencies = ["SECONDLY",  "MINUTELY", "HOURLY", "DAILY", "WEEKLY",
                   "MONTHLY", "YEARLY"]

    # Mac iCal ignores RRULEs where FREQ is not the first rule part.
    # Sorts parts according to the order listed in RFC 5545, section 3.3.10.
    canonical_order = ( "FREQ", "UNTIL", "COUNT", "INTERVAL",
                        "BYSECOND", "BYMINUTE", "BYHOUR", "BYDAY",
                        "BYMONTHDAY", "BYYEARDAY", "BYWEEKNO", "BYMONTH",
                        "BYSETPOS", "WKST" )

    types = CaselessDict({
        'COUNT':vInt,
        'INTERVAL':vInt,
        'BYSECOND':vInt,
        'BYMINUTE':vInt,
        'BYHOUR':vInt,
        'BYMONTHDAY':vInt,
        'BYYEARDAY':vInt,
        'BYMONTH':vInt,
        'UNTIL':vDDDTypes,
        'BYSETPOS':vInt,
        'WKST':vWeekday,
        'BYDAY':vWeekday,
        'FREQ':vFrequency
    })

    def __init__(self, *args, **kwargs):
        CaselessDict.__init__(self, *args, **kwargs)
        self.params = Parameters()

    def to_ical(self):
        # SequenceTypes
        result = []
        for key, vals in self.sorted_items():
            typ = self.types[key]
            if not type(vals) in SequenceTypes:
                vals = [vals]
            vals = ','.join([typ(val).to_ical() for val in vals])
            result.append('%s=%s' % (key, vals))
        return ';'.join(result)

    def parse_type(key, values):
        # integers
        parser = vRecur.types.get(key, vText)
        return [parser.from_ical(v) for v in values.split(',')]
    parse_type = staticmethod(parse_type)

    def from_ical(ical):
        "Parses the data format from ical text format"
        try:
            recur = vRecur()
            for pairs in ical.split(';'):
                key, vals = pairs.split('=')
                recur[key] = vRecur.parse_type(key, vals)
            return dict(recur)
        except:
            raise ValueError, 'Error in recurrence rule: %s' % ical

    from_ical = staticmethod(from_ical)


class vText(unicode):
    """Simple text.

    >>> t = vText(u'Simple text')
    >>> t.to_ical()
    'Simple text'

    Escaped text
    >>> t = vText('Text ; with escaped, chars')
    >>> t.to_ical()
    'Text \\\\; with escaped\\\\, chars'

    Escaped newlines
    >>> vText('Text with escaped\N chars').to_ical()
    'Text with escaped\\\\n chars'

    If you pass a unicode object, it will be utf-8 encoded. As this is the
    (only) standard that RFC 2445 support.

    >>> t = vText(u'international chars \xe4\xf6\xfc')
    >>> t.to_ical()
    'international chars \\xc3\\xa4\\xc3\\xb6\\xc3\\xbc'

    and parsing?
    >>> vText.from_ical('Text \\; with escaped\\, chars')
    u'Text ; with escaped, chars'

    >>> print vText.from_ical('A string with\\; some\\\\ characters in\\Nit')
    A string with; some\\ characters in
    it

    We are forgiving to utf-8 encoding errors:
    >>> # We intentionally use a string with unexpected encoding
    >>> t = vText.from_ical('Ol\\xe9')
    >>> t
    u'Ol\\ufffd'

    Notice how accented E character, encoded with latin-1, got replaced
    with the official U+FFFD REPLACEMENT CHARACTER.
    """

    encoding = DEFAULT_ENCODING

    def __new__(cls, value, encoding=DEFAULT_ENCODING):
        if isinstance(value, unicode):
            value = value.encode(DEFAULT_ENCODING)
        self = super(vText, cls).__new__(cls, value, encoding=encoding)
        self.encoding = encoding
        self.params = Parameters()
        return self

    def escape(self):
        """
        Format value according to iCalendar TEXT escaping rules.
        """
        return (self.replace('\N', '\n')
                    .replace('\\', '\\\\')
                    .replace(';', r'\;')
                    .replace(',', r'\,')
                    .replace('\r\n', r'\n')
                    .replace('\n', r'\n')
                )

    def __repr__(self):
        return u"vText(%s)" % unicode.__repr__(self)

    def to_ical(self):
        return self.escape().encode(self.encoding)

    def from_ical(ical):
        "Parses the data format from ical text format"
        try:
            ical = (ical.replace(r'\N', r'\n')
                        .replace(r'\r\n', '\n')
                        .replace(r'\n', '\n')
                        .replace(r'\,', ',')
                        .replace(r'\;', ';')
                        .replace('\\\\', '\\'))
            return ical.decode(vText.encoding, 'replace')
        except:
            raise ValueError, 'Expected ical text, got: %s' % ical

    from_ical = staticmethod(from_ical)


class vTime(time):
    """A subclass of datetime, that renders itself in the iCalendar time
    format.

    >>> dt = vTime(12, 30, 0)
    >>> dt.to_ical()
    '123000'

    >>> vTime.from_ical('123000')
    datetime.time(12, 30)

    We should also fail, right?
    >>> vTime.from_ical('263000')
    Traceback (most recent call last):
        ...
    ValueError: Expected time, got: 263000
    """

    def __new__(cls, *args, **kwargs):
        self = super(vTime, cls).__new__(cls, *args, **kwargs)
        self.params = Parameters()
        return self

    def to_ical(self):
        return self.strftime("%H%M%S")

    def from_ical(ical):
        "Parses the data format from ical text format"
        try:
            timetuple = map(int, (ical[:2],ical[2:4],ical[4:6]))
            return time(*timetuple)
        except:
            raise ValueError, 'Expected time, got: %s' % ical

    from_ical = staticmethod(from_ical)


class vUri(str):
    """Uniform resource identifier is basically just an unquoted string.

    >>> u = vUri('http://www.example.com/')
    >>> u.to_ical()
    'http://www.example.com/'
    >>> vUri.from_ical('http://www.example.com/') # doh!
    'http://www.example.com/'
    """

    def __new__(cls, *args, **kwargs):
        self = super(vUri, cls).__new__(cls, *args, **kwargs)
        self.params = Parameters()
        return self

    def to_ical(self):
        return str(self)

    def from_ical(ical):
        "Parses the data format from ical text format"
        try:
            return str(ical)
        except:
            raise ValueError, 'Expected , got: %s' % ical

    from_ical = staticmethod(from_ical)


class vGeo:
    """A special type that is only indirectly defined in the rfc.

    >>> g = vGeo((1.2, 3.0))
    >>> g.to_ical()
    '1.2;3.0'

    >>> g = vGeo.from_ical('37.386013;-122.082932')
    >>> g == (float('37.386013'), float('-122.082932'))
    True

    >>> vGeo(g).to_ical()
    '37.386013;-122.082932'

    >>> vGeo('g').to_ical()
    Traceback (most recent call last):
        ...
    ValueError: Input must be (float, float) for latitude and longitude
    """

    def __init__(self, geo):
        try:
            latitude, longitude = geo
            latitude = float(latitude)
            longitude = float(longitude)
        except:
            raise ValueError('Input must be (float, float) for '
                             'latitude and longitude')
        self.latitude = latitude
        self.longitude = longitude
        self.params = Parameters()

    def to_ical(self):
        return '%s;%s' % (self.latitude, self.longitude)

    def from_ical(ical):
        "Parses the data format from ical text format"
        try:
            latitude, longitude = ical.split(';')
            return (float(latitude), float(longitude))
        except:
            raise ValueError, "Expected 'float;float' , got: %s" % ical

    from_ical = staticmethod(from_ical)


class vUTCOffset:
    """Renders itself as a utc offset.

    >>> u = vUTCOffset(timedelta(hours=2))
    >>> u.to_ical()
    '+0200'

    >>> u = vUTCOffset(timedelta(hours=-5))
    >>> u.to_ical()
    '-0500'

    >>> u = vUTCOffset(timedelta())
    >>> u.to_ical()
    '+0000'

    >>> u = vUTCOffset(timedelta(minutes=-30))
    >>> u.to_ical()
    '-0030'

    >>> u = vUTCOffset(timedelta(hours=2, minutes=-30))
    >>> u.to_ical()
    '+0130'

    >>> u = vUTCOffset(timedelta(hours=1, minutes=30))
    >>> u.to_ical()
    '+0130'

    Parsing

    >>> vUTCOffset.from_ical('0000')
    datetime.timedelta(0)

    >>> vUTCOffset.from_ical('-0030')
    datetime.timedelta(-1, 84600)

    >>> vUTCOffset.from_ical('+0200')
    datetime.timedelta(0, 7200)

    >>> vUTCOffset.from_ical('+023040')
    datetime.timedelta(0, 9040)

    >>> o = vUTCOffset.from_ical('+0230')
    >>> vUTCOffset(o).to_ical()
    '+0230'

    And a few failures
    >>> vUTCOffset.from_ical('+323k')
    Traceback (most recent call last):
        ...
    ValueError: Expected utc offset, got: +323k

    >>> vUTCOffset.from_ical('+2400')
    Traceback (most recent call last):
        ...
    ValueError: Offset must be less than 24 hours, was +2400
    """

    def __init__(self, td):
        if not isinstance(td, timedelta):
            raise ValueError('Offset value MUST be a timedelta instance')
        self.td = td
        self.params = Parameters()

    def to_ical(self):
        td = self.td
        day_in_minutes = (td.days * 24 * 60)
        seconds_in_minutes = td.seconds // 60
        total_minutes = day_in_minutes + seconds_in_minutes
        if total_minutes == 0:
            sign = '+%s' # Google Calendar rejects '0000' but accepts '+0000'
        elif total_minutes < 0:
            sign = '-%s'
        else:
            sign = '+%s'
        hours = abs(total_minutes) // 60
        minutes = total_minutes % 60
        duration = '%02i%02i' % (hours, minutes)
        return sign % duration

    def from_ical(ical):
        "Parses the data format from ical text format"
        if isinstance(ical, vUTCOffset):
            return ical.td
        try:
            sign, hours, minutes, seconds = (ical[0:1],
                                             int(ical[1:3]),
                                             int(ical[3:5]),
                                             int(ical[5:7] or 0))
            offset = timedelta(hours=hours, minutes=minutes, seconds=seconds)
        except:
            raise ValueError, 'Expected utc offset, got: %s' % ical
        if offset >= timedelta(hours=24):
            raise ValueError, 'Offset must be less than 24 hours, was %s' % ical
        if sign == '-':
            return -offset
        return offset

    from_ical = staticmethod(from_ical)


class vInline(str):
    """This is an especially dumb class that just holds raw unparsed text and
    has parameters. Conversion of inline values are handled by the Component
    class, so no further processing is needed.

    >>> vInline('Some text')
    'Some text'

    >>> vInline.from_ical('Some text')
    'Some text'

    >>> t2 = vInline('other text')
    >>> t2.params['cn'] = 'Test Osterone'
    >>> t2.params
    Parameters({'CN': 'Test Osterone'})
    """

    def __init__(self,obj):
        self.obj = obj
        self.params = Parameters()

    def to_ical(self):
        return str(self)

    def from_ical(ical):
        return str(ical)

    from_ical = staticmethod(from_ical)


class TypesFactory(CaselessDict):
    """All Value types defined in rfc 2445 are registered in this factory
    class.

    To get a type you can use it like this.
    >>> factory = TypesFactory()
    >>> datetime_parser = factory['date-time']
    >>> dt = datetime_parser(datetime(2001, 1, 1))
    >>> dt.to_ical()
    '20010101T000000'

    A typical use is when the parser tries to find a content type and use text
    as the default
    >>> value = '20050101T123000'
    >>> value_type = 'date-time'
    >>> typ = factory.get(value_type, 'text')
    >>> typ.from_ical(value)
    datetime.datetime(2005, 1, 1, 12, 30)

    It can also be used to directly encode property and parameter values
    >>> comment = factory.to_ical('comment', u'by Rasmussen, Max M\xfcller')
    >>> str(comment)
    'by Rasmussen\\\\, Max M\\xc3\\xbcller'
    >>> factory.to_ical('priority', 1)
    '1'
    >>> factory.to_ical('cn', u'Rasmussen, Max M\xfcller')
    'Rasmussen\\\\, Max M\\xc3\\xbcller'

    >>> factory.from_ical('cn', 'Rasmussen\\\\, Max M\\xc3\\xb8ller')
    u'Rasmussen, Max M\\xf8ller'

    The value and parameter names don't overlap. So one factory is enough for
    both kinds.
    """

    def __init__(self, *args, **kwargs):
        "Set keys to upper for initial dict"
        CaselessDict.__init__(self, *args, **kwargs)
        self['binary'] = vBinary
        self['boolean'] = vBoolean
        self['cal-address'] = vCalAddress
        self['date'] = vDDDTypes
        self['date-time'] = vDDDTypes
        self['duration'] = vDDDTypes
        self['float'] = vFloat
        self['integer'] = vInt
        self['period'] = vPeriod
        self['recur'] = vRecur
        self['text'] = vText
        self['time'] = vTime
        self['uri'] = vUri
        self['utc-offset'] = vUTCOffset
        self['geo'] = vGeo
        self['inline'] = vInline
        self['date-time-list'] = vDDDLists

    #################################################
    # Property types

    # These are the default types
    types_map = CaselessDict({
        ####################################
        # Property value types
        # Calendar Properties
        'calscale' : 'text',
        'method' : 'text',
        'prodid' : 'text',
        'version' : 'text',
        # Descriptive Component Properties
        'attach' : 'uri',
        'categories' : 'text',
        'class' : 'text',
        'comment' : 'text',
        'description' : 'text',
        'geo' : 'geo',
        'location' : 'text',
        'percent-complete' : 'integer',
        'priority' : 'integer',
        'resources' : 'text',
        'status' : 'text',
        'summary' : 'text',
        # Date and Time Component Properties
        'completed' : 'date-time',
        'dtend' : 'date-time',
        'due' : 'date-time',
        'dtstart' : 'date-time',
        'duration' : 'duration',
        'freebusy' : 'period',
        'transp' : 'text',
        # Time Zone Component Properties
        'tzid' : 'text',
        'tzname' : 'text',
        'tzoffsetfrom' : 'utc-offset',
        'tzoffsetto' : 'utc-offset',
        'tzurl' : 'uri',
        # Relationship Component Properties
        'attendee' : 'cal-address',
        'contact' : 'text',
        'organizer' : 'cal-address',
        'recurrence-id' : 'date-time',
        'related-to' : 'text',
        'url' : 'uri',
        'uid' : 'text',
        # Recurrence Component Properties
        'exdate' : 'date-time-list',
        'exrule' : 'recur',
        'rdate' : 'date-time-list',
        'rrule' : 'recur',
        # Alarm Component Properties
        'action' : 'text',
        'repeat' : 'integer',
        'trigger' : 'duration',
        # Change Management Component Properties
        'created' : 'date-time',
        'dtstamp' : 'date-time',
        'last-modified' : 'date-time',
        'sequence' : 'integer',
        # Miscellaneous Component Properties
        'request-status' : 'text',
        ####################################
        # parameter types (luckily there is no name overlap)
        'altrep' : 'uri',
        'cn' : 'text',
        'cutype' : 'text',
        'delegated-from' : 'cal-address',
        'delegated-to' : 'cal-address',
        'dir' : 'uri',
        'encoding' : 'text',
        'fmttype' : 'text',
        'fbtype' : 'text',
        'language' : 'text',
        'member' : 'cal-address',
        'partstat' : 'text',
        'range' : 'text',
        'related' : 'text',
        'reltype' : 'text',
        'role' : 'text',
        'rsvp' : 'boolean',
        'sent-by' : 'cal-address',
        'tzid' : 'text',
        'value' : 'text',
    })

    def for_property(self, name):
        """Returns a the default type for a property or parameter
        """
        return self[self.types_map.get(name, 'text')]

    def to_ical(self, name, value):
        """Encodes a named value from a primitive python type to an icalendar
        encoded string.
        """
        type_class = self.for_property(name)
        return type_class(value).to_ical()

    def from_ical(self, name, value):
        """Decodes a named property or parameter value from an icalendar
        encoded string to a primitive python type.
        """
        type_class = self.for_property(name)
        decoded = type_class.from_ical(value)
        return decoded
