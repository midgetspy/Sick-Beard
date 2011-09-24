
import unittest

from name_parser_tests import simple_test_cases
import sickbeard.show_name_helpers

class Show(object):
    def __init__(self, name, anime):
        self.name = name
        self.is_anime = anime

def fakeAllPossibleShowNames(show):
    return [show.name]

sickbeard.show_name_helpers.allPossibleShowNames = fakeAllPossibleShowNames

class TestSequense(unittest.TestCase):
    pass

def test_generator(toTest, parseResult , anime):
    def test(self):
        if parseResult.series_name:
            show = Show(parseResult.series_name, anime)
            isGood = sickbeard.show_name_helpers.isGoodResult(sickbeard.helpers.sanitizeSceneName(toTest), show)
            self.assertTrue(isGood, toTest + " it is not a valid result " + show.name)
        self.assertTrue(True)
    return test

if __name__ == '__main__':
    print
    print "#####################"
    print "Running isGood result test now"
    print "#####################"


    for t in simple_test_cases:
        for cur_test_base in simple_test_cases[t]:
            saneBase = sickbeard.helpers.full_sanitizeSceneName(cur_test_base)

            test_name = 'test_%s_%s' % (t, cur_test_base)

            anime = False
            if "anime" in t:
                anime = True
            if not anime:
                continue    
                
            testFunc = test_generator(cur_test_base, simple_test_cases[t][cur_test_base], anime)
            setattr(TestSequense, test_name, testFunc)
    unittest.main(verbosity=0)

