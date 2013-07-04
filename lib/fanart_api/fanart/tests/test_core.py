from unittest import TestCase
from fanart.core import Request
from fanart.errors import RequestFanartError, ResponseFanartError
from httpretty import httprettified, HTTPretty


class RequestTestCase(TestCase):
    def test_valitate_error(self):
        self.assertRaises(RequestFanartError, Request, 'key', 'id', 'sport')

    @httprettified
    def test_response_error(self):
        request = Request('apikey', 'objid', 'series')
        HTTPretty.register_uri(
            HTTPretty.GET,
            'http://api.fanart.tv/webservice/series/apikey/objid/JSON/all/1/2',
            body='Please specify a valid API key',
        )
        try:
            request.response()
        except ResponseFanartError as e:
            self.assertEqual(repr(e), "ResponseFanartError('No JSON object could be decoded',)")
            self.assertEqual(str(e), 'No JSON object could be decoded')
