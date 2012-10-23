try:
    from zope.interface import Interface, Attribute
except ImportError:
    class Interface:
        """A dummy interface base class"""

    class Attribute:
        """A dummy attribute implementation"""
        def __init__(self, doc):
            self.doc = doc

_marker = object()

class IComponent(Interface):
    """
    Component is the base object for calendar, Event and the other
    components defined in RFC 2445.

    A component is like a dictionary with extra methods and attributes.
    """

    # MANIPULATORS

    def __setitem__(name, value):
        """Set a property.

        name - case insensitive name
        value - value of the property to set. This can be either a single
        item or a list.

        Some iCalendar properties are set INLINE; these properties
        have multiple values on one property line in the iCalendar
        representation.  The list can be supplied as a comma separated
        string to __setitem__. If special iCalendar characters exist in
        an entry, such as the colon (:) and (,), that comma-separated
        entry needs to be quoted with double quotes. For example:

        'foo, bar, "baz:hoi"'

        See also set_inline() for an easier way to deal with this case.
        """

    def set_inline(name, values, encode=1):
        """Set list of INLINE values for property.

        Converts a list of values into valid iCalendar comma seperated
        string and sets value to that.

        name - case insensitive name of property
        values - list of values to set
        encode - if True, encode Python values as iCalendar types first.
        """

    def add(name, value):
        """Add a property. Can be called multiple times to set a list.

        name - case insensitive name
        value - value of property to set or add to list for this property.
        """

    def add_component(component):
        """Add a nested subcomponent to this component.
        """

    # static method, can be called on class directly
    def from_ical(st, multiple=False):
        """Populates the component recursively from a iCalendar string.

        Reads the iCalendar string and constructs components and
        subcomponents out of it.
        """

    # ACCESSORS
    def __getitem__(name):
        """Get a property

        name - case insensitive name

        Returns an iCalendar property object such as vText.
        """

    def decoded(name, default=_marker):
        """Get a property as a python object.

        name - case insensitive name
        default - optional argument. If supplied, will use this if
        name cannot be found. If not supplied, decoded will raise a
        KeyError if name cannot be found.

        Returns python object (such as unicode string, datetime, etc).
        """

    def get_inline(name, decode=1):
        """Get list of INLINE values from property.

        name - case insensitive name
        decode - decode to Python objects.

        Returns list of python objects.
        """

    def to_ical():
        """Render the component in the RFC 2445 (iCalendar) format.

        Returns a string in RFC 2445 format.
        """

    subcomponents = Attribute("""
        A list of all subcomponents of this component,
        added using add_component()""")

    name = Attribute("""
        Name of this component (VEVENT, etc)
        """)

    def walk(name=None):
        """Recursively traverses component and subcomponents.

        name - optional, if given, only return components with that name

        Returns sequence of components.
        """

    def property_items(recursive=True):
        """Return properties as (name, value) tuples.

        Returns all properties in this comopnent and subcomponents as
        name, value tuples.
        """

class IEvent(IComponent):
    """A component which conforms to an iCalendar VEVENT.
    """

class ITodo(IComponent):
    """A component which conforms to an iCalendar VTODO.
    """

class IJournal(IComponent):
    """A component which conforms to an iCalendar VJOURNAL.
    """

class IFreeBusy(IComponent):
    """A component which conforms to an iCalendar VFREEBUSY.
    """

class ITimezone(IComponent):
    """A component which conforms to an iCalendar VTIMEZONE.
    """

class IAlarm(IComponent):
    """A component which conforms to an iCalendar VALARM.
    """

class ICalendar(IComponent):
    """A component which conforms to an iCalendar VCALENDAR.
    """

class IPropertyValue(Interface):
    """An iCalendar property value.
    iCalendar properties have strongly typed values.

    This invariance should always be true:

    assert x == vDataType.from_ical(vDataType(x).to_ical())
    """

    def to_ical():
        """Render property as string, as defined in iCalendar RFC 2445.
        """

    # this is a static method
    def from_ical(ical):
        """Parse property from iCalendar RFC 2445 text.

        Inverse of to_ical().
        """

class IBinary(IPropertyValue):
    """Binary property values are base 64 encoded
    """

class IBoolean(IPropertyValue):
    """Boolean property.

    Also behaves like a python int.
    """

class ICalAddress(IPropertyValue):
    """Email address.

    Also behaves like a python str.
    """

class IDateTime(IPropertyValue):
    """Render and generates iCalendar datetime format.

    Important: if tzinfo is defined it renders itself as 'date with utc time'
    Meaning that it has a 'Z' appended, and is in absolute time.
    """

class IDate(IPropertyValue):
    """Render and generates iCalendar date format.
    """

class IDuration(IPropertyValue):
    """Render and generates timedelta in iCalendar DURATION format.
    """

class IFloat(IPropertyValue):
    """Render and generate floats in iCalendar format.

    Also behaves like a python float.
    """

class IInt(IPropertyValue):
    """Render and generate ints in iCalendar format.

    Also behaves like a python int.
    """

class IPeriod(IPropertyValue):
    """A precise period of time (datetime, datetime).
    """

class IWeekDay(IPropertyValue):
    """Render and generate weekday abbreviation.
    """

class IFrequency(IPropertyValue):
    """Frequency.
    """

class IRecur(IPropertyValue):
    """Render and generate data based on recurrent event representation.

    This acts like a caseless dictionary.
    """

class IText(IPropertyValue):
    """Unicode text.
    """

class ITime(IPropertyValue):
    """Time.
    """

class IUri(IPropertyValue):
    """URI
    """

class IGeo(IPropertyValue):
    """Geographical location.
    """

class IUTCOffset(IPropertyValue):
    """Offset from UTC.
    """

class IInline(IPropertyValue):
    """Inline list.
    """
