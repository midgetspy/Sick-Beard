import unittest

import sys, os.path
sys.path.append(os.path.abspath('..'))

from sickbeard import common

class QualityTests(unittest.TestCase):

    def test_SDTV(self):
        self.assertEqual(common.Quality.SDTV, common.Quality.nameQuality("Test.Show.S01E02.HDTV.x264-GROUP"))
        self.assertEqual(common.Quality.SDTV, common.Quality.nameQuality("Test.Show.S01E02.HDTV.XViD-GROUP"))
        self.assertEqual(common.Quality.SDTV, common.Quality.nameQuality("Test.Show.S01E02.PDTV.XViD-GROUP"))
        self.assertEqual(common.Quality.SDTV, common.Quality.nameQuality("Test.Show.S01E02.PDTV.x264-GROUP"))
        self.assertEqual(common.Quality.SDTV, common.Quality.nameQuality("Test.Show.S01E02.DSR.x264-GROUP"))
        self.assertEqual(common.Quality.SDTV, common.Quality.nameQuality("Test.Show.S01E02.DSR.XViD-GROUP"))

    def test_SDDVD(self):
        self.assertEqual(common.Quality.SDDVD, common.Quality.nameQuality("Test.Show.S01E02.DVDRiP.XViD-GROUP"))
        self.assertEqual(common.Quality.SDDVD, common.Quality.nameQuality("Test.Show.S01E02.DVDRiP.x264-GROUP"))
        self.assertEqual(common.Quality.SDDVD, common.Quality.nameQuality("Test.Show.S01E02.DVDRiP.DiVX-GROUP"))
        self.assertEqual(common.Quality.SDDVD, common.Quality.nameQuality("Test.Show.S01E02.DVDRip.WS.XViD-GROUP"))
        self.assertEqual(common.Quality.SDDVD, common.Quality.nameQuality("Test.Show.S01E02.DVDRip.WS.x264-GROUP"))
        self.assertEqual(common.Quality.SDDVD, common.Quality.nameQuality("Test.Show.S01E02.DVDRip.WS.DiVX-GROUP"))
        self.assertEqual(common.Quality.SDDVD, common.Quality.nameQuality("Test.Show.S01E02.BDRIP.XViD-GROUP"))
        self.assertEqual(common.Quality.SDDVD, common.Quality.nameQuality("Test.Show.S01E02.BDRIP.x264-GROUP"))
        self.assertEqual(common.Quality.SDDVD, common.Quality.nameQuality("Test.Show.S01E02.BDRIP.DiVX-GROUP"))

    def test_HDTV(self):
        self.assertEqual(common.Quality.HDTV, common.Quality.nameQuality("Test.Show.S01E02.720p.HDTV.x264-GROUP"))

    def test_reverse_parsing(self):
        self.assertEqual(common.Quality.SDTV, common.Quality.nameQuality("Test Show - S01E02 - SD TV - GROUP"))
        self.assertEqual(common.Quality.SDDVD, common.Quality.nameQuality("Test Show - S01E02 - SD DVD - GROUP"))
        self.assertEqual(common.Quality.HDTV, common.Quality.nameQuality("Test Show - S01E02 - HD TV - GROUP"))
        self.assertEqual(common.Quality.RAWHDTV, common.Quality.nameQuality("Test Show - S01E02 - RawHD TV - GROUP"))
        self.assertEqual(common.Quality.FULLHDTV, common.Quality.nameQuality("Test Show - S01E02 - 1080p HD TV - GROUP"))
        self.assertEqual(common.Quality.HDWEBDL, common.Quality.nameQuality("Test Show - S01E02 - 720p WEB-DL - GROUP"))
        self.assertEqual(common.Quality.FULLHDWEBDL, common.Quality.nameQuality("Test Show - S01E02 - 1080p WEB-DL - GROUP"))
        self.assertEqual(common.Quality.HDBLURAY, common.Quality.nameQuality("Test Show - S01E02 - 720p BluRay - GROUP"))
        self.assertEqual(common.Quality.FULLHDBLURAY, common.Quality.nameQuality("Test Show - S01E02 - 1080p BluRay - GROUP"))

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(QualityTests)
    unittest.TextTestRunner(verbosity=2).run(suite)
