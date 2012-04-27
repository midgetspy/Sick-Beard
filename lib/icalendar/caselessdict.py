# -*- coding: latin-1 -*-

class CaselessDict(dict):
    """
    A dictionary that isn't case sensitive, and only use string as keys.

    >>> ncd = CaselessDict(key1='val1', key2='val2')
    >>> ncd
    CaselessDict({'KEY2': 'val2', 'KEY1': 'val1'})
    >>> ncd['key1']
    'val1'
    >>> ncd['KEY1']
    'val1'
    >>> ncd['KEY3'] = 'val3'
    >>> ncd['key3']
    'val3'
    >>> ncd.setdefault('key3', 'FOUND')
    'val3'
    >>> ncd.setdefault('key4', 'NOT FOUND')
    'NOT FOUND'
    >>> ncd['key4']
    'NOT FOUND'
    >>> ncd.get('key1')
    'val1'
    >>> ncd.get('key3', 'NOT FOUND')
    'val3'
    >>> ncd.get('key4', 'NOT FOUND')
    'NOT FOUND'
    >>> 'key4' in ncd
    True
    >>> del ncd['key4']
    >>> ncd.has_key('key4')
    False
    >>> ncd.update({'key5':'val5', 'KEY6':'val6', 'KEY5':'val7'})
    >>> ncd['key6']
    'val6'
    >>> keys = ncd.keys()
    >>> keys.sort()
    >>> keys
    ['KEY1', 'KEY2', 'KEY3', 'KEY5', 'KEY6']
    """

    def __init__(self, *args, **kwargs):
        "Set keys to upper for initial dict"
        dict.__init__(self, *args, **kwargs)
        for k,v in self.items():
            k_upper = k.upper()
            if k != k_upper:
                dict.__delitem__(self, k)
                self[k_upper] = v

    def __getitem__(self, key):
        return dict.__getitem__(self, key.upper())

    def __setitem__(self, key, value):
        dict.__setitem__(self, key.upper(), value)

    def __delitem__(self, key):
        dict.__delitem__(self, key.upper())

    def __contains__(self, item):
        return dict.__contains__(self, item.upper())

    def get(self, key, default=None):
        return dict.get(self, key.upper(), default)

    def setdefault(self, key, value=None):
        return dict.setdefault(self, key.upper(), value)

    def pop(self, key, default=None):
        return dict.pop(self, key.upper(), default)

    def popitem(self):
        return dict.popitem(self)

    def has_key(self, key):
        return dict.has_key(self, key.upper())

    def update(self, indict):
        """
        Multiple keys where key1.upper() == key2.upper() will be lost.
        """
        for entry in indict:
            self[entry] = indict[entry]

    def copy(self):
        return CaselessDict(dict.copy(self))

    def clear(self):
        dict.clear(self)

    def __repr__(self):
        return 'CaselessDict(' + dict.__repr__(self) + ')'
