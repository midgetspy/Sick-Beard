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

from guessit.containers import PropertiesContainer, WeakValidator, LeavesValidator, QualitiesContainer
from guessit.patterns.extension import subtitle_exts, video_exts, info_exts
from guessit.plugins.transformers import Transformer
from guessit.matcher import GuessFinder


class GuessProperties(Transformer):
    def __init__(self):
        Transformer.__init__(self, 35)

        self.container = PropertiesContainer()
        self.qualities = QualitiesContainer()

        def register_property(propname, props):
            """props a dict of {value: [patterns]}"""
            for canonical_form, patterns in props.items():
                if isinstance(patterns, tuple):
                    patterns2, kwargs = patterns
                    kwargs = dict(kwargs)
                    kwargs['canonical_form'] = canonical_form
                    self.container.register_property(propname, *patterns2, **kwargs)

                else:
                    self.container.register_property(propname, *patterns, canonical_form=canonical_form)

        def register_quality(propname, quality_dict):
            """props a dict of {canonical_form: quality}"""
            for canonical_form, quality in quality_dict.items():
                self.qualities.register_quality(propname, canonical_form, quality)

        register_property('container', {'mp4': ['MP4']})

        # http://en.wikipedia.org/wiki/Pirated_movie_release_types
        register_property('format', {'VHS': ['VHS'],
                                     'Cam': ['CAM', 'CAMRip'],
                                     'Telesync': ['TELESYNC', 'PDVD'],
                                     'Telesync': (['TS'], {'confidence': 0.2}),
                                     'Workprint': ['WORKPRINT', 'WP'],
                                     'Telecine': ['TELECINE', 'TC'],
                                     'PPV': ['PPV', 'PPV-Rip'],  # Pay Per View
                                     'TV': ['SD-TV', 'SD-TV-Rip', 'Rip-SD-TV', 'TV-Rip', 'Rip-TV'],
                                     'DVB': ['DVB-Rip', 'DVB', 'PD-TV'],
                                     'DVD': ['DVD', 'DVD-Rip', 'VIDEO-TS'],
                                     'HDTV': ['HD-TV', 'TV-RIP-HD', 'HD-TV-RIP'],
                                     'VOD': ['VOD', 'VOD-Rip'],
                                     'WEBRip': ['WEB-Rip'],
                                     'WEB-DL': ['WEB-DL'],
                                     'HD-DVD': ['HD-(?:DVD)?-Rip', 'HD-DVD'],
                                     'BluRay': ['Blu-ray', 'B[DR]', 'B[DR]-Rip', 'BD[59]', 'BD25', 'BD50']
                                     })

        register_quality('format', {'VHS': -100,
                                    'Cam': -90,
                                    'Telesync': -80,
                                    'Workprint': -70,
                                    'Telecine': -60,
                                    'PPV': -50,
                                    'TV': -30,
                                    'DVB': -20,
                                    'DVD': 0,
                                    'HDTV': 20,
                                    'VOD': 40,
                                    'WEBRip': 50,
                                    'WEB-DL': 60,
                                    'HD-DVD': 80,
                                    'BluRay': 100
                                    })

        register_property('screenSize', {'360p': ['(?:\d{3,}(?:\\|\/|x|\*))?360(?:i|p?x?)'],
                                         '368p': ['(?:\d{3,}(?:\\|\/|x|\*))?368(?:i|p?x?)'],
                                         '480p': ['(?:\d{3,}(?:\\|\/|x|\*))?480(?:i|p?x?)'],
                                         '480p': (['hr'], {'confidence': 0.2}),
                                         '576p': ['(?:\d{3,}(?:\\|\/|x|\*))?576(?:i|p?x?)'],
                                         '720p': ['(?:\d{3,}(?:\\|\/|x|\*))?720(?:i|p?x?)'],
                                         '900p': ['(?:\d{3,}(?:\\|\/|x|\*))?900(?:i|p?x?)'],
                                         '1080i': ['(?:\d{3,}(?:\\|\/|x|\*))?1080i'],
                                         '1080p': ['(?:\d{3,}(?:\\|\/|x|\*))?1080(?:p?x?)'],
                                         '4K': ['(?:\d{3,}(?:\\|\/|x|\*))?2160(?:i|p?x?)']
                                         })

        register_quality('screenSize', {'360p': -300,
                                        '368p': -200,
                                        '480p': -100,
                                        '576p': 0,
                                        '720p': 100,
                                        '900p': 130,
                                        '1080i': 180,
                                        '1080p': 200,
                                        '4K': 400
                                        })

        _videoCodecProperty = {'Real': ['Rv\d{2}'],  # http://en.wikipedia.org/wiki/RealVideo
                               'Mpeg2': ['Mpeg2'],
                               'DivX': ['DVDivX', 'DivX'],
                               'XviD': ['XviD'],
                               'h264': ['[hx]-264(?:-AVC)?', 'MPEG-4(?:-AVC)'],
                               'h265': ['[hx]-265(?:-HEVC)?', 'HEVC']
                               }

        register_property('videoCodec', _videoCodecProperty)

        register_quality('videoCodec', {'Real': -50,
                                        'Mpeg2': -30,
                                        'DivX': -10,
                                        'XviD': 0,
                                        'h264': 100,
                                        'h265': 150
                                        })

        # http://blog.mediacoderhq.com/h264-profiles-and-levels/
        # http://fr.wikipedia.org/wiki/H.264
        self.container.register_property('videoProfile', 'BP', validator=LeavesValidator(lambdas=[lambda node: 'videoCodec' in node.guess]))
        self.container.register_property('videoProfile', 'XP', 'EP', canonical_form='XP', validator=LeavesValidator(lambdas=[lambda node: 'videoCodec' in node.guess]))
        self.container.register_property('videoProfile', 'MP', validator=LeavesValidator(lambdas=[lambda node: 'videoCodec' in node.guess]))
        self.container.register_property('videoProfile', 'HP', 'HiP', canonical_form='HP', validator=LeavesValidator(lambdas=[lambda node: 'videoCodec' in node.guess]))
        self.container.register_property('videoProfile', '10.?bit', 'Hi10P', canonical_form='10bit', validator=LeavesValidator(lambdas=[lambda node: 'videoCodec' in node.guess]))
        self.container.register_property('videoProfile', 'Hi422P', validator=LeavesValidator(lambdas=[lambda node: 'videoCodec' in node.guess]))
        self.container.register_property('videoProfile', 'Hi444PP', validator=LeavesValidator(lambdas=[lambda node: 'videoCodec' in node.guess]))

        register_quality('videoProfile', {'BP': -20,
                                          'XP': -10,
                                          'MP': 0,
                                          'HP': 10,
                                          '10bit': 15,
                                          'Hi422P': 25,
                                          'Hi444PP': 35
                                          })

        # has nothing to do here (or on filenames for that matter), but some
        # releases use it and it helps to identify release groups, so we adapt
        register_property('videoApi', {'DXVA': ['DXVA']})

        register_property('audioCodec', {'MP3': ['MP3'],
                                         'DolbyDigital': ['DD'],
                                         'AAC': ['AAC'],
                                         'AC3': ['AC3'],
                                         'Flac': ['FLAC'],
                                         'DTS': ['DTS'],
                                         'TrueHD': ['True-HD']
                                         })

        register_quality('audioCodec', {'MP3': 10,
                                        'DolbyDigital': 30,
                                        'AAC': 35,
                                        'AC3': 40,
                                        'Flac': 45,
                                        'DTS': 60,
                                        'TrueHD': 70
                                        })

        self.container.register_property('audioProfile', 'HD', validator=LeavesValidator(lambdas=[lambda node: node.guess.get('audioCodec') == 'DTS']))
        self.container.register_property('audioProfile', 'HD-MA', canonical_form='HDMA', validator=LeavesValidator(lambdas=[lambda node: node.guess.get('audioCodec') == 'DTS']))
        self.container.register_property('audioProfile', 'HE', validator=LeavesValidator(lambdas=[lambda node: node.guess.get('audioCodec') == 'AAC']))
        self.container.register_property('audioProfile', 'LC', validator=LeavesValidator(lambdas=[lambda node: node.guess.get('audioCodec') == 'AAC']))
        self.container.register_property('audioProfile', 'HQ', validator=LeavesValidator(lambdas=[lambda node: node.guess.get('audioCodec') == 'AC3']))

        register_quality('audioProfile', {'HD': 20,
                                          'HDMA': 50,
                                          'LC': 0,
                                          'HQ': 0,
                                          'HE': 20
                                          })

        register_property('audioChannels', {'7.1': ['7[\W_]1', '7ch'],
                                            '5.1': ['5[\W_]1', '5ch'],
                                            '2.0': ['2[\W_]0', '2ch', 'stereo'],
                                            '1.0': ['1[\W_]0', '1ch', 'mono']
                                            })

        register_quality('audioChannels', {'7.1': 200,
                                           '5.1': 100,
                                           '2.0': 0,
                                           '1.0': -100
                                           })

        self.container.register_property('episodeFormat', r'Minisodes?', canonical_form='Minisode')

        register_property('other', {'AudioFix': ['Audio-Fix', 'Audio-Fixed'],
                                    'SyncFix': ['Sync-Fix', 'Sync-Fixed'],
                                    'DualAudio': ['Dual-Audio'],
                                    'WideScreen': ['ws', 'wide-screen'],
                                    })

        self.container.register_property('other', 'Real', 'Fix', canonical_form="Proper", validator=WeakValidator())
        self.container.register_property('other', 'Proper', 'Repack', 'Rerip', canonical_form="Proper")

        self.container.register_canonical_properties('other', 'R5', 'Screener', '3D', 'HD', 'HQ', 'DDC')
        self.container.register_canonical_properties('other', 'Limited', 'Complete', 'Classic', 'Unrated', 'LiNE', 'Bonus', 'Trailer', validator=WeakValidator())

        for prop in self.container.get_properties('format'):
            self.container.register_property('other', prop.pattern + '(-?Scr(?:eener)?)', canonical_form='Screener')

        for exts in (subtitle_exts, info_exts, video_exts):
            for container in exts:
                self.container.register_property('container', container, confidence=0.3)

    def guess_properties(self, string, node=None, options=None):
        found = self.container.find_properties(string, node)
        return self.container.as_guess(found, string)

    def supported_properties(self):
        return self.container.get_supported_properties()

    def process(self, mtree, options=None):
        GuessFinder(self.guess_properties, 1.0, self.log, options).process_nodes(mtree.unidentified_leaves())

    def rate_quality(self, guess, *props):
        return self.qualities.rate_quality(guess, *props)
