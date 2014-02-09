import unittest

import sys
import os.path
sys.path.append(os.path.abspath('..'))

from sickbeard import common


class QualityTests(unittest.TestCase):

    # TODO: repack / proper ? air-by-date ? season rip? multi-ep?

    def test_SDTV(self):
        self.assertEqual(common.Quality.SDTV, common.Quality.nameQuality("Test.Show.S01E02.PDTV.XViD-GROUP"))
        self.assertEqual(common.Quality.SDTV, common.Quality.nameQuality("Test.Show.S01E02.PDTV.x264-GROUP"))
        self.assertEqual(common.Quality.SDTV, common.Quality.nameQuality("Test.Show.S01E02.HDTV.XViD-GROUP"))
        self.assertEqual(common.Quality.SDTV, common.Quality.nameQuality("Test.Show.S01E02.HDTV.x264-GROUP"))
        self.assertEqual(common.Quality.SDTV, common.Quality.nameQuality("Test.Show.S01E02.DSR.XViD-GROUP"))
        self.assertEqual(common.Quality.SDTV, common.Quality.nameQuality("Test.Show.S01E02.DSR.x264-GROUP"))
        self.assertEqual(common.Quality.SDTV, common.Quality.nameQuality("Test.Show.S01E02.TVRip.XViD-GROUP"))
        self.assertEqual(common.Quality.SDTV, common.Quality.nameQuality("Test.Show.S01E02.TVRip.x264-GROUP"))
        self.assertEqual(common.Quality.SDTV, common.Quality.nameQuality("Test.Show.S01E02.WEBRip.XViD-GROUP"))
        self.assertEqual(common.Quality.SDTV, common.Quality.nameQuality("Test.Show.S01E02.WEBRip.x264-GROUP"))
        self.assertEqual(common.Quality.SDTV, common.Quality.nameQuality("Test.Show.S01E02.WEB-DL.x264-GROUP"))
        self.assertEqual(common.Quality.SDTV, common.Quality.nameQuality("Test.Show.S01E02.WEB-DL.AAC2.0.H.264-GROUP"))
        self.assertEqual(common.Quality.SDTV, common.Quality.nameQuality("Test.Show.S01E02 WEB-DL H 264-GROUP"))
        self.assertEqual(common.Quality.SDTV, common.Quality.nameQuality("Test.Show.S01E02_WEB-DL_H_264-GROUP"))
        self.assertEqual(common.Quality.SDTV, common.Quality.nameQuality("Test.Show.S01E02.WEB-DL.AAC2.0.H264-GROUP"))

    def test_SDDVD(self):
        self.assertEqual(common.Quality.SDDVD, common.Quality.nameQuality("Test.Show.S01E02.DVDRiP.XViD-GROUP"))
        self.assertEqual(common.Quality.SDDVD, common.Quality.nameQuality("Test.Show.S01E02.DVDRiP.DiVX-GROUP"))
        self.assertEqual(common.Quality.SDDVD, common.Quality.nameQuality("Test.Show.S01E02.DVDRiP.x264-GROUP"))
        self.assertEqual(common.Quality.SDDVD, common.Quality.nameQuality("Test.Show.S01E02.DVDRip.WS.XViD-GROUP"))
        self.assertEqual(common.Quality.SDDVD, common.Quality.nameQuality("Test.Show.S01E02.DVDRip.WS.DiVX-GROUP"))
        self.assertEqual(common.Quality.SDDVD, common.Quality.nameQuality("Test.Show.S01E02.DVDRip.WS.x264-GROUP"))
        self.assertEqual(common.Quality.SDDVD, common.Quality.nameQuality("Test.Show.S01E02.BDRIP.XViD-GROUP"))
        self.assertEqual(common.Quality.SDDVD, common.Quality.nameQuality("Test.Show.S01E02.BDRIP.DiVX-GROUP"))
        self.assertEqual(common.Quality.SDDVD, common.Quality.nameQuality("Test.Show.S01E02.BDRIP.x264-GROUP"))
        self.assertEqual(common.Quality.SDDVD, common.Quality.nameQuality("Test.Show.S01E02.BDRIP.WS.XViD-GROUP"))
        self.assertEqual(common.Quality.SDDVD, common.Quality.nameQuality("Test.Show.S01E02.BDRIP.WS.DiVX-GROUP"))
        self.assertEqual(common.Quality.SDDVD, common.Quality.nameQuality("Test.Show.S01E02.BDRIP.WS.x264-GROUP"))

    def test_HDTV(self):
        self.assertEqual(common.Quality.HDTV, common.Quality.nameQuality("Test.Show.S01E02.720p.HDTV.x264-GROUP"))
        self.assertEqual(common.Quality.HDTV, common.Quality.nameQuality("Test.Show.S01E02.HR.WS.PDTV.x264-GROUP"))

    def test_RAWHDTV(self):
        self.assertEqual(common.Quality.RAWHDTV, common.Quality.nameQuality("Test.Show.S01E02.720p.HDTV.DD5.1.MPEG2-GROUP"))
        self.assertEqual(common.Quality.RAWHDTV, common.Quality.nameQuality("Test.Show.S01E02.1080i.HDTV.DD2.0.MPEG2-GROUP"))
        self.assertEqual(common.Quality.RAWHDTV, common.Quality.nameQuality("Test.Show.S01E02.1080i.HDTV.H.264.DD2.0-GROUP"))
        self.assertEqual(common.Quality.RAWHDTV, common.Quality.nameQuality("Test Show - S01E02 - 1080i HDTV MPA1.0 H.264 - GROUP"))
        self.assertEqual(common.Quality.RAWHDTV, common.Quality.nameQuality("Test.Show.S01E02.1080i.HDTV.DD.5.1.h264-GROUP"))

    def test_FULLHDTV(self):
        self.assertEqual(common.Quality.FULLHDTV, common.Quality.nameQuality("Test.Show.S01E02.1080p.HDTV.x264-GROUP"))

    def test_HDWEBDL(self):
        self.assertEqual(common.Quality.HDWEBDL, common.Quality.nameQuality("Test.Show.S01E02.720p.WEB-DL-GROUP"))
        self.assertEqual(common.Quality.HDWEBDL, common.Quality.nameQuality("Test.Show.S01E02.720p.WEBRip-GROUP"))
        self.assertEqual(common.Quality.HDWEBDL, common.Quality.nameQuality("Test.Show.S01E02.WEBRip.720p.H.264.AAC.2.0-GROUP"))
        self.assertEqual(common.Quality.HDWEBDL, common.Quality.nameQuality("Test.Show.S01E02.720p.WEB-DL.AAC2.0.H.264-GROUP"))
        self.assertEqual(common.Quality.HDWEBDL, common.Quality.nameQuality("Test Show S01E02 720p WEB-DL AAC2 0 H 264-GROUP"))
        self.assertEqual(common.Quality.HDWEBDL, common.Quality.nameQuality("Test_Show.S01E02_720p_WEB-DL_AAC2.0_H264-GROUP"))
        self.assertEqual(common.Quality.HDWEBDL, common.Quality.nameQuality("Test.Show.S01E02.720p.WEB-DL.AAC2.0.H264-GROUP"))
        self.assertEqual(common.Quality.HDWEBDL, common.Quality.nameQuality("Test.Show.S01E02.720p.iTunes.Rip.H264.AAC-GROUP"))

    def test_FULLHDWEBDL(self):
        self.assertEqual(common.Quality.FULLHDWEBDL, common.Quality.nameQuality("Test.Show.S01E02.1080p.WEB-DL-GROUP"))
        self.assertEqual(common.Quality.FULLHDWEBDL, common.Quality.nameQuality("Test.Show.S01E02.1080p.WEBRip-GROUP"))
        self.assertEqual(common.Quality.FULLHDWEBDL, common.Quality.nameQuality("Test.Show.S01E02.WEBRip.1080p.H.264.AAC.2.0-GROUP"))
        self.assertEqual(common.Quality.FULLHDWEBDL, common.Quality.nameQuality("Test.Show.S01E02.WEBRip.1080p.H264.AAC.2.0-GROUP"))
        self.assertEqual(common.Quality.FULLHDWEBDL, common.Quality.nameQuality("Test.Show.S01E02.1080p.iTunes.H.264.AAC-GROUP"))
        self.assertEqual(common.Quality.FULLHDWEBDL, common.Quality.nameQuality("Test Show S01E02 1080p iTunes H 264 AAC-GROUP"))
        self.assertEqual(common.Quality.FULLHDWEBDL, common.Quality.nameQuality("Test_Show_S01E02_1080p_iTunes_H_264_AAC-GROUP"))

    def test_HDBLURAY(self):
        self.assertEqual(common.Quality.HDBLURAY, common.Quality.nameQuality("Test.Show.S01E02.720p.BluRay.x264-GROUP"))
        self.assertEqual(common.Quality.HDBLURAY, common.Quality.nameQuality("Test.Show.S01E02.720p.HDDVD.x264-GROUP"))

    def test_FULLHDBLURAY(self):
        self.assertEqual(common.Quality.FULLHDBLURAY, common.Quality.nameQuality("Test.Show.S01E02.1080p.BluRay.x264-GROUP"))
        self.assertEqual(common.Quality.FULLHDBLURAY, common.Quality.nameQuality("Test.Show.S01E02.1080p.HDDVD.x264-GROUP"))

    def test_UNKNOWN(self):
        self.assertEqual(common.Quality.UNKNOWN, common.Quality.nameQuality("Test.Show.S01E02-SiCKBEARD"))

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
        self.assertEqual(common.Quality.UNKNOWN, common.Quality.nameQuality("Test Show - S01E02 - Unknown - SiCKBEARD"))

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(QualityTests)
    unittest.TextTestRunner(verbosity=2).run(suite)
