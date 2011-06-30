# -*- coding: latin-1 -*-

"""

Calendar is a dictionary like Python object that can render itself as VCAL
files according to rfc2445.

These are the defined components.

"""

# from python
from types import ListType, TupleType
SequenceTypes = (ListType, TupleType)

# from this package
from lib.icalendar.caselessdict import CaselessDict
from lib.icalendar.parser import Contentlines, Contentline, Parameters
from lib.icalendar.parser import q_split, q_join
from lib.icalendar.prop import TypesFactory, vText


######################################
# The component factory

class ComponentFactory(CaselessDict):
    """
    All components defined in rfc 2445 are registered in this factory class. To
    get a component you can use it like this.

    >>> factory = ComponentFactory()
    >>> component = factory['VEVENT']
    >>> event = component(dtstart='19700101')
    >>> event.as_string()
    'BEGIN:VEVENT\\r\\nDTSTART:19700101\\r\\nEND:VEVENT\\r\\n'

    >>> factory.get('VCALENDAR', Component)
    <class 'icalendar.cal.Calendar'>
    """

    def __init__(self, *args, **kwargs):
        "Set keys to upper for initial dict"
        CaselessDict.__init__(self, *args, **kwargs)
        self['VEVENT'] = Event
        self['VTODO'] = Todo
        self['VJOURNAL'] = Journal
        self['VFREEBUSY'] = FreeBusy
        self['VTIMEZONE'] = Timezone
        self['VALARM'] = Alarm
        self['VCALENDAR'] = Calendar


# These Properties have multiple property values inlined in one propertyline
# seperated by comma. Use CaselessDict as simple caseless set.
INLINE = CaselessDict(
    [(cat, 1) for cat in ('CATEGORIES', 'RESOURCES', 'FREEBUSY')]
)

_marker = []

class Component(CaselessDict):
    """
    Component is the base object for calendar, Event and the other components
    defined in RFC 2445. normally you will not use this class directy, but
    rather one of the subclasses.

    A component is like a dictionary with extra methods and attributes.
    >>> c = Component()
    >>> c.name = 'VCALENDAR'

    Every key defines a property. A property can consist of either a single
    item. This can be set with a single value
    >>> c['prodid'] = '-//max m//icalendar.mxm.dk/'
    >>> c
    VCALENDAR({'PRODID': '-//max m//icalendar.mxm.dk/'})

    or with a list
    >>> c['ATTENDEE'] = ['Max M', 'Rasmussen']

    if you use the add method you don't have to considder if a value is a list
    or not.
    >>> c = Component()
    >>> c.name = 'VEVENT'
    >>> c.add('attendee', 'maxm@mxm.dk')
    >>> c.add('attendee', 'test@example.dk')
    >>> c
    VEVENT({'ATTENDEE': [vCalAddress('maxm@mxm.dk'), vCalAddress('test@example.dk')]})

    You can get the values back directly
    >>> c.add('prodid', '-//my product//')
    >>> c['prodid']
    vText(u'-//my product//')

    or decoded to a python type
    >>> c.decoded('prodid')
    u'-//my product//'

    With default values for non existing properties
    >>> c.decoded('version', 'No Version')
    'No Version'

    The component can render itself in the RFC 2445 format.
    >>> c = Component()
    >>> c.name = 'VCALENDAR'
    >>> c.add('attendee', 'Max M')
    >>> c.as_string()
    'BEGIN:VCALENDAR\\r\\nATTENDEE:Max M\\r\\nEND:VCALENDAR\\r\\n'

    >>> from icalendar.prop import vDatetime

    Components can be nested, so You can add a subcompont. Eg a calendar holds events.
    >>> e = Component(summary='A brief history of time')
    >>> e.name = 'VEVENT'
    >>> e.add('dtend', '20000102T000000', encode=0)
    >>> e.add('dtstart', '20000101T000000', encode=0)
    >>> e.as_string()
    'BEGIN:VEVENT\\r\\nDTEND:20000102T000000\\r\\nDTSTART:20000101T000000\\r\\nSUMMARY:A brief history of time\\r\\nEND:VEVENT\\r\\n'

    >>> c.add_component(e)
    >>> c.subcomponents
    [VEVENT({'DTEND': '20000102T000000', 'DTSTART': '20000101T000000', 'SUMMARY': 'A brief history of time'})]

    We can walk over nested componentes with the walk method.
    >>> [i.name for i in c.walk()]
    ['VCALENDAR', 'VEVENT']

    We can also just walk over specific component types, by filtering them on
    their name.
    >>> [i.name for i in c.walk('VEVENT')]
    ['VEVENT']

    >>> [i['dtstart'] for i in c.walk('VEVENT')]
    ['20000101T000000']

    Text fields which span multiple mulitple lines require proper indenting
    >>> c = Calendar()
    >>> c['description']=u'Paragraph one\\n\\nParagraph two'
    >>> c.as_string()
    'BEGIN:VCALENDAR\\r\\nDESCRIPTION:Paragraph one\\r\\n \\r\\n Paragraph two\\r\\nEND:VCALENDAR\\r\\n'

    INLINE properties have their values on one property line. Note the double
    quoting of the value with a colon in it.
    >>> c = Calendar()
    >>> c['resources'] = 'Chair, Table, "Room: 42"'
    >>> c
    VCALENDAR({'RESOURCES': 'Chair, Table, "Room: 42"'})

    >>> c.as_string()
    'BEGIN:VCALENDAR\\r\\nRESOURCES:Chair, Table, "Room: 42"\\r\\nEND:VCALENDAR\\r\\n'

    The inline values must be handled by the get_inline() and set_inline()
    methods.

    >>> c.get_inline('resources', decode=0)
    ['Chair', 'Table', 'Room: 42']

    These can also be decoded
    >>> c.get_inline('resources', decode=1)
    [u'Chair', u'Table', u'Room: 42']

    You can set them directly
    >>> c.set_inline('resources', ['A', 'List', 'of', 'some, recources'], encode=1)
    >>> c['resources']
    'A,List,of,"some, recources"'

    and back again
    >>> c.get_inline('resources', decode=0)
    ['A', 'List', 'of', 'some, recources']

    >>> c['freebusy'] = '19970308T160000Z/PT3H,19970308T200000Z/PT1H,19970308T230000Z/19970309T000000Z'
    >>> c.get_inline('freebusy', decode=0)
    ['19970308T160000Z/PT3H', '19970308T200000Z/PT1H', '19970308T230000Z/19970309T000000Z']

    >>> freebusy = c.get_inline('freebusy', decode=1)
    >>> type(freebusy[0][0]), type(freebusy[0][1])
    (<type 'datetime.datetime'>, <type 'datetime.timedelta'>)
    """

    name = ''       # must be defined in each component
    required = ()   # These properties are required
    singletons = () # These properties must only appear once
    multiple = ()   # may occur more than once
    exclusive = ()  # These properties are mutually exclusive
    inclusive = ()  # if any occurs the other(s) MUST occur ('duration', 'repeat')

    def __init__(self, *args, **kwargs):
        "Set keys to upper for initial dict"
        CaselessDict.__init__(self, *args, **kwargs)
        # set parameters here for properties that use non-default values
        self.subcomponents = [] # Components can be nested.


#    def non_complience(self, warnings=0):
#        """
#        not implemented yet!
#        Returns a dict describing non compliant properties, if any.
#        If warnings is true it also returns warnings.
#
#        If the parser is too strict it might prevent parsing erroneous but
#        otherwise compliant properties. So the parser is pretty lax, but it is
#        possible to test for non-complience by calling this method.
#        """
#        nc = {}
#        if not getattr(self, 'name', ''):
#            nc['name'] = {'type':'ERROR', 'description':'Name is not defined'}
#        return nc


    #############################
    # handling of property values

    def _encode(self, name, value, cond=1):
        # internal, for conditional convertion of values.
        if cond:
            klass = types_factory.for_property(name)
            return klass(value)
        return value


    def set(self, name, value, encode=1):
        if type(value) == ListType:
            self[name] = [self._encode(name, v, encode) for v in value]
        else:
            self[name] = self._encode(name, value, encode)


    def add(self, name, value, encode=1):
        "If property exists append, else create and set it"
        if name in self:
            oldval = self[name]
            value = self._encode(name, value, encode)
            if type(oldval) == ListType:
                oldval.append(value)
            else:
                self.set(name, [oldval, value], encode=0)
        else:
            self.set(name, value, encode)


    def _decode(self, name, value):
        # internal for decoding property values
        decoded = types_factory.from_ical(name, value)
        return decoded


    def decoded(self, name, default=_marker):
        "Returns decoded value of property"
        if name in self:
            value = self[name]
            if type(value) == ListType:
                return [self._decode(name, v) for v in value]
            return self._decode(name, value)
        else:
            if default is _marker:
                raise KeyError, name
            else:
                return default


    ########################################################################
    # Inline values. A few properties have multiple values inlined in in one
    # property line. These methods are used for splitting and joining these.

    def get_inline(self, name, decode=1):
        """
        Returns a list of values (split on comma).
        """
        vals = [v.strip('" ').encode(vText.encoding)
                  for v in q_split(self[name])]
        if decode:
            return [self._decode(name, val) for val in vals]
        return vals


    def set_inline(self, name, values, encode=1):
        """
        Converts a list of values into comma seperated string and sets value to
        that.
        """
        if encode:
            values = [self._encode(name, value, 1) for value in values]
        joined = q_join(values).encode(vText.encoding)
        self[name] = types_factory['inline'](joined)


    #########################
    # Handling of components

    def add_component(self, component):
        "add a subcomponent to this component"
        self.subcomponents.append(component)


    def _walk(self, name):
        # private!
        result = []
        if name is None or self.name == name:
            result.append(self)
        for subcomponent in self.subcomponents:
            result += subcomponent._walk(name)
        return result


    def walk(self, name=None):
        """
        Recursively traverses component and subcomponents. Returns sequence of
        same. If name is passed, only components with name will be returned.
        """
        if not name is None:
            name = name.upper()
        return self._walk(name)

    #####################
    # Generation

    def property_items(self):
        """
        Returns properties in this component and subcomponents as:
        [(name, value), ...]
        """
        vText = types_factory['text']
        properties = [('BEGIN', vText(self.name).ical())]
        property_names = self.keys()
        for name in property_names:
            values = self[name]
            if type(values) == ListType:
                # normally one property is one line
                for value in values:
                    properties.append((name, value))
            else:
                properties.append((name, values))
        # recursion is fun!
        for subcomponent in self.subcomponents:
            properties += subcomponent.property_items()
        properties.append(('END', vText(self.name).ical()))
        return properties


    def from_string(st, multiple=False):
        """
        Populates the component recursively from a string
        """
        stack = [] # a stack of components
        comps = []
        for line in Contentlines.from_string(st): # raw parsing
            if not line:
                continue
            name, params, vals = line.parts()
            uname = name.upper()
            # check for start of component
            if uname == 'BEGIN':
                # try and create one of the components defined in the spec,
                # otherwise get a general Components for robustness.
                component_name = vals.upper()
                component_class = component_factory.get(component_name, Component)
                component = component_class()
                if not getattr(component, 'name', ''): # for undefined components
                    component.name = component_name
                stack.append(component)
            # check for end of event
            elif uname == 'END':
                # we are done adding properties to this component
                # so pop it from the stack and add it to the new top.
                component = stack.pop()
                if not stack: # we are at the end
                    comps.append(component)
                else:
                    stack[-1].add_component(component)
            # we are adding properties to the current top of the stack
            else:
                factory = types_factory.for_property(name)
                vals = factory(factory.from_ical(vals))
                vals.params = params
                stack[-1].add(name, vals, encode=0)
        if multiple:
            return comps
        if not len(comps) == 1:
            raise ValueError('Found multiple components where '
                             'only one is allowed')
        return comps[0]
    from_string = staticmethod(from_string)


    def __repr__(self):
        return '%s(' % self.name + dict.__repr__(self) + ')'

#    def content_line(self, name):
#        "Returns property as content line"
#        value = self[name]
#        params = getattr(value, 'params', Parameters())
#        return Contentline.from_parts((name, params, value))

    def content_lines(self):
        "Converts the Component and subcomponents into content lines"
        contentlines = Contentlines()
        for name, values in self.property_items():
            params = getattr(values, 'params', Parameters())
            contentlines.append(Contentline.from_parts((name, params, values)))
        contentlines.append('') # remember the empty string in the end
        return contentlines


    def as_string(self):
        return str(self.content_lines())


    def __str__(self):
        "Returns rendered iCalendar"
        return self.as_string()



#######################################
# components defined in RFC 2445


class Event(Component):

    name = 'VEVENT'

    required = ('UID',)
    singletons = (
        'CLASS', 'CREATED', 'DESCRIPTION', 'DTSTART', 'GEO',
        'LAST-MOD', 'LOCATION', 'ORGANIZER', 'PRIORITY', 'DTSTAMP', 'SEQUENCE',
        'STATUS', 'SUMMARY', 'TRANSP', 'URL', 'RECURID', 'DTEND', 'DURATION',
        'DTSTART',
    )
    exclusive = ('DTEND', 'DURATION', )
    multiple = (
        'ATTACH', 'ATTENDEE', 'CATEGORIES', 'COMMENT','CONTACT', 'EXDATE',
        'EXRULE', 'RSTATUS', 'RELATED', 'RESOURCES', 'RDATE', 'RRULE'
    )



class Todo(Component):

    name = 'VTODO'

    required = ('UID',)
    singletons = (
        'CLASS', 'COMPLETED', 'CREATED', 'DESCRIPTION', 'DTSTAMP', 'DTSTART',
        'GEO', 'LAST-MOD', 'LOCATION', 'ORGANIZER', 'PERCENT', 'PRIORITY',
        'RECURID', 'SEQUENCE', 'STATUS', 'SUMMARY', 'UID', 'URL', 'DUE', 'DURATION',
    )
    exclusive = ('DUE', 'DURATION',)
    multiple = (
        'ATTACH', 'ATTENDEE', 'CATEGORIES', 'COMMENT', 'CONTACT', 'EXDATE',
        'EXRULE', 'RSTATUS', 'RELATED', 'RESOURCES', 'RDATE', 'RRULE'
    )



class Journal(Component):

    name = 'VJOURNAL'

    required = ('UID',)
    singletons = (
        'CLASS', 'CREATED', 'DESCRIPTION', 'DTSTART', 'DTSTAMP', 'LAST-MOD',
        'ORGANIZER', 'RECURID', 'SEQUENCE', 'STATUS', 'SUMMARY', 'UID', 'URL',
    )
    multiple = (
        'ATTACH', 'ATTENDEE', 'CATEGORIES', 'COMMENT', 'CONTACT', 'EXDATE',
        'EXRULE', 'RELATED', 'RDATE', 'RRULE', 'RSTATUS',
    )


class FreeBusy(Component):

    name = 'VFREEBUSY'

    required = ('UID',)
    singletons = (
        'CONTACT', 'DTSTART', 'DTEND', 'DURATION', 'DTSTAMP', 'ORGANIZER',
        'UID', 'URL',
    )
    multiple = ('ATTENDEE', 'COMMENT', 'FREEBUSY', 'RSTATUS',)


class Timezone(Component):

    name = 'VTIMEZONE'

    required = (
        'TZID', 'STANDARDC', 'DAYLIGHTC', 'DTSTART', 'TZOFFSETTO',
        'TZOFFSETFROM'
        )
    singletons = ('LAST-MOD', 'TZURL', 'TZID',)
    multiple = ('COMMENT', 'RDATE', 'RRULE', 'TZNAME',)


class Alarm(Component):

    name = 'VALARM'
    # not quite sure about these ...
    required = ('ACTION', 'TRIGGER',)
    singletons = ('ATTACH', 'ACTION', 'TRIGGER', 'DURATION', 'REPEAT',)
    inclusive = (('DURATION', 'REPEAT',),)
    multiple = ('STANDARDC', 'DAYLIGHTC')


class Calendar(Component):
    """
    This is the base object for an iCalendar file.

    Setting up a minimal calendar component looks like this
    >>> cal = Calendar()

    Som properties are required to be compliant
    >>> cal['prodid'] = '-//My calendar product//mxm.dk//'
    >>> cal['version'] = '2.0'

    We also need at least one subcomponent for a calendar to be compliant
    >>> from datetime import datetime
    >>> event = Event()
    >>> event['summary'] = 'Python meeting about calendaring'
    >>> event['uid'] = '42'
    >>> event.set('dtstart', datetime(2005,4,4,8,0,0))
    >>> cal.add_component(event)
    >>> cal.subcomponents[0].as_string()
    'BEGIN:VEVENT\\r\\nDTSTART;VALUE=DATE:20050404T080000\\r\\nSUMMARY:Python meeting about calendaring\\r\\nUID:42\\r\\nEND:VEVENT\\r\\n'

    Write to disc
    >>> import tempfile, os
    >>> directory = tempfile.mkdtemp()
    >>> open(os.path.join(directory, 'test.ics'), 'wb').write(cal.as_string())
    """

    name = 'VCALENDAR'
    required = ('prodid', 'version', )
    singletons = ('prodid', 'version', )
    multiple = ('calscale', 'method', )


# These are read only singleton, so one instance is enough for the module
types_factory = TypesFactory()
component_factory = ComponentFactory()
