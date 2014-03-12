#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# GuessIt - A library for guessing information from filenames
# Copyright (c) 2013 Nicolas Wack <wackou@gmail.com>
#
# GuessIt is free software; you can redistribute it and/or modify it under
# the terms of the Lesser GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# GuessIt is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# Lesser GNU General Public License for more details.
#
# You should have received a copy of the Lesser GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from __future__ import absolute_import, division, print_function, unicode_literals

from guessit import UnicodeMixin, s, u, base_text_type
import json
import datetime
import logging

log = logging.getLogger(__name__)


class GuessMetadata(object):
    """GuessMetadata contains confidence, an input string, span and related property.

    If defined on a property of Guess object, it overrides the object defined as global.

    :param parent: The parent metadata, used for undefined properties in self object
    :type parent: :class: `GuessMedata`
    :param confidence: The confidence (from 0.0 to 1.0)
    :type confidence: number
    :param input: The input string
    :type input: string
    :param span: The input string
    :type span: tuple (int, int)
    :param prop: The found property definition
    :type prop: :class `guessit.containers._Property`
    """
    def __init__(self, parent=None, confidence=None, input=None, span=None, prop=None, *args, **kwargs):
        self.parent = parent
        if confidence is None and self.parent is None:
            self._confidence = 1.0
        else:
            self._confidence = confidence
        self._input = input
        self._span = span
        self._prop = prop

    @property
    def confidence(self):
        """The confidence

        :rtype: int
        :return: confidence value
        """
        return self._confidence if not self._confidence is None else self.parent.confidence if self.parent else None

    @confidence.setter
    def confidence(self, confidence):
        self._confidence = confidence

    @property
    def input(self):
        """The input

        :rtype: string
        :return: String used to find this guess value
        """
        return self._input if not self._input is None else self.parent.input if self.parent else None

    @property
    def span(self):
        """The span

        :rtype: tuple (int, int)
        :return: span of input string used to find this guess value
        """
        return self._span if not self._span is None else self.parent.span if self.parent else None

    @span.setter
    def span(self, span):
        """The span

        :rtype: tuple (int, int)
        :return: span of input string used to find this guess value
        """
        self._span = span

    @property
    def prop(self):
        """The property

        :rtype: :class:`_Property`
        :return: The property
        """
        return self._prop if not self._prop is None else self.parent.prop if self.parent else None

    @property
    def raw(self):
        """Return the raw information (original match from the string,
        not the cleaned version) associated with the given property name."""
        if self.input and self.span:
            return self.input[self.span[0]:self.span[1]]
        return None

    def __repr__(self, *args, **kwargs):
        return object.__repr__(self, *args, **kwargs)


def _split_kwargs(**kwargs):
    metadata_args = {}
    for prop in dir(GuessMetadata):
        try:
            metadata_args[prop] = kwargs.pop(prop)
        except KeyError:
            pass
    return metadata_args, kwargs


class Guess(UnicodeMixin, dict):
    """A Guess is a dictionary which has an associated confidence for each of
    its values.

    As it is a subclass of dict, you can use it everywhere you expect a
    simple dict."""

    def __init__(self, *args, **kwargs):
        metadata_kwargs, kwargs = _split_kwargs(**kwargs)
        self._global_metadata = GuessMetadata(**metadata_kwargs)
        dict.__init__(self, *args, **kwargs)

        self._metadata = {}
        for prop in self:
            self._metadata[prop] = GuessMetadata(parent=self._global_metadata)

    def to_dict(self, advanced=False):
        """Return the guess as a dict containing only base types, ie:
        where dates, languages, countries, etc. are converted to strings.

        if advanced is True, return the data as a json string containing
        also the raw information of the properties."""
        data = dict(self)
        for prop, value in data.items():
            if isinstance(value, datetime.date):
                data[prop] = value.isoformat()
            elif isinstance(value, (UnicodeMixin, base_text_type)):
                data[prop] = u(value)
            elif isinstance(value, list):
                data[prop] = [u(x) for x in value]
            if advanced:
                metadata = self.metadata(prop)
                prop_data = {'value': data[prop]}
                if metadata.raw:
                    prop_data['raw'] = metadata.raw
                if metadata.confidence:
                    prop_data['confidence'] = metadata.confidence
                data[prop] = prop_data

        return data

    def nice_string(self, advanced=False):
        """Return a string with the property names and their values,
        that also displays the associated confidence to each property.

        FIXME: doc with param"""
        if advanced:
            data = self.to_dict(advanced)
            return json.dumps(data, indent=4)
        else:
            data = self.to_dict()

            parts = json.dumps(data, indent=4).split('\n')
            for i, p in enumerate(parts):
                if p[:5] != '    "':
                    continue

                prop = p.split('"')[1]
                parts[i] = ('    [%.2f] "' % self.confidence(prop)) + p[5:]

            return '\n'.join(parts)

    def __unicode__(self):
        return u(self.to_dict())

    def metadata(self, prop=None):
        """Return the metadata associated with the given property name

        If no property name is given, get the global_metadata
        """
        if prop is None:
            return self._global_metadata
        if not prop in self._metadata:
            self._metadata[prop] = GuessMetadata(parent=self._global_metadata)
        return self._metadata[prop]

    def confidence(self, prop=None):
        return self.metadata(prop).confidence

    def set_confidence(self, prop, confidence):
        self.metadata(prop).confidence = confidence

    def raw(self, prop):
        return self.metadata(prop).raw

    def set(self, prop_name, value, *args, **kwargs):
        self[prop_name] = value
        self._metadata[prop_name] = GuessMetadata(parent=self._global_metadata, *args, **kwargs)

    def update(self, other, confidence=None):
        dict.update(self, other)
        if isinstance(other, Guess):
            for prop in other:
                try:
                    self._metadata[prop] = other._metadata[prop]
                except KeyError:
                    pass
        if not confidence is None:
            for prop in other:
                self.set_confidence(prop, confidence)

    def update_highest_confidence(self, other):
        """Update this guess with the values from the given one. In case
        there is property present in both, only the one with the highest one
        is kept."""
        if not isinstance(other, Guess):
            raise ValueError('Can only call this function on Guess instances')

        for prop in other:
            if prop in self and self.metadata(prop).confidence >= other.metadata(prop).confidence:
                continue
            self[prop] = other[prop]
            self._metadata[prop] = other.metadata(prop)


def choose_int(g1, g2):
    """Function used by merge_similar_guesses to choose between 2 possible
    properties when they are integers."""
    v1, c1 = g1  # value, confidence
    v2, c2 = g2
    if (v1 == v2):
        return (v1, 1 - (1 - c1) * (1 - c2))
    else:
        if c1 > c2:
            return (v1, c1 - c2)
        else:
            return (v2, c2 - c1)


def choose_string(g1, g2):
    """Function used by merge_similar_guesses to choose between 2 possible
    properties when they are strings.

    If the 2 strings are similar, or one is contained in the other, the latter is returned
    with an increased confidence.

    If the 2 strings are dissimilar, the one with the higher confidence is returned, with
    a weaker confidence.

    Note that here, 'similar' means that 2 strings are either equal, or that they
    differ very little, such as one string being the other one with the 'the' word
    prepended to it.

    >>> s(choose_string(('Hello', 0.75), ('World', 0.5)))
    ('Hello', 0.25)

    >>> s(choose_string(('Hello', 0.5), ('hello', 0.5)))
    ('Hello', 0.75)

    >>> s(choose_string(('Hello', 0.4), ('Hello World', 0.4)))
    ('Hello', 0.64)

    >>> s(choose_string(('simpsons', 0.5), ('The Simpsons', 0.5)))
    ('The Simpsons', 0.75)

    """
    v1, c1 = g1  # value, confidence
    v2, c2 = g2

    if not v1:
        return g2
    elif not v2:
        return g1

    v1, v2 = v1.strip(), v2.strip()
    v1l, v2l = v1.lower(), v2.lower()

    combined_prob = 1 - (1 - c1) * (1 - c2)

    if v1l == v2l:
        return (v1, combined_prob)

    # check for common patterns
    elif v1l == 'the ' + v2l:
        return (v1, combined_prob)
    elif v2l == 'the ' + v1l:
        return (v2, combined_prob)

    # if one string is contained in the other, return the shortest one
    elif v2l in v1l:
        return (v2, combined_prob)
    elif v1l in v2l:
        return (v1, combined_prob)

    # in case of conflict, return the one with highest confidence
    else:
        if c1 > c2:
            return (v1, c1 - c2)
        else:
            return (v2, c2 - c1)


def _merge_similar_guesses_nocheck(guesses, prop, choose):
    """Take a list of guesses and merge those which have the same properties,
    increasing or decreasing the confidence depending on whether their values
    are similar.

    This function assumes there are at least 2 valid guesses."""

    similar = [guess for guess in guesses if prop in guess]

    g1, g2 = similar[0], similar[1]

    other_props = set(g1) & set(g2) - set([prop])
    if other_props:
        log.debug('guess 1: %s' % g1)
        log.debug('guess 2: %s' % g2)
        for prop in other_props:
            if g1[prop] != g2[prop]:
                log.warning('both guesses to be merged have more than one '
                            'different property in common, bailing out...')
                return

    # merge all props of s2 into s1, updating the confidence for the
    # considered property
    v1, v2 = g1[prop], g2[prop]
    c1, c2 = g1.confidence(prop), g2.confidence(prop)

    new_value, new_confidence = choose((v1, c1), (v2, c2))
    if new_confidence >= c1:
        msg = "Updating matching property '%s' with confidence %.2f"
    else:
        msg = "Updating non-matching property '%s' with confidence %.2f"
    log.debug(msg % (prop, new_confidence))

    g2[prop] = new_value
    g2.set_confidence(prop, new_confidence)

    g1.update(g2)
    guesses.remove(g2)


def merge_similar_guesses(guesses, prop, choose):
    """Take a list of guesses and merge those which have the same properties,
    increasing or decreasing the confidence depending on whether their values
    are similar."""

    similar = [guess for guess in guesses if prop in guess]
    if len(similar) < 2:
        # nothing to merge
        return

    if len(similar) == 2:
        _merge_similar_guesses_nocheck(guesses, prop, choose)

    if len(similar) > 2:
        log.debug('complex merge, trying our best...')
        before = len(guesses)
        _merge_similar_guesses_nocheck(guesses, prop, choose)
        after = len(guesses)
        if after < before:
            # recurse only when the previous call actually did something,
            # otherwise we end up in an infinite loop
            merge_similar_guesses(guesses, prop, choose)


def merge_all(guesses, append=None):
    """Merge all the guesses in a single result, remove very unlikely values,
    and return it.
    You can specify a list of properties that should be appended into a list
    instead of being merged.

    >>> s(merge_all([ Guess({'season': 2}, confidence=0.6),
    ...               Guess({'episodeNumber': 13}, confidence=0.8) ])
    ... ) == {'season': 2, 'episodeNumber': 13}
    True


    >>> s(merge_all([ Guess({'episodeNumber': 27}, confidence=0.02),
    ...               Guess({'season': 1}, confidence=0.2) ])
    ... ) == {'season': 1}
    True

    >>> s(merge_all([ Guess({'other': 'PROPER'}, confidence=0.8),
    ...               Guess({'releaseGroup': '2HD'}, confidence=0.8) ],
    ...             append=['other'])
    ... ) == {'releaseGroup': '2HD', 'other': ['PROPER']}
    True

    """
    result = Guess()
    if not guesses:
        return result

    if append is None:
        append = []

    for g in guesses:
        # first append our appendable properties
        for prop in append:
            if prop in g:
                result.set(prop, result.get(prop, []) + [g[prop]],
                           # TODO: what to do with confidence here? maybe an
                           # arithmetic mean...
                           confidence=g.metadata(prop).confidence,
                           input=g.metadata(prop).input,
                           span=g.metadata(prop).span,
                           prop=g.metadata(prop).prop)

                del g[prop]

        # then merge the remaining ones
        dups = set(result) & set(g)
        if dups:
            log.warning('duplicate properties %s in merged result...' % [(result[p], g[p]) for p in dups])

        result.update_highest_confidence(g)

    # delete very unlikely values
    for p in list(result.keys()):
        if result.confidence(p) < 0.05:
            del result[p]

    # make sure our appendable properties contain unique values
    for prop in append:
        try:
            value = result[prop]
            if isinstance(value, list):
                result[prop] = list(set(value))
            else:
                result[prop] = [value]
        except KeyError:
            pass

    return result
