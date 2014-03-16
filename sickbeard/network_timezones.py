# Author: Nic Wolfe <nic@wolfeden.ca>
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

from lib.dateutil import tz
import lib.dateutil.zoneinfo
from sickbeard import db
from sickbeard import helpers
from sickbeard import logger
from sickbeard import encodingKludge as ek
from os.path import basename, join, isfile
import os
import re
import datetime

# regex to parse time (12/24 hour format)
time_regex = re.compile(r"(\d{1,2})(([:.](\d{2,2}))? ?([PA][. ]? ?M)|[:.](\d{2,2}))\b", flags=re.IGNORECASE)
am_regex = re.compile(r"(A[. ]? ?M)", flags=re.IGNORECASE)
pm_regex = re.compile(r"(P[. ]? ?M)", flags=re.IGNORECASE)

network_dict = None

sb_timezone = tz.tzlocal()

# helper to remove failed temp download
def _remove_zoneinfo_failed(filename):
    try:
        ek.ek(os.remove,filename)
    except:
        pass

# helper to remove old unneeded zoneinfo files
def _remove_old_zoneinfo():
    if (lib.dateutil.zoneinfo.ZONEINFOFILE is not None):
        cur_zoneinfo = ek.ek(basename, lib.dateutil.zoneinfo.ZONEINFOFILE)
    else:
        return
    
    cur_file = helpers.real_path(u'lib/dateutil/zoneinfo/' + cur_zoneinfo)
    
    for (path, dirs, files) in ek.ek(os.walk,helpers.real_path(u'lib/dateutil/zoneinfo/')):
        for filename in files:
            if filename.endswith('.tar.gz'):
                file_w_path = ek.ek(join,path,filename)
                if file_w_path != cur_file and ek.ek(isfile,file_w_path):
                    try:
                        ek.ek(os.remove,file_w_path)
                        logger.log(u"Delete unneeded old zoneinfo File: " + file_w_path)
                    except:
                        logger.log(u"Unable to delete: " + file_w_path,logger.ERROR)

# update the dateutil zoneinfo
def _update_zoneinfo():

    global sb_timezone
    sb_timezone = tz.tzlocal()

    # now check if the zoneinfo needs update
    url_zv = 'https://github.com/Prinz23/sb_network_timezones/raw/master/zoneinfo.txt'

    url_data = helpers.getURL(url_zv)

    if url_data is None:
        # When urlData is None, trouble connecting to github
        logger.log(u"Loading zoneinfo.txt failed. Unable to get URL: " + url_zv, logger.ERROR)
        return

    if (lib.dateutil.zoneinfo.ZONEINFOFILE is not None):
        cur_zoneinfo = ek.ek(basename, lib.dateutil.zoneinfo.ZONEINFOFILE)
    else:
        cur_zoneinfo = None
    (new_zoneinfo, zoneinfo_md5) = url_data.decode('utf-8').strip().rsplit(u' ')

    if ((cur_zoneinfo is not None) and (new_zoneinfo == cur_zoneinfo)):
        return

    # now load the new zoneinfo
    url_tar = u'https://github.com/Prinz23/sb_network_timezones/raw/master/' + new_zoneinfo
    zonefile = helpers.real_path(u'lib/dateutil/zoneinfo/' + new_zoneinfo)
    zonefile_tmp = re.sub(r"\.tar\.gz$",'.tmp', zonefile)

    if (ek.ek(os.path.exists,zonefile_tmp)):
        try:
            ek.ek(os.remove,zonefile_tmp)
        except:
            logger.log(u"Unable to delete: " + zonefile_tmp,logger.ERROR)
            return

    if not helpers.download_file(url_tar, zonefile_tmp):
        return

    if not ek.ek(os.path.exists,zonefile_tmp):
        logger.log(u"Download of " + zonefile_tmp + " failed.",logger.ERROR)
        return

    new_hash = str(helpers.md5_for_file(zonefile_tmp))

    if (zoneinfo_md5.upper() == new_hash.upper()):
        logger.log(u"Updating timezone info with new one: " + new_zoneinfo,logger.MESSAGE)
        try:
            # remove the old zoneinfo file
            if (cur_zoneinfo is not None):
                old_file = helpers.real_path(u'lib/dateutil/zoneinfo/' + cur_zoneinfo)
                if (ek.ek(os.path.exists,old_file)):
                    ek.ek(os.remove,old_file)
            # rename downloaded file
            ek.ek(os.rename,zonefile_tmp,zonefile)
            # load the new zoneinfo
            reload(lib.dateutil.zoneinfo)
            sb_timezone = tz.tzlocal()
        except:
            _remove_zoneinfo_failed(zonefile_tmp)
            return
    else:
        _remove_zoneinfo_failed(zonefile_tmp)
        logger.log(u"MD5 HASH doesn't match: " + zoneinfo_md5.upper() + ' File: ' + new_hash.upper(),logger.ERROR)
        return

# update the network timezone table
def update_network_dict():

    _remove_old_zoneinfo()
    _update_zoneinfo()

    d = {}

    # network timezones are stored on github pages
    url = 'https://github.com/Prinz23/sb_network_timezones/raw/master/network_timezones.txt'

    url_data = helpers.getURL(url)

    if url_data is None:
        # When urlData is None, trouble connecting to github
        logger.log(u"Loading Network Timezones update failed. Unable to get URL: " + url, logger.ERROR)
        load_network_dict()
        return

    try:
        for line in url_data.splitlines():
           (key, val) = line.decode('utf-8').strip().rsplit(u':',1)
           if key is None or val is None:
               continue
           d[key] = val
    except (IOError, OSError):
        pass

    myDB = db.DBConnection("cache.db")
    # load current network timezones
    old_d = dict(myDB.select("SELECT * FROM network_timezones"))

    # list of sql commands to update the network_timezones table
    ql = []
    for cur_d, cur_t in d.iteritems():
        h_k = old_d.has_key(cur_d)
        if h_k and cur_t != old_d[cur_d]:
            # update old record
            ql.append(["UPDATE network_timezones SET network_name=?, timezone=? WHERE network_name=?", [cur_d, cur_t, cur_d]])
        elif not h_k:
            # add new record
            ql.append(["INSERT INTO network_timezones (network_name, timezone) VALUES (?,?)", [cur_d, cur_t]])
        if h_k:
            del old_d[cur_d]
    # remove deleted records
    if len(old_d) > 0:
        L = list(va for va in old_d)
        ql.append(["DELETE FROM network_timezones WHERE network_name IN ("+','.join(['?'] * len(L))+")", L])
    # change all network timezone infos at once (much faster)
    if len(ql) > 0:
        myDB.mass_action(ql)
        load_network_dict()

# load network timezones from db into dict
def load_network_dict():
    d = {}
    try:
        myDB = db.DBConnection("cache.db")
        cur_network_list = myDB.select("SELECT * FROM network_timezones")
        if cur_network_list is None or len(cur_network_list) < 1:
            update_network_dict()
            cur_network_list = myDB.select("SELECT * FROM network_timezones")
        d = dict(cur_network_list)
    except:
        d = {}
    global network_dict
    network_dict = d

# get timezone of a network or return default timezone
def get_network_timezone(network, network_dict):
    if network is None:
        return sb_timezone

    try:
        if lib.dateutil.zoneinfo.ZONEINFOFILE is not None:
            n_t =  tz.gettz(network_dict[network])
            if n_t is not None:
                return n_t
            else:
                return sb_timezone
        else:
            return sb_timezone
    except:
        return sb_timezone

# parse date and time string into local time
def parse_date_time(d, t, network):
    if network_dict is None:
        load_network_dict()
    mo = time_regex.search(t)
    if mo is not None and len(mo.groups()) >= 5:
        if mo.group(5) is not None:
            try:
                hr = helpers.tryInt(mo.group(1))
                m = helpers.tryInt(mo.group(4))
                ap = mo.group(5)
                # convert am/pm to 24 hour clock
                if ap is not None:
                    if pm_regex.search(ap) is not None and hr != 12:
                        hr += 12
                    elif am_regex.search(ap) is not None and hr == 12:
                        hr -= 12
            except:
                hr = 0
                m = 0
        else:
            try:
                hr = helpers.tryInt(mo.group(1))
                m = helpers.tryInt(mo.group(6))
            except:
                hr = 0
                m = 0
    else:
        hr = 0
        m = 0
    if hr < 0 or hr > 23 or m < 0 or m > 59:
        hr = 0
        m = 0
    te = datetime.datetime.fromordinal(helpers.tryInt(d))
    foreign_timezone = get_network_timezone(network, network_dict)
    foreign_naive = datetime.datetime(te.year, te.month, te.day, hr, m, tzinfo=foreign_timezone)
    try:
        return foreign_naive.astimezone(sb_timezone)
    except (ValueError):
        return foreign_naive

def test_timeformat(t):
    mo = time_regex.search(t)
    if mo is None or len(mo.groups()) < 2:
        return False
    else:
        return True