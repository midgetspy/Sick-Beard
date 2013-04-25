# Author: Tyler Fenby <tylerfenby@gmail.com>
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

import re
import urllib

from sickbeard import db

def prepareFailedName(release):
    """Standardizes release name for failed DB"""

    fixed = urllib.unquote(release)
    fixed = re.sub("[\.\-\+\ ]", "_", fixed)
    return fixed

def logFailed(release):
    myDB = db.DBConnection('failed.db')
    myDB.select("INSERT INTO failed (release) VALUES (?)", [prepareFailedName(release)])

def hasFailed(release):
    myDB = db.DBConnection('failed.db')
    sql_results = myDB.select("SELECT * FROM failed WHERE release like ?", [prepareFailedName(release)])
    return (len(sql_results) > 0)
