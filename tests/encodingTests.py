# coding=UTF-8

import unittest
import sys, os, locale

sys.path.append(os.path.abspath('..'))
sys.path.append(os.path.abspath('../lib'))

import sickbeard, sickbeard.encodingKludge as ek

try:
    locale.setlocale(locale.LC_ALL, "")
    sickbeard.SYS_ENCODING = locale.getpreferredencoding()
except (locale.Error, IOError):
    pass

# for OSes that are poorly configured I'll just force UTF-8
if not sickbeard.SYS_ENCODING or sickbeard.SYS_ENCODING in ('ANSI_X3.4-1968', 'US-ASCII', 'ASCII'):
    sickbeard.SYS_ENCODING = 'UTF-8'

class EncodingTests(unittest.TestCase):
    
    test_filename = u'test.\xee\xe2\xe9\xe8.txt'
    test_path_unicode = u'test_data' + os.sep + u'encoding_tests'
    test_path_bytestring = str(test_path_unicode)
    
    def setUp(self):
        print "setting up"
        f = open(self.test_path_unicode + os.sep + self.test_filename, 'w')
        f.write('test data')
        f.close()
    
    def tearDown(self):
        os.remove(self.test_path_unicode + os.sep + self.test_filename)
    
    def test_unicode(self):
        ufiles = os.listdir(self.test_path_unicode)
        files = os.listdir(self.test_path_bytestring)
        
        print
        print 'Testing that the encoding', sickbeard.SYS_ENCODING, 'behaves as we expect it would'
        
        self.assertEqual(ufiles[0], files[0].decode(sickbeard.SYS_ENCODING))

    def test_ek(self):
        str_file = ek.ek(os.listdir, self.test_path_bytestring)[0]
        unicode_file = ek.ek(os.listdir, self.test_path_unicode)[0]

        # no matter if we give unicode or not we should get unicode back
        self.assertEqual(u'test.\xee\xe2\xe9\xe8.txt', unicode_file)
        self.assertEqual(u'test.\xee\xe2\xe9\xe8.txt', str_file)

        # we should be able to append it onto a string without an exception
        self.assertEqual(unicode, type("str" + unicode_file))
        self.assertEqual(unicode, type(u"unicode" + unicode_file))
        
        # we should be able to encode it arbitrarily without an exception
        self.assertEqual('test.\xc3\xae\xc3\xa2\xc3\xa9\xc3\xa8.txt', unicode_file.encode('utf-8'))

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(EncodingTests)
    unittest.TextTestRunner(verbosity=2).run(suite)
