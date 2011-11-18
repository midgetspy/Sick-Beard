# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# object.py - base class for all kaa objects
# -----------------------------------------------------------------------------
# $Id: object.py 4070 2009-05-25 15:32:31Z tack $
# -----------------------------------------------------------------------------
# kaa.base - The Kaa Application Framework
# Copyright 2009 Dirk Meyer, Jason Tackaberry, et al.
#
# This library is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version
# 2.1 as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301 USA
#
# -----------------------------------------------------------------------------

# python imports
import inspect

# kaa imports
from signals import Signals

def get_all_signals(cls):
    """
    Merge __kaasignals__ dict for the entire inheritance tree for the given
    class.  Newer (most descended) __kaasignals__ will replace older ones if
    there are conflicts.
    """
    signals = {}
    for c in reversed(inspect.getmro(cls)):
        if hasattr(c, '__kaasignals__'):
            signals.update(c.__kaasignals__)

    # Remove all signals whose value is None.
    [ signals.pop(k) for k, v in signals.items() if v is None ]
    return signals


class Object(object):
    """
    Base class for kaa objects.

    This class contains logic to convert the __kaasignals__ class attribute
    (a dict) into a signals instance attribute (a kaa.Signals object).

    __kaasignals__ is a dict whose key is the name of the signal, and value
    a docstring.  The dict and docstring should be formatted like so::

        ___kaasignals__ = {
            'example':
                '''
                Single short line describing the signal.

                .. describe:: def callback(arg1, arg2, ...)

                   :param arg1: Description of arg1
                   :type arg1: str
                   :param arg2: Description of arg2
                   :type arg2: bool

                A more detailed description of the signal, if necessary, follows.
                ''',

            'another':
                '''
                Docstring similar to the above example.  Note the blank line
                separating signal stanzas.
                '''
        }

    It is possible for a subclass to remove a signal provided by its superclass
    by setting the dict value to None.  e.g.::

        __kaasignals__ = {
            'newsignal':
                '''
                New signal provided by this subclass.
                ''',

            # This ensures the signal 'supersignal' does not appear in the
            # current class's kaa.Signals object.  (It does not affect the
            # superclass.)
            'supersignal': None
        }
    """
    def __init__(self, *args, **kwargs):
        # Accept all args, and pass to superclass.  Necessary for kaa.Object
        # descendants to be involved in inheritance diamonds.
        super(Object, self).__init__(*args, **kwargs)

        signals = get_all_signals(self.__class__)
        if signals:
            # Construct the kaa.Signals object and attach the docstrings to
            # each signal in the Signal object's __doc__ attribute.
            self.signals = Signals(*signals.keys())
            for name in signals:
                self.signals[name].__doc__ = signals[name]
