import datetime
import unittest

import sys, os.path
sys.path.append(os.path.abspath('..'))
sys.path.append(os.path.abspath('../lib'))

from sickbeard.name_parser import parser

import sickbeard
sickbeard.SYS_ENCODING = 'UTF-8'


DEBUG = VERBOSE = False


simple_test_cases = {
              'standard': {
              'Mr.Show.Name.S01E02.Source.Quality.Etc-Group': parser.ParseResult(None, 'Mr Show Name', 1, [2], 'Source.Quality.Etc', 'Group'),
              'Show.Name.S01E02': parser.ParseResult(None, 'Show Name', 1, [2]),
              'Show Name - S01E02 - My Ep Name': parser.ParseResult(None, 'Show Name', 1, [2], 'My Ep Name'),
              'Show.1.0.Name.S01.E03.My.Ep.Name-Group': parser.ParseResult(None, 'Show 1.0 Name', 1, [3], 'My.Ep.Name', 'Group'),
              'Show.Name.S01E02E03.Source.Quality.Etc-Group': parser.ParseResult(None, 'Show Name', 1, [2,3], 'Source.Quality.Etc', 'Group'),
              'Mr. Show Name - S01E02-03 - My Ep Name': parser.ParseResult(None, 'Mr. Show Name', 1, [2,3], 'My Ep Name'),
              'Show.Name.S01.E02.E03': parser.ParseResult(None, 'Show Name', 1, [2,3]),
              'Show.Name-0.2010.S01E02.Source.Quality.Etc-Group': parser.ParseResult(None, 'Show Name-0 2010', 1, [2], 'Source.Quality.Etc', 'Group'),
              'S01E02 Ep Name': parser.ParseResult(None, None, 1, [2], 'Ep Name'),
              'Show Name - S06E01 - 2009-12-20 - Ep Name': parser.ParseResult(None, 'Show Name', 6, [1], '2009-12-20 - Ep Name'),
              'Show Name - S06E01 - -30-': parser.ParseResult(None, 'Show Name', 6, [1], '30-' ),
              'Show-Name-S06E01-720p': parser.ParseResult(None, 'Show-Name', 6, [1], '720p' ),
              'Show-Name-S06E01-1080i': parser.ParseResult(None, 'Show-Name', 6, [1], '1080i' )
              },
              
              'fov': {
              'Show_Name.1x02.Source_Quality_Etc-Group': parser.ParseResult(None, 'Show Name', 1, [2], 'Source_Quality_Etc', 'Group'),
              'Show Name 1x02': parser.ParseResult(None, 'Show Name', 1, [2]),
              'Show Name 1x02 x264 Test': parser.ParseResult(None, 'Show Name', 1, [2], 'x264 Test'),
              'Show Name - 1x02 - My Ep Name': parser.ParseResult(None, 'Show Name', 1, [2], 'My Ep Name'),
              'Show_Name.1x02x03x04.Source_Quality_Etc-Group': parser.ParseResult(None, 'Show Name', 1, [2,3,4], 'Source_Quality_Etc', 'Group'),
              'Show Name - 1x02-03-04 - My Ep Name': parser.ParseResult(None, 'Show Name', 1, [2,3,4], 'My Ep Name'),
              '1x02 Ep Name': parser.ParseResult(None, None, 1, [2], 'Ep Name'),
              'Show-Name-1x02-720p': parser.ParseResult(None, 'Show-Name', 1, [2], '720p'),
              'Show-Name-1x02-1080i': parser.ParseResult(None, 'Show-Name', 1, [2], '1080i'),
              'Show Name [05x12] Ep Name': parser.ParseResult(None, 'Show Name', 5, [12], 'Ep Name'),
              },

              'standard_repeat': {
              'Show.Name.S01E02.S01E03.Source.Quality.Etc-Group': parser.ParseResult(None, 'Show Name', 1, [2,3], 'Source.Quality.Etc', 'Group'),
              'Show.Name.S01E02.S01E03': parser.ParseResult(None, 'Show Name', 1, [2,3]),
              'Show Name - S01E02 - S01E03 - S01E04 - Ep Name': parser.ParseResult(None, 'Show Name', 1, [2,3,4], 'Ep Name'),
              },
              
              'fov_repeat': {
              'Show.Name.1x02.1x03.Source.Quality.Etc-Group': parser.ParseResult(None, 'Show Name', 1, [2,3], 'Source.Quality.Etc', 'Group'),
              'Show.Name.1x02.1x03': parser.ParseResult(None, 'Show Name', 1, [2,3]),
              'Show Name - 1x02 - 1x03 - 1x04 - Ep Name': parser.ParseResult(None, 'Show Name', 1, [2,3,4], 'Ep Name'),
              },

              'bare': {
              'Show.Name.102.Source.Quality.Etc-Group': parser.ParseResult(None, 'Show Name', 1, [2], 'Source.Quality.Etc', 'Group'),
              'show.name.2010.123.source.quality.etc-group': parser.ParseResult(None, 'show name 2010', 1, [23], 'source.quality.etc', 'group'),
              'show.name.2010.222.123.source.quality.etc-group': parser.ParseResult(None, 'show name 2010.222', 1, [23], 'source.quality.etc', 'group'),
              'Show.Name.102': parser.ParseResult(None, 'Show Name', 1, [2]),
              'the.event.401.hdtv-lol': parser.ParseResult(None, 'the event', 4, [1], 'hdtv', 'lol'),
              },
              
              'stupid': {
              'tpz-abc102': parser.ParseResult(None, None, 1, [2], None, 'tpz'),
              'tpz-abc.102': parser.ParseResult(None, None, 1, [2], None, 'tpz'),
              },
              
              'no_season': {
              'Show Name - 01 - Ep Name': parser.ParseResult(None, 'Show Name', None, [1], 'Ep Name'),
              '01 - Ep Name': parser.ParseResult(None, None, None, [1], 'Ep Name'),
              },

              'no_season_general': {
              'Deconstructed.E07.1080i.HDTV.DD5.1.MPEG2-TrollHD': parser.ParseResult(None, 'Deconstructed', None, [7], '1080i.HDTV.DD5.1.MPEG2', 'TrollHD'),
              'Show.Name.E23.Source.Quality.Etc-Group': parser.ParseResult(None, 'Show Name', None, [23], 'Source.Quality.Etc', 'Group'),
              'Show Name - Episode 01 - Ep Name': parser.ParseResult(None, 'Show Name', None, [1], 'Ep Name'),
              'Show.Name.Part.3.Source.Quality.Etc-Group': parser.ParseResult(None, 'Show Name', None, [3], 'Source.Quality.Etc', 'Group'),
              'Show.Name.Part.1.and.Part.2.Blah-Group': parser.ParseResult(None, 'Show Name', None, [1,2], 'Blah', 'Group'),
              'Show.Name.Part.IV.Source.Quality.Etc-Group': parser.ParseResult(None, 'Show Name', None, [4], 'Source.Quality.Etc', 'Group'),
              },

              'no_season_multi_ep': {
              'Show.Name.E23-24.Source.Quality.Etc-Group': parser.ParseResult(None, 'Show Name', None, [23,24], 'Source.Quality.Etc', 'Group'),
              'Show Name - Episode 01-02 - Ep Name': parser.ParseResult(None, 'Show Name', None, [1,2], 'Ep Name'),
              },

              'season_only': {
              'Show.Name.S02.Source.Quality.Etc-Group': parser.ParseResult(None, 'Show Name', 2, [], 'Source.Quality.Etc', 'Group'),
              'Show Name Season 2': parser.ParseResult(None, 'Show Name', 2),
              'Season 02': parser.ParseResult(None, None, 2),
              },
              
              'scene_date_format': {
              'Show.Name.2010.11.23.Source.Quality.Etc-Group': parser.ParseResult(None, 'Show Name', None, [], 'Source.Quality.Etc', 'Group', datetime.date(2010,11,23)),
              'Show Name - 2010.11.23': parser.ParseResult(None, 'Show Name', air_date = datetime.date(2010,11,23)),
              'Show.Name.2010.23.11.Source.Quality.Etc-Group': parser.ParseResult(None, 'Show Name', None, [], 'Source.Quality.Etc', 'Group', datetime.date(2010,11,23)),
              'Show Name - 2010-11-23 - Ep Name': parser.ParseResult(None, 'Show Name', extra_info = 'Ep Name', air_date = datetime.date(2010,11,23)),
              '2010-11-23 - Ep Name': parser.ParseResult(None, extra_info = 'Ep Name', air_date = datetime.date(2010,11,23)),
               },
               
              'anime_ultimate': {
              '[Tsuki] Bleach - 301 [1280x720][61D1D4EE]': parser.ParseResult(None, 'Bleach', None, [], '1280x720', 'Tsuki', None, [301]),
              '[Tsuki] Fairy Tail - 70 [1280x720][C4807111]': parser.ParseResult(None, 'Fairy Tail', None, [], '1280x720', 'Tsuki', None, [70]),
              '[SGKK] Bleach 312v2 [720p MKV]': parser.ParseResult(None, 'Bleach', None, [], '720p MKV', 'SGKK', None, [312]),
              '[BSS-Anon] Tengen Toppa Gurren Lagann - 22-23 [1280x720][h264][6039D9AF]': parser.ParseResult(None, 'Tengen Toppa Gurren Lagann', None, [], '1280x720', 'BSS-Anon', None, [22,23]),
              '[SJSUBS]_Naruto_Shippuden_-_02_[480p AAC]': parser.ParseResult(None, 'Naruto Shippuden', None, [], '480p AAC', 'SJSUBS', None, [2]),
              '[SFW-Chihiro] Dance in the Vampire Bund - 12 [1920x1080 Blu-ray FLAC][2F6DBC66].mkv': parser.ParseResult(None, 'Dance in the Vampire Bund', None, [], '1920x1080 Blu-ray FLAC', 'SFW-Chihiro', None, [12]),
              '[SHiN-gx] Hanasaku Iroha - 01 [1280x720 h.264 AAC][BDC36683]': parser.ParseResult(None, 'Hanasaku Iroha', None, [], '1280x720 h.264 AAC', 'SHiN-gx', None, [1]),
              '[SFW-Chihiro] Dance in the Vampire Bund - 02 [1920x1080 Blu-ray FLAC][C1FA0A09]': parser.ParseResult(None, 'Dance in the Vampire Bund', None, [], '1920x1080 Blu-ray FLAC', 'SFW-Chihiro', None, [2]),
              '[HorribleSubs] No. 6 - 11 [720p]': parser.ParseResult(None, 'No. 6', None, [], '720p', 'HorribleSubs', None, [11]),
              '[HorribleSubs] D Gray-Man - 312 (480p) [F501C9BE]': parser.ParseResult(None, 'D Gray-Man', None, [], '480p', 'HorribleSubs', None, [312]),
              '[SGKK] Tengen Toppa Gurren Lagann - 45-46 (720p h264) [F501C9BE]': parser.ParseResult(None, 'Tengen Toppa Gurren Lagann', None, [], '720p h264', 'SGKK', None, [45,46]),
              '[Stratos-Subs]_Infinite_Stratos_-_12_(1280x720_H.264_AAC)_[379759DB]': parser.ParseResult(None, 'Infinite Stratos', None, [], '1280x720_H.264_AAC', 'Stratos-Subs', None, [12]),
              '[ShinBunBu-Subs] Bleach - 02-03 (CX 1280x720 x264 AAC)': parser.ParseResult(None, 'Bleach', None, [], 'CX 1280x720 x264 AAC', 'ShinBunBu-Subs', None, [02,03]),
              '[Doki] Hanasaku Iroha - 03 (848x480 h264 AAC) [CB1AA73B]': parser.ParseResult(None, 'Hanasaku Iroha', None, [], '848x480 h264 AAC', 'Doki', None, [03]),
              '[UTW]_Fractal_-_01_[h264-720p][96D3F1BF]': parser.ParseResult(None, 'Fractal', None, [], 'h264-720p', 'UTW', None, [1]),
              
               },
               'anime_ep_name':{
               '[TzaTziki]_One_Piece_279_Chopper_Man_1_[720p][8AE5F25D]': parser.ParseResult(None, 'One Piece', None, [], '720p', 'TzaTziki', None, [279]),
               "[ACX]Wolf's_Rain_-_04_-_Scars_in_the_Wasteland_[octavarium]_[82B7E357]": parser.ParseResult(None, "Wolf's Rain", None, [], 'octavarium', 'ACX', None, [4])
              },
              
              "anime_standard_round": {
              '[SGKK] Bleach - 312v2 (1280x720 h264 AAC) [F501C9BE]': parser.ParseResult(None, 'Bleach', None, [], '1280x720 h264 AAC', 'SGKK', None, [312]),
              },
               
              'anime_slash': {
              '[SGKK] Bleach 312v1 [720p/MKV]': parser.ParseResult(None, 'Bleach', None, [], '720p', 'SGKK', None, [312]),
              '[SGKK] Bleach 312 [480p/MKV]': parser.ParseResult(None, 'Bleach', None, [], '480p', 'SGKK', None, [312])
              },
               
              'anime_standard_codec' : {
              '[Ayako]_Infinite_Stratos_-_IS_-_07_[H264][720p][EB7838FC]': parser.ParseResult(None, 'Infinite Stratos', None, [], '720p', 'Ayako', None, [7]),
              '[Ayako] Infinite Stratos - IS - 07v2 [H264][720p][44419534]': parser.ParseResult(None, 'Infinite Stratos', None, [], '720p', 'Ayako', None, [7]),
              '[Ayako-Shikkaku] Oniichan no Koto Nanka Zenzen Suki Janain Dakara ne - 10 [LQ][h264][720p] [8853B21C]': parser.ParseResult(None, 'Oniichan no Koto Nanka Zenzen Suki Janain Dakara ne', None, [], '720p', 'Ayako-Shikkaku',None, [10]),
              '[Tsuki] Fairy Tail - 72 [XviD][C4807111]': parser.ParseResult(None, 'Fairy Tail', None, [], 'C4807111', 'Tsuki', None, [72]),
              'Bubblegum Crisis Tokyo 2040 - 25 [aX] [F4E2E558]': parser.ParseResult(None, 'Bubblegum Crisis Tokyo 2040', None, [], "aX", None, None, [25]),
              
              },
              
              'anime_and_normal':{
              'Bleach - s02e03 - 012 - Name & Name': parser.ParseResult(None, 'Bleach', 2, [3], None, None, None, [12]),
              'Bleach - s02e03e04 - 012-013 - Name & Name': parser.ParseResult(None, 'Bleach', 2, [3,4], None, None, None, [12,13]),
              'Bleach - s16e03-04 - 313-314': parser.ParseResult(None, 'Bleach', 16, [3,4], None, None, None, [313,314]),
              'Blue Submarine No. 6 s16e03e04 313-314': parser.ParseResult(None, 'Blue Submarine No. 6', 16, [3,4], None, None, None, [313,314]),
              'Bleach.s16e03-04.313-314': parser.ParseResult(None, 'Bleach', 16, [3,4], None, None, None, [313,314]),
              '.hack roots s01e01 001.mkv': parser.ParseResult(None, 'hack roots', 1, [1], None, None, None, [1]),
              '.hack sign s01e01 001.mkv': parser.ParseResult(None, 'hack sign', 1, [1], None, None, None, [1])
              
              },
              
              'anime_and_normal_reverse':{
              'Bleach - 012 - s02e03 - Name & Name': parser.ParseResult(None, 'Bleach', 2, [3], None, None, None, [12]),
              'Blue Submarine No. 6 - 012-013 - s02e03e04 - Name & Name': parser.ParseResult(None, 'Blue Submarine No. 6', 2, [3,4], None, None, None, [12,13]),
              '07-GHOST - 012-013 - s02e03e04 - Name & Name': parser.ParseResult(None, '07-GHOST', 2, [3,4], None, None, None, [12,13]),
              '3x3 Eyes - 012-013 - s02e03-04 - Name & Name': parser.ParseResult(None, '3x3 Eyes', 2, [3,4], None, None, None, [12,13]),
              },
              
              'anime_and_normal_front':{
              '165.Naruto Shippuuden.s08e014': parser.ParseResult(None, 'Naruto Shippuuden', 8, [14], None, None, None, [165]),
              '165-166.Naruto Shippuuden.s08e014e015': parser.ParseResult(None, 'Naruto Shippuuden', 8, [14,15], None, None, None, [165,166]),
              '165-166.07-GHOST.s08e014-015': parser.ParseResult(None, '07-GHOST', 8, [14,15], None, None, None, [165,166]),
              '165-166.3x3 Eyes.S08E014E015': parser.ParseResult(None, '3x3 Eyes', 8, [14,15], None, None, None, [165,166]),
              },
                 
              'anime_bare' :{
              'One Piece 102': parser.ParseResult(None, 'One Piece', None, [], None, None, None, [102]),
              'bleach - 010': parser.ParseResult(None, 'bleach', None, [], None, None, None, [10]),
              'Naruto Shippuden - 314v2': parser.ParseResult(None, 'Naruto Shippuden', None, [], None, None, None, [314]),
              'Blue Submarine No. 6 104-105': parser.ParseResult(None, 'Blue Submarine No. 6', None, [], None, None, None, [104,105]),
              'Samurai X: Trust & Betrayal (OVA) 001-002': parser.ParseResult(None, 'Samurai X: Trust & Betrayal (OVA)', None, [], None, None, None, [1,2]),
              "[ACX]_Wolf's_Spirit_001.mkv": parser.ParseResult(None, "Wolf's Spirit", None, [], None, 'ACX', None, [1])
              }
              
              }

combination_test_cases = [
                          ('/test/path/to/Season 02/03 - Ep Name.avi',
                           parser.ParseResult(None, None, 2, [3], 'Ep Name'),
                           ['no_season', 'season_only']),
                          
                          ('Show.Name.S02.Source.Quality.Etc-Group/tpz-sn203.avi',
                           parser.ParseResult(None, 'Show Name', 2, [3], 'Source.Quality.Etc', 'Group'),
                           ['stupid', 'season_only']),

                          ('MythBusters.S08E16.720p.HDTV.x264-aAF/aaf-mb.s08e16.720p.mkv',
                           parser.ParseResult(None, 'MythBusters', 8, [16], '720p.HDTV.x264', 'aAF'),
                           ['standard']),
                           
                          ('/home/drop/storage/TV/Terminator The Sarah Connor Chronicles/Season 2/S02E06 The Tower is Tall, But the Fall is Short.mkv',
                           parser.ParseResult(None, None, 2, [6], 'The Tower is Tall, But the Fall is Short'),
                           ['standard']),
                           
                          (r'/Test/TV/Jimmy Fallon/Season 2/Jimmy Fallon - 2010-12-15 - blah.avi',
                           parser.ParseResult(None, 'Jimmy Fallon', extra_info = 'blah', air_date = datetime.date(2010,12,15)),
                           ['scene_date_format']),

                          (r'/X/30 Rock/Season 4/30 Rock - 4x22 -.avi',
                           parser.ParseResult(None, '30 Rock', 4, [22]),
                           ['fov']),
                           
                          ]

unicode_test_cases = [
                      (u'The.Big.Bang.Theory.2x07.The.Panty.Pi\xf1ata.Polarization.720p.HDTV.x264.AC3-SHELDON.mkv',
                       parser.ParseResult(None, 'The.Big.Bang.Theory', 2, [7], '720p.HDTV.x264.AC3', 'SHELDON')
                       ),
                      ('The.Big.Bang.Theory.2x07.The.Panty.Pi\xc3\xb1ata.Polarization.720p.HDTV.x264.AC3-SHELDON.mkv',
                       parser.ParseResult(None, 'The.Big.Bang.Theory', 2, [7], '720p.HDTV.x264.AC3', 'SHELDON')
                       ),
                      ]

failure_cases = ['7sins-jfcs01e09-720p-bluray-x264']


class UnicodeTests(unittest.TestCase):
    
    def _test_unicode(self, name, result):
        np = parser.NameParser(True)
        parse_result = np.parse(name)
        # this shouldn't raise an exception
        a = repr(str(parse_result))
    
    def test_unicode(self):
        for (name, result) in unicode_test_cases:
            self._test_unicode(name, result)

class FailureCaseTests(unittest.TestCase):
    
    def _test_name(self, name):
        np = parser.NameParser(True)
        try:
            parse_result = np.parse(name)
        except parser.InvalidNameException:
            return True
        
        if VERBOSE:
            print 'Actual: ', parse_result.which_regex, parse_result
        return False
    
    def test_failures(self):
        for name in failure_cases:
            self.assertTrue(self._test_name(name))

class ComboTests(unittest.TestCase):
    
    def _test_combo(self, name, result, which_regexes):
        if VERBOSE:
            print
            print 'Testing', name 
        
        np = parser.NameParser(True)
        test_result = np.parse(name)
        
        if DEBUG:
            print test_result, test_result.which_regex
            print result, which_regexes  
        
        self.assertEqual(test_result, result)
        for cur_regex in which_regexes:
            self.assertTrue(cur_regex in test_result.which_regex)
        self.assertEqual(len(which_regexes), len(test_result.which_regex))

    def test_combos(self):
        
        for (name, result, which_regexes) in combination_test_cases:
            # Normalise the paths. Converts UNIX-style paths into Windows-style
            # paths when test is run on Windows.
            self._test_combo(os.path.normpath(name), result, which_regexes)


class BasicTests(unittest.TestCase):

    def _test_names(self, np, section, transform=None, verbose=False):
        
        for cur_test_base in simple_test_cases[section]:
            out = ""
            
            
            if transform:
                cur_test = transform(cur_test_base)
            else:
                cur_test = cur_test_base

            result = simple_test_cases[section][cur_test_base]
            if not result:
                self.assertRaises(parser.InvalidNameException, np.parse, cur_test)
                return
            else:
                test_result = np.parse(cur_test)
            result.which_regex = [section]
            
            #self.assertEqual(test_result.which_regex, [section])
            if not test_result == result:
                print  
                out += "----\n"
                out += 'Testing ' + cur_test + "\n"
                out +=  "Should:" + str(result) +"\n"
                out +=  "Is    :" + str(test_result)
                print out
            self.assertEqual(test_result, result)


    def test_standard_names(self):
        np = parser.NameParser(False)
        self._test_names(np, 'standard')

    def test_standard_repeat_names(self):
        np = parser.NameParser(False)
        self._test_names(np, 'standard_repeat')

    def test_fov_names(self):
        np = parser.NameParser(False)
        self._test_names(np, 'fov')

    def test_fov_repeat_names(self):
        np = parser.NameParser(False)
        self._test_names(np, 'fov_repeat')

    def test_bare_names(self):
        np = parser.NameParser(False)
        self._test_names(np, 'bare')

    def test_stupid_names(self):
        np = parser.NameParser(False)
        self._test_names(np, 'stupid')

    def test_no_season_names(self):
        np = parser.NameParser(False)
        self._test_names(np, 'no_season')

    def test_no_season_general_names(self):
        np = parser.NameParser(False)
        self._test_names(np, 'no_season_general')

    def test_no_season_multi_ep_names(self):
        np = parser.NameParser(False)
        self._test_names(np, 'no_season_multi_ep')

    def test_season_only_names(self):
        np = parser.NameParser(False)
        self._test_names(np, 'season_only')

    def test_scene_date_format_names(self):
        np = parser.NameParser(False)
        self._test_names(np, 'scene_date_format')
        
    def test_anime_ultimate(self):
        np = parser.NameParser(False,parser.NameParser.ANIME_REGEX)
        self._test_names(np, 'anime_ultimate',verbose=False)

    def test_anime_ep_name(self):
        np = parser.NameParser(False,parser.NameParser.ANIME_REGEX)
        self._test_names(np, 'anime_ep_name',verbose=False)
        
    def test_anime_slash(self):
        np = parser.NameParser(False,parser.NameParser.ANIME_REGEX)
        self._test_names(np, 'anime_slash',verbose=False)
        
    def test_anime_codec(self):
        np = parser.NameParser(False,parser.NameParser.ANIME_REGEX)
        self._test_names(np, 'anime_standard_codec',verbose=False)
                
    def test_anime_and_normal(self):
        np = parser.NameParser(False,parser.NameParser.ANIME_REGEX)
        self._test_names(np, 'anime_and_normal',verbose=False)
                
    def test_anime_and_normal_reverse(self):
        np = parser.NameParser(False,parser.NameParser.ANIME_REGEX)
        self._test_names(np, 'anime_and_normal_reverse',verbose=False)
                
    def test_anime_and_normal_front(self):
        np = parser.NameParser(False,parser.NameParser.ANIME_REGEX)
        self._test_names(np, 'anime_and_normal_front',verbose=False)

    def test_anime_bare(self):
        np = parser.NameParser(False,parser.NameParser.ANIME_REGEX)
        self._test_names(np, 'anime_bare',verbose=True)
    
    def test_standard_file_names(self):
        np = parser.NameParser()
        self._test_names(np, 'standard', lambda x: x + '.avi')

    def test_standard_repeat_file_names(self):
        np = parser.NameParser()
        self._test_names(np, 'standard_repeat', lambda x: x + '.avi')

    def test_fov_file_names(self):
        np = parser.NameParser()
        self._test_names(np, 'fov', lambda x: x + '.avi')

    def test_fov_repeat_file_names(self):
        np = parser.NameParser()
        self._test_names(np, 'fov_repeat', lambda x: x + '.avi')

    def test_bare_file_names(self):
        np = parser.NameParser()
        self._test_names(np, 'bare', lambda x: x + '.avi')

    def test_stupid_file_names(self):
        np = parser.NameParser()
        self._test_names(np, 'stupid', lambda x: x + '.avi')

    def test_no_season_file_names(self):
        np = parser.NameParser()
        self._test_names(np, 'no_season', lambda x: x + '.avi')

    def test_no_season_general_file_names(self):
        np = parser.NameParser()
        self._test_names(np, 'no_season_general', lambda x: x + '.avi')

    def test_no_season_multi_ep_file_names(self):
        np = parser.NameParser()
        self._test_names(np, 'no_season_multi_ep', lambda x: x + '.avi')

    def test_season_only_file_names(self):
        np = parser.NameParser()
        self._test_names(np, 'season_only', lambda x: x + '.avi')

    def test_scene_date_format_file_names(self):
        np = parser.NameParser()
        self._test_names(np, 'scene_date_format', lambda x: x + '.avi')

    def test_combination_names(self):
        pass

if __name__ == '__main__':
    if len(sys.argv) > 1:
        suite = unittest.TestLoader().loadTestsFromName('name_parser_tests.BasicTests.test_'+sys.argv[1])
        unittest.TextTestRunner(verbosity=2).run(suite)
        exit()
    else:
        suite = unittest.TestLoader().loadTestsFromTestCase(BasicTests)
        unittest.TextTestRunner(verbosity=2).run(suite)

    suite = unittest.TestLoader().loadTestsFromTestCase(ComboTests)
    unittest.TextTestRunner(verbosity=2).run(suite)

    suite = unittest.TestLoader().loadTestsFromTestCase(UnicodeTests)
    unittest.TextTestRunner(verbosity=2).run(suite)

    suite = unittest.TestLoader().loadTestsFromTestCase(FailureCaseTests)
    unittest.TextTestRunner(verbosity=2).run(suite)
