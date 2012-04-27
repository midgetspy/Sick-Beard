from string import ascii_letters, digits
import random

"""
This module contains non-essential tools for iCalendar. Pretty thin so far eh?

"""

class UIDGenerator:

    """
    If you are too lazy to create real uid's. Notice, this doctest is disabled!

    Automatic semi-random uid
    >> g = UIDGenerator()
    >> uid = g.uid()
    >> uid.ical()
    '20050109T153222-7ekDDHKcw46QlwZK@example.com'

    You Should at least insert your own hostname to be more complient
    >> g = UIDGenerator()
    >> uid = g.uid('Example.ORG')
    >> uid.ical()
    '20050109T153549-NbUItOPDjQj8Ux6q@Example.ORG'

    You can also insert a path or similar
    >> g = UIDGenerator()
    >> uid = g.uid('Example.ORG', '/path/to/content')
    >> uid.ical()
    '20050109T153415-/path/to/content@Example.ORG'
    """

    chars = list(ascii_letters + digits)

    def rnd_string(self, length=16):
        "Generates a string with random characters of length"
        return ''.join([random.choice(self.chars) for i in range(length)])

    def uid(self, host_name='example.com', unique=''):
        """
        Generates a unique id consisting of:
        datetime-uniquevalue@host. Like:
        20050105T225746Z-HKtJMqUgdO0jDUwm@example.com
        """
        from PropertyValues import vText, vDatetime
        unique = unique or self.rnd_string()
        return vText('%s-%s@%s' % (vDatetime.today().ical(), unique, host_name))


if __name__ == "__main__":
    import doctest, tools
    # import and test this file
    doctest.testmod(tools)
