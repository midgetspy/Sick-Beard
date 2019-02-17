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

from stevedore import ExtensionManager
from pkg_resources import EntryPoint

from stevedore.extension import Extension
from logging import getLogger

log = getLogger(__name__)


class Transformer(object):  # pragma: no cover
    def __init__(self, priority=0):
        self.priority = priority
        self.log = getLogger(self.name)

    @property
    def name(self):
        return self.__class__.__name__

    def supported_properties(self):
        return {}

    def second_pass_options(self, mtree, options=None):
        return None

    def should_process(self, mtree, options=None):
        return True

    def process(self, mtree, options=None):
        pass

    def post_process(self, mtree, options=None):
        pass

    def rate_quality(self, guess, *props):
        return 0


class CustomTransformerExtensionManager(ExtensionManager):
    def __init__(self, namespace='guessit.transformer', invoke_on_load=True,
        invoke_args=(), invoke_kwds={}, propagate_map_exceptions=True, on_load_failure_callback=None,
                 verify_requirements=False):
        super(CustomTransformerExtensionManager, self).__init__(namespace=namespace,
                 invoke_on_load=invoke_on_load,
                 invoke_args=invoke_args,
                 invoke_kwds=invoke_kwds,
                 propagate_map_exceptions=propagate_map_exceptions,
                 on_load_failure_callback=on_load_failure_callback,
                 verify_requirements=verify_requirements)

    def order_extensions(self, extensions):
        """Order the loaded transformers

        It should follow those rules
           - website before language (eg: tvu.org.ru vs russian)
           - language before episodes_rexps
           - properties before language (eg: he-aac vs hebrew)
           - release_group before properties (eg: XviD-?? vs xvid)
        """
        extensions.sort(key=lambda ext: -ext.obj.priority)
        return extensions

    def _load_one_plugin(self, ep, invoke_on_load, invoke_args, invoke_kwds, verify_requirements):
        if not ep.dist:
            plugin = ep.load(require=False)
        else:
            plugin = ep.load(require=verify_requirements)
        if invoke_on_load:
            obj = plugin(*invoke_args, **invoke_kwds)
        else:
            obj = None
        return Extension(ep.name, ep, plugin, obj)

    def _load_plugins(self, invoke_on_load, invoke_args, invoke_kwds, verify_requirements):
        return self.order_extensions(super(CustomTransformerExtensionManager, self)._load_plugins(invoke_on_load, invoke_args, invoke_kwds, verify_requirements))

    def objects(self):
        return self.map(self._get_obj)

    def _get_obj(self, ext):
        return ext.obj

    def object(self, name):
        try:
            return self[name].obj
        except KeyError:
            return None

    def register_module(self, name, module_name):
        ep = EntryPoint(name, module_name)
        loaded = self._load_one_plugin(ep, invoke_on_load=True, invoke_args=(), invoke_kwds={})
        if loaded:
            self.extensions.append(loaded)
            self.extensions = self.order_extensions(self.extensions)
            self._extensions_by_name = None


class DefaultTransformerExtensionManager(CustomTransformerExtensionManager):
    @property
    def _internal_entry_points(self):
        return ['split_path_components = guessit.transfo.split_path_components:SplitPathComponents',
                                    'guess_filetype = guessit.transfo.guess_filetype:GuessFiletype',
                                    'split_explicit_groups = guessit.transfo.split_explicit_groups:SplitExplicitGroups',
                                    'guess_date = guessit.transfo.guess_date:GuessDate',
                                    'guess_website = guessit.transfo.guess_website:GuessWebsite',
                                    'guess_release_group = guessit.transfo.guess_release_group:GuessReleaseGroup',
                                    'guess_properties = guessit.transfo.guess_properties:GuessProperties',
                                    'guess_language = guessit.transfo.guess_language:GuessLanguage',
                                    'guess_video_rexps = guessit.transfo.guess_video_rexps:GuessVideoRexps',
                                    'guess_episodes_rexps = guessit.transfo.guess_episodes_rexps:GuessEpisodesRexps',
                                    'guess_weak_episodes_rexps = guessit.transfo.guess_weak_episodes_rexps:GuessWeakEpisodesRexps',
                                    'guess_bonus_features = guessit.transfo.guess_bonus_features:GuessBonusFeatures',
                                    'guess_year = guessit.transfo.guess_year:GuessYear',
                                    'guess_country = guessit.transfo.guess_country:GuessCountry',
                                    'guess_idnumber = guessit.transfo.guess_idnumber:GuessIdnumber',
                                    'split_on_dash = guessit.transfo.split_on_dash:SplitOnDash',
                                    'guess_episode_info_from_position = guessit.transfo.guess_episode_info_from_position:GuessEpisodeInfoFromPosition',
                                    'guess_movie_title_from_position = guessit.transfo.guess_movie_title_from_position:GuessMovieTitleFromPosition',
                                    'guess_episode_special = guessit.transfo.guess_episode_special:GuessEpisodeSpecial']

    def _find_entry_points(self, namespace):
        entry_points = {}
        # Internal entry points
        if namespace == self.namespace:
            for internal_entry_point_str in self._internal_entry_points:
                internal_entry_point = EntryPoint.parse(internal_entry_point_str)
                entry_points[internal_entry_point.name] = internal_entry_point

        # Package entry points
        setuptools_entrypoints = super(DefaultTransformerExtensionManager, self)._find_entry_points(namespace)
        for setuptools_entrypoint in setuptools_entrypoints:
            entry_points[setuptools_entrypoint.name] = setuptools_entrypoint

        return list(entry_points.values())

_extensions = None


def all_transformers():
    return _extensions.objects()


def get_transformer(name):
    return _extensions.object(name)


def add_transformer(name, module_name):
    _extensions.register_module(name, module_name)


def reload(custom=False):
    """
    Reload extension manager with default or custom one.
    :param custom: if True, custom manager will be used, else default one.
    Default manager will load default extensions from guessit and setuptools packaging extensions
    Custom manager will not load default extensions from guessit, using only setuptools packaging extensions.
    :type custom: boolean
    """
    global _extensions
    if custom:
        _extensions = CustomTransformerExtensionManager()
    else:
        _extensions = DefaultTransformerExtensionManager()

reload()
