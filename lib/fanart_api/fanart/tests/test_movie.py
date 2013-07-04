import os
import unittest
from httpretty import HTTPretty, httprettified
from fanart.movie import Movie
from fanart.tests import LOCALDIR
os.environ['FANART_APIKEY'] = 'e3c7f0d0beeaf45b3a0dd3b9dd8a3338'


class TvItemTestCase(unittest.TestCase):
    @httprettified
    def test_get(self):
        with open(os.path.join(LOCALDIR, 'response/movie_thg.json')) as fp:
            body = fp.read()
        HTTPretty.register_uri(
            HTTPretty.GET,
            'http://api.fanart.tv/webservice/movie/e3c7f0d0beeaf45b3a0dd3b9dd8a3338/70160/JSON/all/1/2',
            body=body
        )
        hunger_games = Movie.get(id=70160)
        self.assertEqual(hunger_games.tmdbid, '70160')
