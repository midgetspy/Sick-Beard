#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# GuessIt - A library for guessing information from filenames
# Copyright (c) 2013 Rémi Alvergnat <toilal.dev@gmail.com>
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

from guessit.plugins.transformers import all_transformers


def best_quality_properties(props, *guesses):
    """Retrieve the best quality guess, based on given properties

    :param props: Properties to include in the rating
    :type props: list of strings
    :param guesses: Guesses to rate
    :type guesses: :class:`guessit.guess.Guess`

    :return: Best quality guess from all passed guesses
    :rtype: :class:`guessit.guess.Guess`
    """
    best_guess = None
    best_rate = None
    for guess in guesses:
        for transformer in all_transformers():
            rate = transformer.rate_quality(guess, *props)
            if best_rate is None or best_rate < rate:
                best_rate = rate
                best_guess = guess
    return best_guess


def best_quality(*guesses):
    """Retrieve the best quality guess.

    :param guesses: Guesses to rate
    :type guesses: :class:`guessit.guess.Guess`

    :return: Best quality guess from all passed guesses
    :rtype: :class:`guessit.guess.Guess`
    """
    best_guess = None
    best_rate = None
    for guess in guesses:
        for transformer in all_transformers():
            rate = transformer.rate_quality(guess)
            if best_rate is None or best_rate < rate:
                best_rate = rate
                best_guess = guess
    return best_guess
