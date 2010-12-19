import datetime
import unittest

import sys, os.path
sys.path.append(os.path.abspath('..'))

from sickbeard.name_parser import parser

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
              },
              
              'fov': {
              'Show_Name.1x02.Source_Quality_Etc-Group': parser.ParseResult(None, 'Show Name', 1, [2], 'Source_Quality_Etc', 'Group'),
              'Show Name 1x02': parser.ParseResult(None, 'Show Name', 1, [2]),
              'Show Name - 1x02 - My Ep Name': parser.ParseResult(None, 'Show Name', 1, [2], 'My Ep Name'),
              'Show_Name.1x02x03x04.Source_Quality_Etc-Group': parser.ParseResult(None, 'Show Name', 1, [2,3,4], 'Source_Quality_Etc', 'Group'),
              'Show Name - 1x02-03-04 - My Ep Name': parser.ParseResult(None, 'Show Name', 1, [2,3,4], 'My Ep Name'),
              '1x02 Ep Name': parser.ParseResult(None, None, 1, [2], 'Ep Name'),
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
              'Show.Name.102': parser.ParseResult(None, 'Show Name', 1, [2]),
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
              'Show.Name.E23.Source.Quality.Etc-Group': parser.ParseResult(None, 'Show Name', None, [23], 'Source.Quality.Etc', 'Group'),
              'Show Name - Episode 01 - Ep Name': parser.ParseResult(None, 'Show Name', None, [1], 'Ep Name'),
              'Show.Name.Part.3.Source.Quality.Etc-Group': parser.ParseResult(None, 'Show Name', None, [3], 'Source.Quality.Etc', 'Group'),
              'Show.Name.Part.1.and.Part.2.Blah-Group': parser.ParseResult(None, 'Show Name', None, [1,2], 'Blah', 'Group'),
              'Show Name Episode 3 and 4': parser.ParseResult(None, 'Show Name', None, [3,4]),
              'Show.Name.Part.IV.Source.Quality.Etc-Group': parser.ParseResult(None, 'Show Name', None, [4], 'Source.Quality.Etc', 'Group'),
              },

              'season_only': {
              'Show.Name.S02.Source.Quality.Etc-Group': parser.ParseResult(None, 'Show Name', 2, [], 'Source.Quality.Etc', 'Group'),
              'Show Name Season 2': parser.ParseResult(None, 'Show Name', 2),
              'Season 02': parser.ParseResult(None, None, 2),
              },
              
              'scene_date_format': {
              'Show.Name.2010.11.23.Source.Quality.Etc-Group': parser.ParseResult(None, 'Show Name', None, [], 'Source.Quality.Etc', 'Group', datetime.date(2010,11,23)),
              'Show.Name.2010.23.11.Source.Quality.Etc-Group': parser.ParseResult(None, 'Show Name', None, [], 'Source.Quality.Etc', 'Group', datetime.date(2010,11,23)),
              'Show Name - 2010-11-23 - Ep Name': parser.ParseResult(None, 'Show Name', extra_info = 'Ep Name', air_date = datetime.date(2010,11,23)),
               }
              }

combination_test_cases = [
                          ('/test/path/to/Season 02/03 - Ep Name.avi',
                           parser.ParseResult(None, None, 2, [3], 'Ep Name'),
                           ['no_season', 'season_only']),
                          
                          ('Show.Name.S02.Source.Quality.Etc-Group/tpz-sn203.avi',
                           parser.ParseResult(None, 'Show Name', 2, [3], 'Source.Quality.Etc', 'Group'),
                           ['stupid', 'season_only']),

                          ('MythBusters.S08E16.720p.HDTV.x264-aAF\\aaf-mb.s08e16.720p.mkv',
                           parser.ParseResult(None, 'MythBusters', 8, [16], '720p.HDTV.x264', 'aAF'),
                           ['standard']),
                           
                           ('/home/drop/storage/TV/Terminator The Sarah Connor Chronicles/Season 2/S02E06 The Tower is Tall, But the Fall is Short.mkv',
                            parser.ParseResult(None, None, 2, [6], 'The Tower is Tall, But the Fall is Short'),
                            ['standard']),
                          
                          ]

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
            self._test_combo(name, result, which_regexes)

class BasicTests(unittest.TestCase):

    def _test_names(self, np, section, transform=None, verbose=False):

        if VERBOSE or verbose:
            print
            print 'Running', section, 'tests'
        for cur_test_base in simple_test_cases[section]:
            if transform:
                cur_test = transform(cur_test_base)
            else:
                cur_test = cur_test_base
            if VERBOSE or verbose:
                print 'Testing', cur_test
            test_result = np.parse(cur_test)
            result = simple_test_cases[section][cur_test_base]
            if DEBUG or verbose:
                print 'air_by_date:', test_result.air_by_date, 'air_date:', test_result.air_date
                print test_result
                print result
            self.assertEqual(test_result.which_regex, [section])
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

    def test_season_only_names(self):
        np = parser.NameParser(False)
        self._test_names(np, 'season_only')

    def test_scene_date_format_names(self):
        np = parser.NameParser(False)
        self._test_names(np, 'scene_date_format')

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
    else:
        suite = unittest.TestLoader().loadTestsFromTestCase(BasicTests)
    unittest.TextTestRunner(verbosity=2).run(suite)

    suite = unittest.TestLoader().loadTestsFromTestCase(ComboTests)
    unittest.TextTestRunner(verbosity=2).run(suite)
