import requests
import lib.fanart_api.fanart as fanart
from lib.fanart_api.fanart.errors import RequestFanartError, ResponseFanartError


class Request(object):
    def __init__(self, apikey, id, ws, type=None, sort=None, limit=None):
        self._apikey = apikey
        self._id = id
        self._ws = ws
        self._type = type or fanart.TYPE.ALL
        self._sort = sort or fanart.SORT.POPULAR
        self._limit = limit or fanart.LIMIT.ALL
        self.validate()
        self._response = None

    def validate(self):
        for attribute_name in ('ws', 'type', 'sort', 'limit'):
            attribute = getattr(self, '_' + attribute_name)
            choices = getattr(fanart, attribute_name.upper() + '_LIST')
            if attribute not in choices:
                raise RequestFanartError('Not allowed {0}: {1} [{2}]'.format(attribute_name, attribute, ', '.join(choices)))

    def __str__(self):
        return '/'.join(map(str, [
            fanart.BASEURL,
            self._ws,
            self._apikey,
            self._id,
            fanart.FORMAT.JSON,
            self._type,
            self._sort,
            self._limit,
        ]))

    def response(self):
        try:
            return requests.get(str(self)).json()
        except Exception as e:
            raise ResponseFanartError(str(e))
