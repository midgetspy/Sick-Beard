
import unittest
import test_lib as test

from name_parser_tests import simple_test_cases
import sickbeard.show_name_helpers
from sickbeard.tv import TVShow


dontTest = ["Show.Name.102",
            "Show.Name.102.Source.Quality.Etc-Group",
            "show.name.2010.123.source.quality.etc-group",
            "show.name.2010.222.123.source.quality.etc-group",
            "the.event.401.hdtv-lol",
            "Show_Name.1x02.Source_Quality_Etc-Group",
            "Show_Name.1x02x03x04.Source_Quality_Etc-Group",
            "Show Name - 01 - Ep Name",
            "Show Name - Episode 01 - Ep Name",
            "Show Name - Episode 01-02 - Ep Name",
            "Show Name Season 2"]


class TestSequense(test.SickbeardTestDBCase):
    pass

def test_generator(toTest, tvdb_id, parseResult , anime):
    def test(self):
        if parseResult.series_name:
            show = TVShow(parseResult.series_name)
            show.name = parseResult.series_name
            if anime:
                show.anime = 1
            show.saveToDB()
            isGood = sickbeard.show_name_helpers.isGoodResult(sickbeard.helpers.sanitizeSceneName(toTest), show)
            self.assertTrue(isGood, "'" + toTest + "' it is not a valid result '" + show.name + "'")
        self.assertTrue(True)
    return test


tvdb_id = 1
for t in simple_test_cases:
    for cur_test_base in simple_test_cases[t]:
        if cur_test_base in dontTest:
            continue
        saneBase = sickbeard.helpers.full_sanitizeSceneName(cur_test_base)

        test_name = 'test_%s_%s' % (t, cur_test_base)

        anime = False
        if "anime" in t:
            anime = True

        testFunc = test_generator(cur_test_base, tvdb_id, simple_test_cases[t][cur_test_base], anime)
        setattr(TestSequense, test_name, testFunc)
        tvdb_id += 1



if __name__ == '__main__':
    print
    print "#####################"
    print "Running isGood result test now"
    print "#####################"

    suite = unittest.TestLoader().loadTestsFromTestCase(TestSequense)
    unittest.TextTestRunner(verbosity=2).run(suite)

