"""Translate an ics file's events to a different timezone."""

from optparse import OptionParser
from vobject import icalendar, base
import sys
try:
    import PyICU
except:
    PyICU = None

from datetime import datetime

def change_tz(cal, new_timezone, default, utc_only=False, utc_tz=icalendar.utc):
    for vevent in getattr(cal, 'vevent_list', []):
        start = getattr(vevent, 'dtstart', None)
        end   = getattr(vevent, 'dtend',   None)
        for node in (start, end):
            if node:
                dt = node.value
                if (isinstance(dt, datetime) and
                    (not utc_only or dt.tzinfo == utc_tz)):
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo = default)
                    node.value = dt.astimezone(new_timezone)

def main():
    options, args = get_options()
    if PyICU is None:
        print "Failure. change_tz requires PyICU, exiting"
    elif options.list:
        for tz_string in PyICU.TimeZone.createEnumeration():
            print tz_string
    elif args:
        utc_only = options.utc
        if utc_only:
            which = "only UTC"
        else:
            which = "all"
        print "Converting %s events" % which
        ics_file = args[0]
        if len(args) > 1:
            timezone = PyICU.ICUtzinfo.getInstance(args[1])
        else:
            timezone = PyICU.ICUtzinfo.default
        print "... Reading %s" % ics_file
        cal = base.readOne(file(ics_file))
        change_tz(cal, timezone, PyICU.ICUtzinfo.default, utc_only)

        out_name = ics_file + '.converted'
        print "... Writing %s" % out_name
        out = file(out_name, 'wb')
        cal.serialize(out)
        print "Done"


version = "0.1"

def get_options():
    ##### Configuration options #####

    usage = """usage: %prog [options] ics_file [timezone]"""
    parser = OptionParser(usage=usage, version=version)
    parser.set_description("change_tz will convert the timezones in an ics file. ")

    parser.add_option("-u", "--only-utc", dest="utc", action="store_true",
                      default=False, help="Only change UTC events.")
    parser.add_option("-l", "--list", dest="list", action="store_true",
                      default=False, help="List available timezones")


    (cmdline_options, args) = parser.parse_args()
    if not args and not cmdline_options.list:
        print "error: too few arguments given"
        print
        print parser.format_help()
        return False, False

    return cmdline_options, args

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print "Aborted"
