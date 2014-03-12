#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# GuessIt - A library for guessing information from filenames
# Copyright (c) 2013 Nicolas Wack <wackou@gmail.com>
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
import logging
import os

from guessit import PY2, u, guess_file_info
from guessit.options import option_parser


def guess_file(filename, info='filename', options=None, **kwargs):
    options = options or {}
    filename = u(filename)

    print('For:', filename)
    guess = guess_file_info(filename, info, options, **kwargs)
    if options.get('yaml'):
        try:
            import yaml
            for k, v in guess.items():
                if isinstance(v, list) and len(v) == 1:
                    guess[k] = v[0]
            ystr = yaml.safe_dump({filename: dict(guess)}, default_flow_style=False)
            i = 0
            for yline in ystr.splitlines():
                if i == 0:
                    print("? " + yline[:-1])
                elif i == 1:
                    print(":" + yline[1:])
                else:
                    print(yline)
                i = i + 1
            return
        except ImportError:  # pragma: no cover
            print('PyYAML not found. Using default output.')
    print('GuessIt found:', guess.nice_string(options.get('advanced')))


def _supported_properties():
    from guessit.plugins import transformers

    all_properties = {}
    transformers_properties = []
    for transformer in transformers.all_transformers():
        supported_properties = transformer.supported_properties()
        transformers_properties.append((transformer, supported_properties))

        if isinstance(supported_properties, dict):
            for property_name, possible_values in supported_properties.items():
                current_possible_values = all_properties.get(property_name)
                if current_possible_values is None:
                    current_possible_values = []
                    all_properties[property_name] = current_possible_values
                if possible_values:
                    current_possible_values.extend(possible_values)
        else:
            for property_name in supported_properties:
                current_possible_values = all_properties.get(property_name)
                if current_possible_values is None:
                    current_possible_values = []
                    all_properties[property_name] = current_possible_values

    return (all_properties, transformers_properties)


def display_transformers():
    print('GuessIt transformers:')
    _, transformers_properties = _supported_properties()
    for transformer, _ in transformers_properties:
        print('[@] %s (%s)' % (transformer.name, transformer.priority))


def display_properties(values, transformers):
    print('GuessIt properties:')
    all_properties, transformers_properties = _supported_properties()
    if transformers:
        for transformer, properties_list in transformers_properties:
            print('[@] %s (%s)' % (transformer.name, transformer.priority))
            for property_name in properties_list:
                property_values = all_properties.get(property_name)
                print('  [+] %s' % (property_name,))
                if property_values and values:
                    _display_property_values(property_name, indent=4)
    else:
        properties_list = []
        properties_list.extend(all_properties.keys())
        properties_list.sort()
        for property_name in properties_list:
            property_values = all_properties.get(property_name)
            print('  [+] %s' % (property_name,))
            if property_values and values:
                _display_property_values(property_name, indent=4)


def _display_property_values(property_name, indent=2):
    all_properties, _ = _supported_properties()
    property_values = all_properties.get(property_name)
    for property_value in property_values:
        print(indent * ' ' + '[!] %s' % (property_value,))


def run_demo(episodes=True, movies=True, options=None):
    # NOTE: tests should not be added here but rather in the tests/ folder
    #       this is just intended as a quick example
    if episodes:
        testeps = ['Series/Californication/Season 2/Californication.2x05.Vaginatown.HDTV.XviD-0TV.[tvu.org.ru].avi',
                   'Series/dexter/Dexter.5x02.Hello,.Bandit.ENG.-.sub.FR.HDTV.XviD-AlFleNi-TeaM.[tvu.org.ru].avi',
                   'Series/Treme/Treme.1x03.Right.Place,.Wrong.Time.HDTV.XviD-NoTV.[tvu.org.ru].avi',
                   'Series/Duckman/Duckman - 101 (01) - 20021107 - I, Duckman.avi',
                   'Series/Duckman/Duckman - S1E13 Joking The Chicken (unedited).avi',
                   'Series/Simpsons/The_simpsons_s13e18_-_i_am_furious_yellow.mpg',
                   'Series/Simpsons/Saison 12 Français/Simpsons,.The.12x08.A.Bas.Le.Sergent.Skinner.FR.[tvu.org.ru].avi',
                   'Series/Dr._Slump_-_002_DVB-Rip_Catalan_by_kelf.avi',
                   'Series/Kaamelott/Kaamelott - Livre V - Second Volet - HD 704x396 Xvid 2 pass - Son 5.1 - TntRip by Slurm.avi'
                   ]

        for f in testeps:
            print('-' * 80)
            guess_file(f, options=options, type='episode')

    if movies:
        testmovies = ['Movies/Fear and Loathing in Las Vegas (1998)/Fear.and.Loathing.in.Las.Vegas.720p.HDDVD.DTS.x264-ESiR.mkv',
                      'Movies/El Dia de la Bestia (1995)/El.dia.de.la.bestia.DVDrip.Spanish.DivX.by.Artik[SEDG].avi',
                      'Movies/Blade Runner (1982)/Blade.Runner.(1982).(Director\'s.Cut).CD1.DVDRip.XviD.AC3-WAF.avi',
                      'Movies/Dark City (1998)/Dark.City.(1998).DC.BDRip.720p.DTS.X264-CHD.mkv',
                      'Movies/Sin City (BluRay) (2005)/Sin.City.2005.BDRip.720p.x264.AC3-SEPTiC.mkv',
                      'Movies/Borat (2006)/Borat.(2006).R5.PROPER.REPACK.DVDRip.XviD-PUKKA.avi',  # FIXME: PROPER and R5 get overwritten
                      '[XCT].Le.Prestige.(The.Prestige).DVDRip.[x264.HP.He-Aac.{Fr-Eng}.St{Fr-Eng}.Chaps].mkv',  # FIXME: title gets overwritten
                      'Battle Royale (2000)/Battle.Royale.(Batoru.Rowaiaru).(2000).(Special.Edition).CD1of2.DVDRiP.XviD-[ZeaL].avi',
                      'Movies/Brazil (1985)/Brazil_Criterion_Edition_(1985).CD2.English.srt',
                      'Movies/Persepolis (2007)/[XCT] Persepolis [H264+Aac-128(Fr-Eng)+ST(Fr-Eng)+Ind].mkv',
                      'Movies/Toy Story (1995)/Toy Story [HDTV 720p English-Spanish].mkv',
                      'Movies/Pirates of the Caribbean: The Curse of the Black Pearl (2003)/Pirates.Of.The.Carribean.DC.2003.iNT.DVDRip.XviD.AC3-NDRT.CD1.avi',
                      'Movies/Office Space (1999)/Office.Space.[Dual-DVDRip].[Spanish-English].[XviD-AC3-AC3].[by.Oswald].avi',
                      'Movies/The NeverEnding Story (1984)/The.NeverEnding.Story.1.1984.DVDRip.AC3.Xvid-Monteque.avi',
                      'Movies/Juno (2007)/Juno KLAXXON.avi',
                      'Movies/Chat noir, chat blanc (1998)/Chat noir, Chat blanc - Emir Kusturica (VO - VF - sub FR - Chapters).mkv',
                      'Movies/Wild Zero (2000)/Wild.Zero.DVDivX-EPiC.srt',
                      'Movies/El Bosque Animado (1987)/El.Bosque.Animado.[Jose.Luis.Cuerda.1987].[Xvid-Dvdrip-720x432].avi',
                      'testsmewt_bugs/movies/Baraka_Edition_Collector.avi'
                      ]

        for f in testmovies:
            print('-' * 80)
            guess_file(f, options=options, type='movie')


def main(args=None, setup_logging=True):
    if setup_logging:
        from guessit import slogging
        slogging.setupLogging()

    if PY2:  # pragma: no cover
        import codecs
        import locale
        import sys

        # see http://bugs.python.org/issue2128
        if os.name == 'nt':
            for i, a in enumerate(sys.argv):
                sys.argv[i] = a.decode(locale.getpreferredencoding())

        # see https://github.com/wackou/guessit/issues/43
        # and http://stackoverflow.com/questions/4545661/unicodedecodeerror-when-redirecting-to-file
        # Wrap sys.stdout into a StreamWriter to allow writing unicode.
        sys.stdout = codecs.getwriter(locale.getpreferredencoding())(sys.stdout)

    if args:
        options, args = option_parser.parse_args(args)
    else:  # pragma: no cover
        options, args = option_parser.parse_args()
    if options.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    help_required = True
    if options.properties or options.values:
        display_properties(options.values, options.transformers)
        help_required = False
    elif options.transformers:
        display_transformers()
        help_required = False
    if options.demo:
        run_demo(episodes=True, movies=True, options=vars(options))
        help_required = False
    else:
        if args:
            help_required = False
            for filename in args:
                guess_file(filename,
                                info=options.info.split(','),
                                options=vars(options)
                                )

    if help_required:  # pragma: no cover
        option_parser.print_help()

if __name__ == '__main__':
    main()
