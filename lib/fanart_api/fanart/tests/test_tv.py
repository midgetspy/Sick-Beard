import os
import unittest
from httpretty import HTTPretty, httprettified
from fanart.tv import TvShow
from fanart.tests import LOCALDIR
os.environ['FANART_APIKEY'] = 'e3c7f0d0beeaf45b3a0dd3b9dd8a3338'


class TvItemTestCase(unittest.TestCase):
    @httprettified
    def test_get(self):
        with open(os.path.join(LOCALDIR, 'response/tv_239761.json')) as fp:
            body = fp.read()
        HTTPretty.register_uri(
            HTTPretty.GET,
            'http://api.fanart.tv/webservice/series/e3c7f0d0beeaf45b3a0dd3b9dd8a3338/239761/JSON/all/1/2',
            body=body
        )
        wilfred = TvShow.get(id=239761)
        self.assertEqual(wilfred.tvdbid, '239761')
