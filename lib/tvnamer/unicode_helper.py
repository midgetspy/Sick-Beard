#!/usr/bin/env python
#encoding:utf-8
#author:dbr/Ben
#project:tvnamer
#repository:http://github.com/dbr/tvnamer
#license:Creative Commons GNU GPL v2
# http://creativecommons.org/licenses/GPL/2.0/

"""Helpers to deal with strings, unicode objects and terminal output
"""

import sys


def unicodify(obj, encoding = "utf-8"):
    if isinstance(obj, basestring):
        if not isinstance(obj, unicode):
            obj = unicode(obj, encoding)
    return obj


def p(*args, **kw):
    """Rough implementation of the Python 3 print function,
    http://www.python.org/dev/peps/pep-3105/

    def print(*args, sep=' ', end='\n', file=None)

    """
    kw.setdefault('encoding', 'utf-8')
    kw.setdefault('sep', ' ')
    kw.setdefault('end', '\n')
    kw.setdefault('file', sys.stdout)

    new_args = []
    for x in args:
        if not isinstance(x, basestring):
            new_args.append(repr(x))
        else:
            if kw['encoding'] is not None:
                new_args.append(x.encode(kw['encoding']))
            else:
                new_args.append(x)

    out = kw['sep'].join(new_args)

    kw['file'].write(out + kw['end'])
