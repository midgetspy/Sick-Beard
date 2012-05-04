#!/usr/bin/env python
# coding=UTF-8
# Author: Dennis Lutter <lad1337@gmail.com>
# URL: http://code.google.com/p/sickbeard/
#
# This file is part of Sick Beard.
#
# Sick Beard is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Sick Beard is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.

if __name__ == "__main__":
    import glob
    import unittest

    test_file_strings = [ x for x in glob.glob('*_tests.py') if not x in __file__]
    module_strings = [file_string[0:len(file_string) - 3] for file_string in test_file_strings]
    suites = [unittest.defaultTestLoader.loadTestsFromName(file_string) for file_string in module_strings]
    testSuite = unittest.TestSuite(suites)


    print "=================="
    print "STARTING - ALL TESTS"
    print "=================="
    print "this will include"
    for includedfiles in test_file_strings:
        print "- " + includedfiles


    text_runner = unittest.TextTestRunner().run(testSuite)
