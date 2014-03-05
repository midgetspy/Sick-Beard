# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from babelfish import LanguageReverseConverter, LanguageConvertError, LanguageReverseError


class PodnapisiConverter(LanguageReverseConverter):
    def __init__(self):
        self.from_podnapisi = {2: ('eng',), 28: ('spa',), 26: ('pol',), 36: ('srp',), 1: ('slv',), 38: ('hrv',),
                               9: ('ita',), 8: ('fra',), 48: ('por', 'BR'), 23: ('nld',), 12: ('ara',), 13: ('ron',),
                               33: ('bul',), 32: ('por',), 16: ('ell',), 15: ('hun',), 31: ('fin',), 30: ('tur',),
                               7: ('ces',), 25: ('swe',), 27: ('rus',), 24: ('dan',), 22: ('heb',), 51: ('vie',),
                               52: ('fas',), 5: ('deu',), 14: ('spa', 'AR'), 54: ('ind',), 47: ('srp', None, 'Cyrl'),
                               3: ('nor',), 20: ('est',), 10: ('bos',), 17: ('zho',), 37: ('slk',), 35: ('mkd',),
                               11: ('jpn',), 4: ('kor',), 29: ('sqi',), 6: ('isl',), 19: ('lit',), 46: ('ukr',),
                               44: ('tha',), 53: ('cat',), 56: ('sin',), 21: ('lav',), 40: ('cmn',), 55: ('msa',),
                               42: ('hin',), 50: ('bel',)}
        self.to_podnapisi = {v: k for k, v in self.from_podnapisi.items()}
        self.codes = set(self.from_podnapisi.keys())

    def convert(self, alpha3, country=None, script=None):
        if (alpha3,) in self.to_podnapisi:
            return self.to_podnapisi[(alpha3,)]
        if (alpha3, country) in self.to_podnapisi:
            return self.to_podnapisi[(alpha3, country)]
        if (alpha3, country, script) in self.to_podnapisi:
            return self.to_podnapisi[(alpha3, country, script)]
        raise LanguageConvertError(alpha3, country, script)

    def reverse(self, podnapisi):
        if podnapisi not in self.from_podnapisi:
            raise LanguageReverseError(podnapisi)
        return self.from_podnapisi[podnapisi]
