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
from os.path import basename, realpath
import os
import re

# helper to remove failed temp download
def _remove_zoneinfo_failed(filename):
    try:
        os.remove(filename)
    except:
        pass

# update the dateutil zoneinfo
def _update_zoneinfo():

    # now check if the zoneinfo needs update
    url_zv = 'http://github.com/Prinz23/sb_network_timezones/raw/master/zoneinfo.txt'

    url_data = helpers.getURL(url_zv)

    if url_data is None:
        # When urlData is None, trouble connecting to github
        logger.log(u"Loading zoneinfo.txt failed. Unable to get URL: " + url_zv, logger.ERROR)
        return

    if (lib.dateutil.zoneinfo.ZONEINFOFILE != None):
        cur_zoneinfo = ek.ek(basename, lib.dateutil.zoneinfo.ZONEINFOFILE)
    else:
        cur_zoneinfo = None
    (new_zoneinfo, zoneinfo_md5) = url_data.decode('utf-8').strip().rsplit(u' ')

    if ((cur_zoneinfo != None) and (new_zoneinfo == cur_zoneinfo)):
        return

    # now load the new zoneinfo
    url_tar = u'http://github.com/Prinz23/sb_network_timezones/raw/master/' + new_zoneinfo
    zonefile = ek.ek(realpath, u'lib/dateutil/zoneinfo/' + new_zoneinfo)
    zonefile_tmp = re.sub(r"\.tar\.gz$",'.tmp', zonefile)

    if (os.path.exists(zonefile_tmp)):
        try:
            os.remove(zonefile_tmp)
        except:
            logger.log(u"Unable to delete: " + zonefile_tmp,logger.ERROR)
            return

    if not helpers.download_file(url_tar, zonefile_tmp):
        return

    new_hash = str(helpers.md5_for_file(zonefile_tmp))

    if (zoneinfo_md5.upper() == new_hash.upper()):
        logger.log(u"Updating timezone info with new one: " + new_zoneinfo,logger.MESSAGE)
        try:
            # remove the old zoneinfo file
            if (cur_zoneinfo != None):
                old_file = ek.ek(realpath, u'lib/dateutil/zoneinfo/' + cur_zoneinfo)
                if (os.path.exists(old_file)):
                    os.remove(old_file)
            # rename downloaded file
            os.rename(zonefile_tmp,zonefile)
            # load the new zoneinfo
            reload(lib.dateutil.zoneinfo)
        except:
            _remove_zoneinfo_failed(zonefile_tmp)
            return
    else:
        _remove_zoneinfo_failed(zonefile_tmp)
        logger.log(u"MD5 HASH doesn't match: " + zoneinfo_md5.upper() + ' File: ' + new_hash.upper(),logger.ERROR)
        return

# update the network timezone table
def update_network_dict():

    _update_zoneinfo()

    d = {}

    # network timezones are stored on github pages
    url = 'http://github.com/Prinz23/sb_network_timezones/raw/master/network_timezones.txt'

    url_data = helpers.getURL(url)

    if url_data is None:
        # When urlData is None, trouble connecting to github
        logger.log(u"Loading Network Timezones update failed. Unable to get URL: " + url, logger.ERROR)
        return

    try:
        for line in url_data.splitlines():
           (key, val) = line.decode('utf-8').strip().rsplit(u':',1)
           if key == None or val == None:
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
    myDB.mass_action(ql)

# load network timezones from db into dict
def load_network_dict():
    d = {}
    try:
        myDB = db.DBConnection("cache.db")
        cur_network_list = myDB.select("SELECT * FROM network_timezones")
        if cur_network_list == None or len(cur_network_list) < 1:
            update_network_dict()
            cur_network_list = myDB.select("SELECT * FROM network_timezones")
        d = dict(cur_network_list)
    except:
        d = {}
    return d

# get timezone of a network or return default timezone
def get_network_timezone(network, network_dict, sb_timezone):
    if network == None:
        return sb_timezone

    try:
        return tz.gettz(network_dict[network])
    except:
        return sb_timezone