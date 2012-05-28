# Author: Nic Wolfe <nic@wolfeden.ca>
# URL: http://code.google.com/p/sickbeard/
#
# This file is part of Sick Beard.
#
# Sick Beard is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Sick Beard is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.

# all regexes are case insensitive

ep_regexes = [
              ('standard_repeat',
               # Show.Name.S01E02.S01E03.Source.Quality.Etc-Group
               # Show Name - S01E02 - S01E03 - S01E04 - Ep Name 
               '''
               ^(?P<series_name>.+?)[. _-]+                # Show_Name and separator
               s(?P<season_num>\d+)[. _-]*                 # S01 and optional separator
               e(?P<ep_num>\d+)                            # E02 and separator
               ([. _-]+s(?P=season_num)[. _-]*             # S01 and optional separator
               e(?P<extra_ep_num>\d+))+                    # E03/etc and separator
               [. _-]*((?P<extra_info>.+?)                 # Source_Quality_Etc-
               ((?<![. _-])-(?P<release_group>[^-]+))?)?$  # Group
               '''),
              
              ('fov_repeat',
               # Show.Name.1x02.1x03.Source.Quality.Etc-Group
               # Show Name - 1x02 - 1x03 - 1x04 - Ep Name
               '''
               ^(?P<series_name>.+?)[. _-]+                # Show_Name and separator
               (?P<season_num>\d+)x                        # 1x
               (?P<ep_num>\d+)                             # 02 and separator
               ([. _-]+(?P=season_num)x                    # 1x
               (?P<extra_ep_num>\d+))+                     # 03/etc and separator
               [. _-]*((?P<extra_info>.+?)                 # Source_Quality_Etc-
               ((?<![. _-])-(?P<release_group>[^-]+))?)?$  # Group
               '''),
              
              ('standard',
               # Show.Name.S01E02.Source.Quality.Etc-Group
               # Show Name - S01E02 - My Ep Name
               # Show.Name.S01.E03.My.Ep.Name
               # Show.Name.S01E02E03.Source.Quality.Etc-Group
               # Show Name - S01E02-03 - My Ep Name
               # Show.Name.S01.E02.E03
               '''
               ^((?P<series_name>.+?)[. _-]+)?             # Show_Name and separator
               s(?P<season_num>\d+)[. _-]*                 # S01 and optional separator
               e(?P<ep_num>\d+)                            # E02 and separator
               (([. _-]*e|-)                               # linking e/- char
               (?P<extra_ep_num>(?!(1080|720)[pi])\d+))*   # additional E03/etc
               [. _-]*((?P<extra_info>.+?)                 # Source_Quality_Etc-
               ((?<![. _-])-(?P<release_group>[^-]+))?)?$  # Group
               '''),

              ('fov',
               # Show_Name.1x02.Source_Quality_Etc-Group
               # Show Name - 1x02 - My Ep Name
               # Show_Name.1x02x03x04.Source_Quality_Etc-Group
               # Show Name - 1x02-03-04 - My Ep Name
               '''
               ^((?P<series_name>.+?)[\[. _-]+)?           # Show_Name and separator
               (?P<season_num>\d+)x                        # 1x
               (?P<ep_num>\d+)                             # 02 and separator
               (([. _-]*x|-)                               # linking x/- char
               (?P<extra_ep_num>
               (?!(1080|720)[pi])(?!(?<=x)264)             # ignore obviously wrong multi-eps
               \d+))*                                      # additional x03/etc
               [\]. _-]*((?P<extra_info>.+?)               # Source_Quality_Etc-
               ((?<![. _-])-(?P<release_group>[^-]+))?)?$  # Group
               '''),
        
              ('scene_date_format',
               # Show.Name.2010.11.23.Source.Quality.Etc-Group
               # Show Name - 2010-11-23 - Ep Name
               '''
               ^((?P<series_name>.+?)[. _-]+)?             # Show_Name and separator
               (?P<air_year>\d{4})[. _-]+                  # 2010 and separator
               (?P<air_month>\d{2})[. _-]+                 # 11 and separator
               (?P<air_day>\d{2})                          # 23 and separator
               [. _-]*((?P<extra_info>.+?)                 # Source_Quality_Etc-
               ((?<![. _-])-(?P<release_group>[^-]+))?)?$  # Group
               '''),
              
              ('stupid',
               # tpz-abc102
               '''
               (?P<release_group>.+?)-\w+?[\. ]?           # tpz-abc
               (?!264)                                     # don't count x264
               (?P<season_num>\d{1,2})                     # 1
               (?P<ep_num>\d{2})$                          # 02
               '''),
              
              ('verbose',
               # Show Name Season 1 Episode 2 Ep Name
               '''
               ^(?P<series_name>.+?)[. _-]+                # Show Name and separator
               season[. _-]+                               # season and separator
               (?P<season_num>\d+)[. _-]+                  # 1
               episode[. _-]+                              # episode and separator
               (?P<ep_num>\d+)[. _-]+                      # 02 and separator
               (?P<extra_info>.+)$                         # Source_Quality_Etc-
               '''),
              
              ('season_only',
               # Show.Name.S01.Source.Quality.Etc-Group
               '''
               ^((?P<series_name>.+?)[. _-]+)?             # Show_Name and separator
               s(eason[. _-])?                             # S01/Season 01
               (?P<season_num>\d+)[. _-]*                  # S01 and optional separator
               [. _-]*((?P<extra_info>.+?)                 # Source_Quality_Etc-
               ((?<![. _-])-(?P<release_group>[^-]+))?)?$  # Group
               '''
               ),

              ('no_season_multi_ep',
               # Show.Name.E02-03
               # Show.Name.E02.2010
               '''
               ^((?P<series_name>.+?)[. _-]+)?             # Show_Name and separator
               (e(p(isode)?)?|part|pt)[. _-]?              # e, ep, episode, or part
               (?P<ep_num>(\d+|[ivx]+))                    # first ep num
               ((([. _-]+(and|&|to)[. _-]+)|-)                # and/&/to joiner
               (?P<extra_ep_num>(?!(1080|720)[pi])(\d+|[ivx]+))[. _-])            # second ep num
               ([. _-]*(?P<extra_info>.+?)                 # Source_Quality_Etc-
               ((?<![. _-])-(?P<release_group>[^-]+))?)?$  # Group
               '''
               ),

              ('no_season_general',
               # Show.Name.E23.Test
               # Show.Name.Part.3.Source.Quality.Etc-Group
               # Show.Name.Part.1.and.Part.2.Blah-Group
               '''
               ^((?P<series_name>.+?)[. _-]+)?             # Show_Name and separator
               (e(p(isode)?)?|part|pt)[. _-]?              # e, ep, episode, or part
               (?P<ep_num>(\d+|([ivx]+(?=[. _-]))))                    # first ep num
               ([. _-]+((and|&|to)[. _-]+)?                # and/&/to joiner
               ((e(p(isode)?)?|part|pt)[. _-]?)           # e, ep, episode, or part
               (?P<extra_ep_num>(?!(1080|720)[pi])
               (\d+|([ivx]+(?=[. _-]))))[. _-])*            # second ep num
               ([. _-]*(?P<extra_info>.+?)                 # Source_Quality_Etc-
               ((?<![. _-])-(?P<release_group>[^-]+))?)?$  # Group
               '''
               ),

              ('bare',
               # Show.Name.102.Source.Quality.Etc-Group
               '''
               ^(?P<series_name>.+?)[. _-]+                # Show_Name and separator
               (?P<season_num>\d{1,2})                     # 1
               (?P<ep_num>\d{2})                           # 02 and separator
               ([. _-]+(?P<extra_info>(?!\d{3}[. _-]+)[^-]+) # Source_Quality_Etc-
               (-(?P<release_group>.+))?)?$                # Group
               '''),
              
              ('no_season',
               # Show Name - 01 - Ep Name
               # 01 - Ep Name
               '''
               ^((?P<series_name>.+?)[. _-]+)?             # Show_Name and separator
               (?P<ep_num>\d{2})                           # 02
               [. _-]+((?P<extra_info>.+?)                 # Source_Quality_Etc-
               ((?<![. _-])-(?P<release_group>[^-]+))?)?$  # Group
               '''
               ),
              ]
anime_ep_regexes = [
                    

               ('anime_ultimate',
                """
                ^(?:\[(?P<release_group>.+?)\][ ._-]*)
                (?P<series_name>.+?)[ ._-]+
                (?P<ep_ab_num>\d{1,3})
                (-(?P<extra_ab_ep_num>\d{1,3}))?[ ._-]+?
                (?:v(?P<version>[0-9]))?
                (?:[\w\.]*)
                (?:(?:(?:[\[\(])(?P<extra_info>\d{3,4}[xp]?\d{0,4}[\.\w\s-]*)(?:[\]\)]))|(?:\d{3,4}[xp]))
                (?:[ ._]?\[(?P<crc>\w+)\])?
                .*?
                """
                ),
               ('anime_standard',
               # [Group Name] Show Name.13-14
               # [Group Name] Show Name - 13-14
               # Show Name 13-14
               # [Group Name] Show Name.13
               # [Group Name] Show Name - 13
               # Show Name 13
               '''
               ^(\[(?P<release_group>.+?)\][ ._-]*)?                        # Release Group and separator
               (?P<series_name>.+?)[ ._-]+                                 # Show_Name and separator
               (?P<ep_ab_num>\d{1,3})                                       # E01
               (-(?P<extra_ab_ep_num>\d{1,3}))?                             # E02
               (v(?P<version>[0-9]))?                                       # version
               [ ._-]+\[(?P<extra_info>\d{3,4}[xp]?\d{0,4}[\.\w\s-]*)\]       # Source_Quality_Etc-
               (\[(?P<crc>\w{8})\])?                                        # CRC
               .*?                                                          # Separator and EOL
               '''),
                    
               ('anime_standard_round',
               # TODO examples
               # [Stratos-Subs]_Infinite_Stratos_-_12_(1280x720_H.264_AAC)_[379759DB]
               # [ShinBunBu-Subs] Bleach - 02-03 (CX 1280x720 x264 AAC)
               '''
               ^(\[(?P<release_group>.+?)\][ ._-]*)?                                    # Release Group and separator
               (?P<series_name>.+?)[ ._-]+                                              # Show_Name and separator
               (?P<ep_ab_num>\d{1,3})                                                   # E01
               (-(?P<extra_ab_ep_num>\d{1,3}))?                                         # E02
               (v(?P<version>[0-9]))?                                                   # version
               [ ._-]+\((?P<extra_info>(CX[ ._-]?)?\d{3,4}[xp]?\d{0,4}[\.\w\s-]*)\)     # Source_Quality_Etc-
               (\[(?P<crc>\w{8})\])?                                                    # CRC
               .*?                                                                      # Separator and EOL
               '''),
               
               ('anime_slash',
               # [SGKK] Bleach 312v1 [720p/MKV]
               '''
               ^(\[(?P<release_group>.+?)\][ ._-]*)? # Release Group and separator
               (?P<series_name>.+?)[ ._-]+           # Show_Name and separator
               (?P<ep_ab_num>\d{1,3})                # E01
               (-(?P<extra_ab_ep_num>\d{1,3}))?      # E02
               (v(?P<version>[0-9]))?                # version
               [ ._-]+\[(?P<extra_info>\d{3,4}p)     # Source_Quality_Etc-
               (\[(?P<crc>\w{8})\])?                 # CRC
               .*?                                   # Separator and EOL
               '''),
               
               ('anime_standard_codec',
               # [Ayako]_Infinite_Stratos_-_IS_-_07_[H264][720p][EB7838FC]
               # [Ayako] Infinite Stratos - IS - 07v2 [H264][720p][44419534]
               # [Ayako-Shikkaku] Oniichan no Koto Nanka Zenzen Suki Janain Dakara ne - 10 [LQ][h264][720p] [8853B21C]
               '''
               ^(\[(?P<release_group>.+?)\][ ._-]*)?                        # Release Group and separator
               (?P<series_name>.+?)[ ._]*                                   # Show_Name and separator
               ([ ._-]+-[ ._-]+[A-Z]+[ ._-]+)?[ ._-]+                       # funny stuff, this is sooo nuts ! this will kick me in the butt one day
               (?P<ep_ab_num>\d{1,3})                                       # E01
               (-(?P<extra_ab_ep_num>\d{1,3}))?                             # E02
               (v(?P<version>[0-9]))?                                       # version
               ([ ._-](\[\w{1,2}\])?\[[a-z][.]?\w{2,4}\])?                        #codec
               [ ._-]*\[(?P<extra_info>(\d{3,4}[xp]?\d{0,4})?[\.\w\s-]*)\]    # Source_Quality_Etc-
               (\[(?P<crc>\w{8})\])?
               .*?                                                          # Separator and EOL
               '''),
               
               ('anime_and_normal',
               # Bleach - s16e03-04 - 313-314
               # Bleach.s16e03-04.313-314
               # Bleach s16e03e04 313-314
               '''
               ^(?P<series_name>.+?)[ ._-]+                 # start of string and series name and non optinal separator
               [sS](?P<season_num>\d+)[. _-]*               # S01 and optional separator
               [eE](?P<ep_num>\d+)                          # epipisode E02
               (([. _-]*e|-)                                # linking e/- char
               (?P<extra_ep_num>\d+))*                      # additional E03/etc
               ([ ._-]{2,}|[ ._]+)                          # if "-" is used to separate at least something else has to be there(->{2,}) "s16e03-04-313-314" would make sens any way
               (?P<ep_ab_num>\d{1,3})                       # absolute number
               (-(?P<extra_ab_ep_num>\d{1,3}))?             # "-" as separator and anditional absolute number, all optinal
               (v(?P<version>[0-9]))?                       # the version e.g. "v2"
               .*?
               '''

               ),
               ('anime_and_normal_x',
               # Bleach - s16e03-04 - 313-314
               # Bleach.s16e03-04.313-314
               # Bleach s16e03e04 313-314
               '''
               ^(?P<series_name>.+?)[ ._-]+                 # start of string and series name and non optinal separator
               (?P<season_num>\d+)[. _-]*               # S01 and optional separator
               [xX](?P<ep_num>\d+)                          # epipisode E02
               (([. _-]*e|-)                                # linking e/- char
               (?P<extra_ep_num>\d+))*                      # additional E03/etc
               ([ ._-]{2,}|[ ._]+)                          # if "-" is used to separate at least something else has to be there(->{2,}) "s16e03-04-313-314" would make sens any way
               (?P<ep_ab_num>\d{1,3})                       # absolute number
               (-(?P<extra_ab_ep_num>\d{1,3}))?             # "-" as separator and anditional absolute number, all optinal
               (v(?P<version>[0-9]))?                       # the version e.g. "v2"
               .*?
               '''

               ),
               
               ('anime_and_normal_reverse',
               # Bleach - 313-314 - s16e03-04
               '''
               ^(?P<series_name>.+?)[ ._-]+                 # start of string and series name and non optinal separator
               (?P<ep_ab_num>\d{1,3})                       # absolute number
               (-(?P<extra_ab_ep_num>\d{1,3}))?             # "-" as separator and anditional absolute number, all optinal
               (v(?P<version>[0-9]))?                       # the version e.g. "v2"
               ([ ._-]{2,}|[ ._]+)                          # if "-" is used to separate at least something else has to be there(->{2,}) "s16e03-04-313-314" would make sens any way
               [sS](?P<season_num>\d+)[. _-]*               # S01 and optional separator
               [eE](?P<ep_num>\d+)                          # epipisode E02
               (([. _-]*e|-)                                # linking e/- char
               (?P<extra_ep_num>\d+))*                      # additional E03/etc
               .*?
               '''
               ),
               
               ('anime_and_normal_front',
               # 165.Naruto Shippuuden.s08e014
               '''
               ^(?P<ep_ab_num>\d{1,3})                       # start of string and absolute number
               (-(?P<extra_ab_ep_num>\d{1,3}))?              # "-" as separator and anditional absolute number, all optinal
               (v(?P<version>[0-9]))?[ ._-]+                 # the version e.g. "v2"
               (?P<series_name>.+?)[ ._-]+
               [sS](?P<season_num>\d+)[. _-]*                 # S01 and optional separator
               [eE](?P<ep_num>\d+) 
               (([. _-]*e|-)                               # linking e/- char
               (?P<extra_ep_num>\d+))*                      # additional E03/etc
               .*?
               '''
               ),
                ('anime_ep_name',
                 """
                ^(?:\[(?P<release_group>.+?)\][ ._-]*)
                (?P<series_name>.+?)[ ._-]+
                (?P<ep_ab_num>\d{1,3})
                (-(?P<extra_ab_ep_num>\d{1,3}))?[ ._-]*?
                (?:v(?P<version>[0-9])[ ._-]+?)?
                (?:.+?[ ._-]+?)?
                \[(?P<extra_info>\w+)\][ ._-]?
                (?:\[(?P<crc>\w{8})\])?
                .*?
                 """
                ),
               ('anime_bare',
               # One Piece - 102
               # [ACX]_Wolf's_Spirit_001.mkv
               '''
               ^(\[(?P<release_group>.+?)\][ ._-]*)?
               (?P<series_name>.+?)[ ._-]+                         # Show_Name and separator
               (?P<ep_ab_num>\d{3})                                      # E01
               (-(?P<extra_ab_ep_num>\d{3}))?                            # E02
               (v(?P<version>[0-9]))?                                     # v2
               .*?                                                         # Separator and EOL
               ''')
               ]
