import random
import sys
import textwrap
from string import ascii_letters, digits
from datetime import datetime


class UIDGenerator:
    """If you are too lazy to create real uid's. Notice, this doctest is
    disabled!

    Automatic semi-random uid
    >> g = UIDGenerator()
    >> uid = g.uid()
    >> uid.to_ical()
    '20050109T153222-7ekDDHKcw46QlwZK@example.com'

    You should at least insert your own hostname to be more compliant
    >> g = UIDGenerator()
    >> uid = g.uid('Example.ORG')
    >> uid.to_ical()
    '20050109T153549-NbUItOPDjQj8Ux6q@Example.ORG'

    You can also insert a path or similar
    >> g = UIDGenerator()
    >> uid = g.uid('Example.ORG', '/path/to/content')
    >> uid.to_ical()
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
        from icalendar.prop import vText, vDatetime
        unique = unique or self.rnd_string()
        return vText('%s-%s@%s' % (vDatetime(datetime.today()).to_ical(), unique, host_name))


if sys.version_info[0:2] <= (2, 5):
    class TextWrapper(textwrap.TextWrapper):
        """A TextWrapper that borrow its _wrap_chunks implementation
        from python 2.7
        """
        def __init__(self, **kw):
            self.drop_whitespace = kw.pop('drop_whitespace', True)
            textwrap.TextWrapper.__init__(self, **kw)

        def _wrap_chunks(self, chunks):
            """_wrap_chunks(chunks : [string]) -> [string]

            Wrap a sequence of text chunks and return a list of lines of
            length 'self.width' or less.  (If 'break_long_words' is false,
            some lines may be longer than this.)  Chunks correspond roughly
            to words and the whitespace between them: each chunk is
            indivisible (modulo 'break_long_words'), but a line break can
            come between any two chunks.  Chunks should not have internal
            whitespace; ie. a chunk is either all whitespace or a "word".
            Whitespace chunks will be removed from the beginning and end of
            lines, but apart from that whitespace is preserved.
            """
            lines = []
            if self.width <= 0:
                raise ValueError("invalid width %r (must be > 0)" % self.width)

            # Arrange in reverse order so items can be efficiently popped
            # from a stack of chucks.
            chunks.reverse()

            while chunks:

                # Start the list of chunks that will make up the current line.
                # cur_len is just the length of all the chunks in cur_line.
                cur_line = []
                cur_len = 0

                # Figure out which static string will prefix this line.
                if lines:
                    indent = self.subsequent_indent
                else:
                    indent = self.initial_indent

                # Maximum width for this line.
                width = self.width - len(indent)

                # First chunk on line is whitespace -- drop it, unless this
                # is the very beginning of the text (ie. no lines started yet).
                if self.drop_whitespace and chunks[-1].strip() == '' and lines:
                    del chunks[-1]

                while chunks:
                    l = len(chunks[-1])

                    # Can at least squeeze this chunk onto the current line.
                    if cur_len + l <= width:
                        cur_line.append(chunks.pop())
                        cur_len += l

                    # Nope, this line is full.
                    else:
                        break

                # The current line is full, and the next chunk is too big to
                # fit on *any* line (not just this one).
                if chunks and len(chunks[-1]) > width:
                    self._handle_long_word(chunks, cur_line, cur_len, width)

                # If the last chunk on this line is all whitespace, drop it.
                if self.drop_whitespace and cur_line and cur_line[-1].strip() == '':
                    del cur_line[-1]

                # Convert current line back to a string and store it in list
                # of all lines (return value).
                if cur_line:
                    lines.append(indent + ''.join(cur_line))

            return lines
else:
    TextWrapper = textwrap.TextWrapper


def wrap(text, width=70, **kwargs):
    w = TextWrapper(width=width, **kwargs)
    return w.wrap(text)

if __name__ == "__main__":
    import doctest, tools
    # import and test this file
    doctest.testmod(tools)
