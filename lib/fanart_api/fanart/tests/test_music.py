import os
import unittest
from httpretty import HTTPretty, httprettified
from fanart.music import Artist
from fanart.tests import LOCALDIR
os.environ['FANART_APIKEY'] = 'e3c7f0d0beeaf45b3a0dd3b9dd8a3338'


class ArtistItemTestCase(unittest.TestCase):
    @httprettified
    def test_get(self):
        with open(os.path.join(LOCALDIR, 'response/music_a7f.json')) as fp:
            body = fp.read()
        HTTPretty.register_uri(
            HTTPretty.GET,
            'http://api.fanart.tv/webservice/artist/e3c7f0d0beeaf45b3a0dd3b9dd8a3338/24e1b53c-3085-4581-8472-0b0088d2508c/JSON/all/1/2',
            body=body
        )
        a7f = Artist.get(id='24e1b53c-3085-4581-8472-0b0088d2508c')
        self.assertEqual(a7f.mbid, '24e1b53c-3085-4581-8472-0b0088d2508c')
