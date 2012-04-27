# -*- coding: latin-1 -*-

"""

This module contains the parser/generators (or coders/encoders if you prefer)
for the classes/datatypes that are used in Icalendar:

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
defines these types, calling val.ical() on them, Will render them as defined in
rfc2445.

If you pass any of these classes a Python primitive, you will have an object
that can render itself as iCalendar formatted date.

Property Value Data Types starts with a 'v'. they all have an ical() and
from_ical() method. The ical() method generates a text string in the iCalendar
format. The from_ical() method can parse this format and return a primitive
Python datatype. So it should allways be true that:

    x == vDataType.from_ical(VDataType(x).ical())

These types are mainly used for parsing and file generation. But you can set
them directly.

"""

# from python >= 2.3
from datetime import datetime, timedelta, time, date, tzinfo
from types import TupleType, ListType
SequenceTypes = [TupleType, ListType]
import re
import time as _time
import binascii

# from this package
from lib.icalendar.caselessdict import CaselessDict
from lib.icalendar.parser import Parameters

DATE_PART = r'(\d+)D'
TIME_PART = r'T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
DATETIME_PART = '(?:%s)?(?:%s)?' % (DATE_PART, TIME_PART)
WEEKS_PART = r'(\d+)W'
DURATION_REGEX = re.compile(r'([-+]?)P(?:%s|%s)$'
                            % (WEEKS_PART, DATETIME_PART))
WEEKDAY_RULE = re.compile('(?P<signal>[+-]?)(?P<relative>[\d]?)'
                          '(?P<weekday>[\w]{2})$')

class vBinary:
    """
    Binary property values are base 64 encoded
    >>> b = vBinary('This is gibberish')
    >>> b.ical()
    'VGhpcyBpcyBnaWJiZXJpc2g='
    >>> b = vBinary.from_ical('VGhpcyBpcyBnaWJiZXJpc2g=')
    >>> b
    'This is gibberish'

    The roundtrip test
    >>> x = 'Binary data æ ø å \x13 \x56'
    >>> vBinary(x).ical()
    'QmluYXJ5IGRhdGEg5iD4IOUgEyBW'
    >>> vBinary.from_ical('QmluYXJ5IGRhdGEg5iD4IOUgEyBW')
    'Binary data \\xe6 \\xf8 \\xe5 \\x13 V'

    >>> b = vBinary('txt')
    >>> b.params
    Parameters({'VALUE': 'BINARY', 'ENCODING': 'BASE64'})

    Long data should not have line breaks, as that would interfere
    >>> x = 'a'*99
    >>> vBinary(x).ical() == 'YWFh' * 33
    True
    >>> vBinary.from_ical('YWFh' * 33) == 'a' * 99
    True
    
    """

    def __init__(self, obj):
        self.obj = obj
        self.params = Parameters(encoding='BASE64', value="BINARY")

    def __repr__(self):
        return "vBinary(%s)" % str.__repr__(self.obj)

    def ical(self):
        return binascii.b2a_base64(self.obj)[:-1]

    def from_ical(ical):
        "Parses the data format from ical text format"
        try:
            return ical.decode('base-64')
        except:
            raise ValueError, 'Not valid base 64 encoding.'
    from_ical = staticmethod(from_ical)

    def __str__(self):
        return self.ical()



class vBoolean(int):
    """
    Returns specific string according to state
    >>> bin = vBoolean(True)
    >>> bin.ical()
    'TRUE'
    >>> bin = vBoolean(0)
    >>> bin.ical()
    'FALSE'

    The roundtrip test
    >>> x = True
    >>> x == vBoolean.from_ical(vBoolean(x).ical())
    True
    >>> vBoolean.from_ical('true')
    True
    """

    def __new__(cls, *args, **kwargs):
        self = super(vBoolean, cls).__new__(cls, *args, **kwargs)
        self.params = Parameters()
        return self

    def ical(self):
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

    def __str__(self):
        return self.ical()



class vCalAddress(str):
    """
    This just returns an unquoted string
    >>> a = vCalAddress('MAILTO:maxm@mxm.dk')
    >>> a.params['cn'] = 'Max M'
    >>> a.ical()
    'MAILTO:maxm@mxm.dk'
    >>> str(a)
    'MAILTO:maxm@mxm.dk'
    >>> a.params
    Parameters({'CN': 'Max M'})
    >>> vCalAddress.from_ical('MAILTO:maxm@mxm.dk')
    'MAILTO:maxm@mxm.dk'
    """

    def __new__(cls, *args, **kwargs):
        self = super(vCalAddress, cls).__new__(cls, *args, **kwargs)
        self.params = Parameters()
        return self

    def __repr__(self):
        return u"vCalAddress(%s)" % str.__repr__(self)

    def ical(self):
        return str(self)

    def from_ical(ical):
        "Parses the data format from ical text format"
        try:
            return str(ical)
        except:
            raise ValueError, 'Expected vCalAddress, got: %s' % ical
    from_ical = staticmethod(from_ical)

    def __str__(self):
        return str.__str__(self)

####################################################
# handy tzinfo classes you can use.

ZERO = timedelta(0)
HOUR = timedelta(hours=1)
STDOFFSET = timedelta(seconds = -_time.timezone)
if _time.daylight:
    DSTOFFSET = timedelta(seconds = -_time.altzone)
else:
    DSTOFFSET = STDOFFSET
DSTDIFF = DSTOFFSET - STDOFFSET


class FixedOffset(tzinfo):
    """Fixed offset in minutes east from UTC."""

    def __init__(self, offset, name):
        self.__offset = timedelta(minutes = offset)
        self.__name = name

    def utcoffset(self, dt):
        return self.__offset

    def tzname(self, dt):
        return self.__name

    def dst(self, dt):
        return ZERO


class Utc(tzinfo):
    """UTC tzinfo subclass"""

    def utcoffset(self, dt):
        return ZERO

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return ZERO
UTC = Utc()

class LocalTimezone(tzinfo):
    """
    Timezone of the machine where the code is running
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

####################################################



class vDatetime:
    """
    Render and generates iCalendar datetime format.

    Important: if tzinfo is defined it renders itself as "date with utc time"
    Meaning that it has a 'Z' appended, and is in absolute time.

    >>> d = datetime(2001, 1,1, 12, 30, 0)

    >>> dt = vDatetime(d)
    >>> dt.ical()
    '20010101T123000'

    >>> vDatetime.from_ical('20000101T120000')
    datetime.datetime(2000, 1, 1, 12, 0)

    >>> dutc = datetime(2001, 1,1, 12, 30, 0, tzinfo=UTC)
    >>> vDatetime(dutc).ical()
    '20010101T123000Z'

    >>> vDatetime.from_ical('20010101T000000')
    datetime.datetime(2001, 1, 1, 0, 0)

    >>> vDatetime.from_ical('20010101T000000A')
    Traceback (most recent call last):
      ...
    ValueError: Wrong datetime format: 20010101T000000A

    >>> utc = vDatetime.from_ical('20010101T000000Z')
    >>> vDatetime(utc).ical()
    '20010101T000000Z'
    """

    def __init__(self, dt):
        self.dt = dt
        self.params = Parameters()

    def ical(self):
        if self.dt.tzinfo:
            utc_time = self.dt - self.dt.tzinfo.utcoffset(datetime.now())
            return utc_time.strftime("%Y%m%dT%H%M%SZ")
        return self.dt.strftime("%Y%m%dT%H%M%S")

    def from_ical(ical):
        "Parses the data format from ical text format"
        try:
            timetuple = map(int, ((
                ical[:4],       # year
                ical[4:6],      # month
                ical[6:8],      # day
                ical[9:11],     # hour
                ical[11:13],    # minute
                ical[13:15],    # second
                )))
            if not ical[15:]:
                return datetime(*timetuple)
            elif ical[15:16] == 'Z':
                timetuple += [0, UTC]
                return datetime(*timetuple)
            else:
                raise ValueError, ical
        except:
            raise ValueError, 'Wrong datetime format: %s' % ical
    from_ical = staticmethod(from_ical)

    def __str__(self):
        return self.ical()



class vDate:
    """
    Render and generates iCalendar date format.
    >>> d = date(2001, 1,1)
    >>> vDate(d).ical()
    '20010101'

    >>> vDate.from_ical('20010102')
    datetime.date(2001, 1, 2)

    >>> vDate('d').ical()
    Traceback (most recent call last):
        ...
    ValueError: Value MUST be a date instance
    """

    def __init__(self, dt):
        if not isinstance(dt, date):
            raise ValueError('Value MUST be a date instance')
        self.dt = dt

    def ical(self):
        return self.dt.strftime("%Y%m%d")

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

    def __str__(self):
        return self.ical()



class vDuration:
    """
    Subclass of timedelta that renders itself in the iCalendar DURATION format.

    >>> vDuration(timedelta(11)).ical()
    'P11D'
    >>> vDuration(timedelta(-14)).ical()
    '-P14D'
    >>> vDuration(timedelta(1, 7384)).ical()
    'P1DT2H3M4S'
    >>> vDuration(timedelta(1, 7380)).ical()
    'P1DT2H3M'
    >>> vDuration(timedelta(1, 7200)).ical()
    'P1DT2H'
    >>> vDuration(timedelta(0, 7200)).ical()
    'PT2H'
    >>> vDuration(timedelta(0, 7384)).ical()
    'PT2H3M4S'
    >>> vDuration(timedelta(0, 184)).ical()
    'PT3M4S'
    >>> vDuration(timedelta(0, 22)).ical()
    'PT22S'
    >>> vDuration(timedelta(0, 3622)).ical()
    'PT1H0M22S'
    
    >>> vDuration(timedelta(days=1, hours=5)).ical()
    'P1DT5H'
    >>> vDuration(timedelta(hours=-5)).ical()
    '-PT5H'
    >>> vDuration(timedelta(days=-1, hours=-5)).ical()
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

    def ical(self):
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
        """
        Parses the data format from ical text format.
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

    def __str__(self):
        return self.ical()



class vFloat(float):
    """
    Just a float.
    >>> f = vFloat(1.0)
    >>> f.ical()
    '1.0'
    >>> vFloat.from_ical('42')
    42.0
    >>> vFloat(42).ical()
    '42.0'
    """

    def __new__(cls, *args, **kwargs):
        self = super(vFloat, cls).__new__(cls, *args, **kwargs)
        self.params = Parameters()
        return self

    def ical(self):
        return str(self)

    def from_ical(ical):
        "Parses the data format from ical text format"
        try:
            return float(ical)
        except:
            raise ValueError, 'Expected float value, got: %s' % ical
    from_ical = staticmethod(from_ical)



class vInt(int):
    """
    Just an int.
    >>> f = vInt(42)
    >>> f.ical()
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

    def ical(self):
        return str(self)

    def from_ical(ical):
        "Parses the data format from ical text format"
        try:
            return int(ical)
        except:
            raise ValueError, 'Expected int, got: %s' % ical
    from_ical = staticmethod(from_ical)



class vDDDTypes:
    """
    A combined Datetime, Date or Duration parser/generator. Their format cannot
    be confused, and often values can be of either types. So this is practical.

    >>> d = vDDDTypes.from_ical('20010101T123000')
    >>> type(d)
    <type 'datetime.datetime'>

    >>> repr(vDDDTypes.from_ical('20010101T123000Z'))[:65]
    'datetime.datetime(2001, 1, 1, 12, 30, tzinfo=<icalendar.prop.Utc '

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
        wrong_type_used = 1
        for typ in (datetime, date, timedelta):
            if isinstance(dt, typ):
                wrong_type_used = 0
        if wrong_type_used:
            raise ValueError ('You must use datetime, date or timedelta')

        self.dt = dt

    def ical(self):
        dt = self.dt
        if isinstance(dt, datetime):
            return vDatetime(dt).ical()
        elif isinstance(dt, date):
            return vDate(dt).ical()
        elif isinstance(dt, timedelta):
            return vDuration(dt).ical()
        else:
            raise ValueError('Unknown date type')

    def from_ical(ical):
        "Parses the data format from ical text format"
        u = ical.upper()
        if u.startswith('-P') or u.startswith('P'):
            return vDuration.from_ical(ical)
        try:
            return vDatetime.from_ical(ical)
        except:
            return vDate.from_ical(ical)
    from_ical = staticmethod(from_ical)

    def __str__(self):
        return self.ical()


class vDDDLists:
    """
    A list of vDDDTypes values.
    
    >>> dt_list = vDDDLists.from_ical('19960402T010000Z')
    >>> type(dt_list)
    <type 'list'>
    
    >>> len(dt_list)
    1
    
    >>> type(dt_list[0])
    <type 'datetime.datetime'>
        
    >>> str(dt_list[0])
    '1996-04-02 01:00:00+00:00'
    
    >>> dt_list = vDDDLists.from_ical('19960402T010000Z,19960403T010000Z,19960404T010000Z')
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
    >>> str(dt_list)
    ''
    
    >>> dt_list = vDDDLists([datetime(2000,1,1)])
    >>> str(dt_list)
    '20000101T000000'
        
    >>> dt_list = vDDDLists([datetime(2000,1,1), datetime(2000,11,11)])
    >>> str(dt_list)
    '20000101T000000,20001111T000000'
    """
    
    def __init__(self, dt_list):
        if not isinstance(dt_list, list):
            raise ValueError('Value MUST be a list (of date instances)')        
        vDDD = []
        for dt in dt_list:
            vDDD.append(vDDDTypes(dt))
        self.dts = vDDD
    
    def ical(self):
        '''
        Generates the text string in the iCalendar format.
        '''
        dts_ical = [dt.ical() for dt in self.dts]
        return ",".join(dts_ical)
    
    def from_ical(ical):
        '''
        Parses the list of data formats from ical text format.
        @param ical: ical text format
        '''
        out = []
        ical_dates = ical.split(",")
        for ical_dt in ical_dates:
            out.append(vDDDTypes.from_ical(ical_dt))
        return out
    from_ical = staticmethod(from_ical)
    
    def __str__(self):
        return self.ical()
        

class vPeriod:
    """
    A precise period of time.
    One day in exact datetimes
    >>> per = (datetime(2000,1,1), datetime(2000,1,2))
    >>> p = vPeriod(per)
    >>> p.ical()
    '20000101T000000/20000102T000000'

    >>> per = (datetime(2000,1,1), timedelta(days=31))
    >>> p = vPeriod(per)
    >>> p.ical()
    '20000101T000000/P31D'

    Roundtrip
    >>> p = vPeriod.from_ical('20000101T000000/20000102T000000')
    >>> p
    (datetime.datetime(2000, 1, 1, 0, 0), datetime.datetime(2000, 1, 2, 0, 0))
    >>> vPeriod(p).ical()
    '20000101T000000/20000102T000000'

    >>> vPeriod.from_ical('20000101T000000/P31D')
    (datetime.datetime(2000, 1, 1, 0, 0), datetime.timedelta(31))

    Roundtrip with absolute time
    >>> p = vPeriod.from_ical('20000101T000000Z/20000102T000000Z')
    >>> vPeriod(p).ical()
    '20000101T000000Z/20000102T000000Z'

    And an error
    >>> vPeriod.from_ical('20000101T000000/Psd31D')
    Traceback (most recent call last):
        ...
    ValueError: Expected period format, got: 20000101T000000/Psd31D

    Utc datetime
    >>> da_tz = FixedOffset(+1.0, 'da_DK')
    >>> start = datetime(2000,1,1, tzinfo=da_tz)
    >>> end = datetime(2000,1,2, tzinfo=da_tz)
    >>> per = (start, end)
    >>> vPeriod(per).ical()
    '19991231T235900Z/20000101T235900Z'

    >>> p = vPeriod((datetime(2000,1,1, tzinfo=da_tz), timedelta(days=31)))
    >>> p.ical()
    '19991231T235900Z/P31D'
    """

    def __init__(self, per):
        start, end_or_duration = per
        if not (isinstance(start, datetime) or isinstance(start, date)):
            raise ValueError('Start value MUST be a datetime or date instance')
        if not (isinstance(end_or_duration, datetime) or
                isinstance(end_or_duration, date) or
                isinstance(end_or_duration, timedelta)):
            raise ValueError('end_or_duration MUST be a datetime, date or timedelta instance')
        self.start = start
        self.end_or_duration = end_or_duration
        self.by_duration = 0
        if isinstance(end_or_duration, timedelta):
            self.by_duration = 1
            self.duration = end_or_duration
            self.end = self.start + self.duration
        else:
            self.end = end_or_duration
            self.duration = self.end - self.start
        if self.start > self.end:
            raise ValueError("Start time is greater than end time")
        self.params = Parameters()

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

    def ical(self):
        if self.by_duration:
            return '%s/%s' % (vDatetime(self.start).ical(), vDuration(self.duration).ical())
        return '%s/%s' % (vDatetime(self.start).ical(), vDatetime(self.end).ical())

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

    def __str__(self):
        return self.ical()

    def __repr__(self):
        if self.by_duration:
            p = (self.start, self.duration)
        else:
            p = (self.start, self.end)
        return 'vPeriod(%s)' % repr(p)

class vWeekday(str):
    """
    This returns an unquoted weekday abbrevation
    >>> a = vWeekday('mo')
    >>> a.ical()
    'MO'

    >>> a = vWeekday('erwer')
    Traceback (most recent call last):
        ...
    ValueError: Expected weekday abbrevation, got: ERWER

    >>> vWeekday.from_ical('mo')
    'MO'

    >>> vWeekday.from_ical('+3mo')
    '+3MO'

    >>> vWeekday.from_ical('Saturday')
    Traceback (most recent call last):
        ...
    ValueError: Expected weekday abbrevation, got: Saturday

    >>> a = vWeekday('+mo')
    >>> a.ical()
    '+MO'

    >>> a = vWeekday('+3mo')
    >>> a.ical()
    '+3MO'

    >>> a = vWeekday('-tu')
    >>> a.ical()
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

    def ical(self):
        return self.upper()

    def from_ical(ical):
        "Parses the data format from ical text format"
        try:
            return vWeekday(ical.upper())
        except:
            raise ValueError, 'Expected weekday abbrevation, got: %s' % ical
    from_ical = staticmethod(from_ical)

    def __str__(self):
        return self.ical()



class vFrequency(str):
    """
    A simple class that catches illegal values.
    >>> f = vFrequency('bad test')
    Traceback (most recent call last):
        ...
    ValueError: Expected frequency, got: BAD TEST
    >>> vFrequency('daily').ical()
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

    def ical(self):
        return self.upper()

    def from_ical(ical):
        "Parses the data format from ical text format"
        try:
            return vFrequency(ical.upper())
        except:
            raise ValueError, 'Expected weekday abbrevation, got: %s' % ical
    from_ical = staticmethod(from_ical)

    def __str__(self):
        return self.ical()



class vRecur(CaselessDict):
    """
    Let's see how close we can get to one from the rfc:
    FREQ=YEARLY;INTERVAL=2;BYMONTH=1;BYDAY=SU;BYHOUR=8,9;BYMINUTE=30

    >>> r = dict(freq='yearly', interval=2)
    >>> r['bymonth'] = 1
    >>> r['byday'] = 'su'
    >>> r['byhour'] = [8,9]
    >>> r['byminute'] = 30
    >>> r = vRecur(r)
    >>> r.ical()
    'BYHOUR=8,9;BYDAY=SU;BYMINUTE=30;BYMONTH=1;FREQ=YEARLY;INTERVAL=2'

    >>> r = vRecur(FREQ='yearly', INTERVAL=2)
    >>> r['BYMONTH'] = 1
    >>> r['BYDAY'] = 'su'
    >>> r['BYHOUR'] = [8,9]
    >>> r['BYMINUTE'] = 30
    >>> r.ical()
    'BYDAY=SU;BYMINUTE=30;BYMONTH=1;INTERVAL=2;FREQ=YEARLY;BYHOUR=8,9'

    >>> r = vRecur(freq='DAILY', count=10)
    >>> r['bysecond'] = [0, 15, 30, 45]
    >>> r.ical()
    'COUNT=10;FREQ=DAILY;BYSECOND=0,15,30,45'

    >>> r = vRecur(freq='DAILY', until=datetime(2005,1,1,12,0,0))
    >>> r.ical()
    'FREQ=DAILY;UNTIL=20050101T120000'

    How do we fare with regards to parsing?
    >>> r = vRecur.from_ical('FREQ=DAILY;INTERVAL=2;COUNT=10')
    >>> r
    {'COUNT': [10], 'FREQ': ['DAILY'], 'INTERVAL': [2]}
    >>> vRecur(r).ical()
    'COUNT=10;FREQ=DAILY;INTERVAL=2'

    >>> r = vRecur.from_ical('FREQ=YEARLY;INTERVAL=2;BYMONTH=1;BYDAY=-SU;BYHOUR=8,9;BYMINUTE=30')
    >>> r
    {'BYHOUR': [8, 9], 'BYDAY': ['-SU'], 'BYMINUTE': [30], 'BYMONTH': [1], 'FREQ': ['YEARLY'], 'INTERVAL': [2]}
    >>> vRecur(r).ical()
    'BYDAY=-SU;BYMINUTE=30;INTERVAL=2;BYMONTH=1;FREQ=YEARLY;BYHOUR=8,9'

    Some examples from the spec

    >>> r = vRecur.from_ical('FREQ=MONTHLY;BYDAY=MO,TU,WE,TH,FR;BYSETPOS=-1')
    >>> vRecur(r).ical()
    'BYSETPOS=-1;FREQ=MONTHLY;BYDAY=MO,TU,WE,TH,FR'

    >>> r = vRecur.from_ical('FREQ=YEARLY;INTERVAL=2;BYMONTH=1;BYDAY=SU;BYHOUR=8,9;BYMINUTE=30')
    >>> vRecur(r).ical()
    'BYDAY=SU;BYMINUTE=30;INTERVAL=2;BYMONTH=1;FREQ=YEARLY;BYHOUR=8,9'

    and some errors
    >>> r = vRecur.from_ical('BYDAY=12')
    Traceback (most recent call last):
        ...
    ValueError: Error in recurrence rule: BYDAY=12

    """

    frequencies = ["SECONDLY",  "MINUTELY", "HOURLY", "DAILY", "WEEKLY",
                   "MONTHLY", "YEARLY"]

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

    def ical(self):
        # SequenceTypes
        result = []
        for key, vals in self.items():
            typ = self.types[key]
            if not type(vals) in SequenceTypes:
                vals = [vals]
            vals = ','.join([typ(val).ical() for val in vals])
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

    def __str__(self):
        return self.ical()



class vText(unicode):
    """
    Simple text
    >>> t = vText(u'Simple text')
    >>> t.ical()
    'Simple text'

    Escaped text
    >>> t = vText('Text ; with escaped, chars')
    >>> t.ical()
    'Text \\\\; with escaped\\\\, chars'

    Escaped newlines
    >>> vText('Text with escaped\N chars').ical()
    'Text with escaped\\\\n chars'

    If you pass a unicode object, it will be utf-8 encoded. As this is the
    (only) standard that RFC 2445 support.

    >>> t = vText(u'international chars æøå ÆØÅ ü')
    >>> t.ical()
    'international chars \\xc3\\xa6\\xc3\\xb8\\xc3\\xa5 \\xc3\\x86\\xc3\\x98\\xc3\\x85 \\xc3\\xbc'

    Unicode is converted to utf-8
    >>> t = vText(u'international æ ø å')
    >>> str(t)
    'international \\xc3\\xa6 \\xc3\\xb8 \\xc3\\xa5'

    and parsing?
    >>> vText.from_ical('Text \\; with escaped\\, chars')
    u'Text ; with escaped, chars'

    >>> print vText.from_ical('A string with\\; some\\\\ characters in\\Nit')
    A string with; some\\ characters in
    it
    """

    encoding = 'utf-8'

    def __new__(cls, *args, **kwargs):
        self = super(vText, cls).__new__(cls, *args, **kwargs)
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

    def ical(self):
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
            return ical.decode(vText.encoding)
        except:
            raise ValueError, 'Expected ical text, got: %s' % ical
    from_ical = staticmethod(from_ical)

    def __str__(self):
        return self.ical()



class vTime(time):
    """
    A subclass of datetime, that renders itself in the iCalendar time
    format.
    >>> dt = vTime(12, 30, 0)
    >>> dt.ical()
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

    def ical(self):
        return self.strftime("%H%M%S")

    def from_ical(ical):
        "Parses the data format from ical text format"
        try:
            timetuple = map(int, (ical[:2],ical[2:4],ical[4:6]))
            return time(*timetuple)
        except:
            raise ValueError, 'Expected time, got: %s' % ical
    from_ical = staticmethod(from_ical)

    def __str__(self):
        return self.ical()



class vUri(str):
    """
    Uniform resource identifier is basically just an unquoted string.
    >>> u = vUri('http://www.example.com/')
    >>> u.ical()
    'http://www.example.com/'
    >>> vUri.from_ical('http://www.example.com/') # doh!
    'http://www.example.com/'
    """

    def __new__(cls, *args, **kwargs):
        self = super(vUri, cls).__new__(cls, *args, **kwargs)
        self.params = Parameters()
        return self

    def ical(self):
        return str(self)

    def from_ical(ical):
        "Parses the data format from ical text format"
        try:
            return str(ical)
        except:
            raise ValueError, 'Expected , got: %s' % ical
    from_ical = staticmethod(from_ical)

    def __str__(self):
        return str.__str__(self)



class vGeo:
    """
    A special type that is only indirectly defined in the rfc.

    >>> g = vGeo((1.2, 3.0))
    >>> g.ical()
    '1.2;3.0'

    >>> g = vGeo.from_ical('37.386013;-122.082932')
    >>> g
    (37.386012999999998, -122.082932)

    >>> vGeo(g).ical()
    '37.386013;-122.082932'

    >>> vGeo('g').ical()
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
            raise ValueError('Input must be (float, float) for latitude and longitude')
        self.latitude = latitude
        self.longitude = longitude
        self.params = Parameters()

    def ical(self):
        return '%s;%s' % (self.latitude, self.longitude)

    def from_ical(ical):
        "Parses the data format from ical text format"
        try:
            latitude, longitude = ical.split(';')
            return (float(latitude), float(longitude))
        except:
            raise ValueError, "Expected 'float;float' , got: %s" % ical
    from_ical = staticmethod(from_ical)

    def __str__(self):
        return self.ical()



class vUTCOffset:
    """
    Renders itself as a utc offset

    >>> u = vUTCOffset(timedelta(hours=2))
    >>> u.ical()
    '+0200'

    >>> u = vUTCOffset(timedelta(hours=-5))
    >>> u.ical()
    '-0500'

    >>> u = vUTCOffset(timedelta())
    >>> u.ical()
    '0000'

    >>> u = vUTCOffset(timedelta(minutes=-30))
    >>> u.ical()
    '-0030'

    >>> u = vUTCOffset(timedelta(hours=2, minutes=-30))
    >>> u.ical()
    '+0130'

    >>> u = vUTCOffset(timedelta(hours=1, minutes=30))
    >>> u.ical()
    '+0130'

    Parsing

    >>> vUTCOffset.from_ical('0000')
    datetime.timedelta(0)

    >>> vUTCOffset.from_ical('-0030')
    datetime.timedelta(-1, 84600)

    >>> vUTCOffset.from_ical('+0200')
    datetime.timedelta(0, 7200)

    >>> o = vUTCOffset.from_ical('+0230')
    >>> vUTCOffset(o).ical()
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

    def ical(self):
        td = self.td
        day_in_minutes = (td.days * 24 * 60)
        seconds_in_minutes = td.seconds // 60
        total_minutes = day_in_minutes + seconds_in_minutes
        if total_minutes == 0:
            sign = '%s'
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
        try:
            sign, hours, minutes = (ical[-5:-4], int(ical[-4:-2]), int(ical[-2:]))
            offset = timedelta(hours=hours, minutes=minutes)
        except:
            raise ValueError, 'Expected utc offset, got: %s' % ical
        if offset >= timedelta(hours=24):
            raise ValueError, 'Offset must be less than 24 hours, was %s' % ical
        if sign == '-':
            return -offset
        return offset
    from_ical = staticmethod(from_ical)

    def __str__(self):
        return self.ical()



class vInline(str):
    """
    This is an especially dumb class that just holds raw unparsed text and has
    parameters. Conversion of inline values are handled by the Component class,
    so no further processing is needed.

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

    def ical(self):
        return str(self)

    def from_ical(ical):
        return str(ical)
    from_ical = staticmethod(from_ical)

    def __str__(self):
        return str(self.obj)


class TypesFactory(CaselessDict):
    """
    All Value types defined in rfc 2445 are registered in this factory class. To
    get a type you can use it like this.
    >>> factory = TypesFactory()
    >>> datetime_parser = factory['date-time']
    >>> dt = datetime_parser(datetime(2001, 1, 1))
    >>> dt.ical()
    '20010101T000000'

    A typical use is when the parser tries to find a content type and use text
    as the default
    >>> value = '20050101T123000'
    >>> value_type = 'date-time'
    >>> typ = factory.get(value_type, 'text')
    >>> typ.from_ical(value)
    datetime.datetime(2005, 1, 1, 12, 30)

    It can also be used to directly encode property and parameter values
    >>> comment = factory.ical('comment', u'by Rasmussen, Max Møller')
    >>> str(comment)
    'by Rasmussen\\\\, Max M\\xc3\\xb8ller'
    >>> factory.ical('priority', 1)
    '1'
    >>> factory.ical('cn', u'Rasmussen, Max Møller')
    'Rasmussen\\\\, Max M\\xc3\\xb8ller'

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
        # parameter types (luckilly there is no name overlap)
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
        "Returns a the default type for a property or parameter"
        return self[self.types_map.get(name, 'text')]

    def ical(self, name, value):
        """
        Encodes a named value from a primitive python type to an
        icalendar encoded string.
        """
        type_class = self.for_property(name)
        return type_class(value).ical()

    def from_ical(self, name, value):
        """
        Decodes a named property or parameter value from an icalendar encoded
        string to a primitive python type.
        """
        type_class = self.for_property(name)
        decoded = type_class.from_ical(str(value))
        return decoded
