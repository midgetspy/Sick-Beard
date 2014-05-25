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

import cherrypy
import os.path
import datetime
import re
import urlparse

from sickbeard import encodingKludge as ek
from sickbeard import helpers
from sickbeard import logger
from sickbeard import naming
from sickbeard import db

import sickbeard

naming_ep_type = ("%(seasonnumber)dx%(episodenumber)02d",
                  "s%(seasonnumber)02de%(episodenumber)02d",
                   "S%(seasonnumber)02dE%(episodenumber)02d",
                   "%(seasonnumber)02dx%(episodenumber)02d")
naming_ep_type_text = ("1x02", "s01e02", "S01E02", "01x02")

naming_multi_ep_type = {0: ["-%(episodenumber)02d"] * len(naming_ep_type),
                        1: [" - " + x for x in naming_ep_type],
                        2: [x + "%(episodenumber)02d" for x in ("x", "e", "E", "x")]}
naming_multi_ep_type_text = ("extend", "duplicate", "repeat")

naming_sep_type = (" - ", " ")
naming_sep_type_text = (" - ", "space")


def change_HTTPS_CERT(https_cert):

    if https_cert == '':
        sickbeard.HTTPS_CERT = ''
        return True

    if os.path.normpath(sickbeard.HTTPS_CERT) != os.path.normpath(https_cert):
        if helpers.makeDir(os.path.dirname(os.path.abspath(https_cert))):
            sickbeard.HTTPS_CERT = os.path.normpath(https_cert)
            logger.log(u"Changed https cert path to " + https_cert)
        else:
            return False

    return True


def change_HTTPS_KEY(https_key):

    if https_key == '':
        sickbeard.HTTPS_KEY = ''
        return True

    if os.path.normpath(sickbeard.HTTPS_KEY) != os.path.normpath(https_key):
        if helpers.makeDir(os.path.dirname(os.path.abspath(https_key))):
            sickbeard.HTTPS_KEY = os.path.normpath(https_key)
            logger.log(u"Changed https key path to " + https_key)
        else:
            return False

    return True


def change_LOG_DIR(log_dir, web_log):

    log_dir_changed = False
    abs_log_dir = os.path.normpath(os.path.join(sickbeard.DATA_DIR, log_dir))
    web_log_value = checkbox_to_value(web_log)

    if os.path.normpath(sickbeard.LOG_DIR) != abs_log_dir:
        if helpers.makeDir(abs_log_dir):
            sickbeard.ACTUAL_LOG_DIR = os.path.normpath(log_dir)
            sickbeard.LOG_DIR = abs_log_dir

            logger.sb_log_instance.initLogging()
            logger.log(u"Initialized new log file in " + sickbeard.LOG_DIR)
            log_dir_changed = True

        else:
            return False

    if sickbeard.WEB_LOG != web_log_value or log_dir_changed == True:

        sickbeard.WEB_LOG = web_log_value

        if sickbeard.WEB_LOG:
            cherry_log = os.path.join(sickbeard.LOG_DIR, "cherrypy.log")
            logger.log(u"Change cherry log file to " + cherry_log)
        else:
            cherry_log = None
            logger.log(u"Disable cherry logging")

        cherrypy.config.update({'log.access_file': cherry_log})

    return True


def change_NZB_DIR(nzb_dir):

    if nzb_dir == '':
        sickbeard.NZB_DIR = ''
        return True

    if os.path.normpath(sickbeard.NZB_DIR) != os.path.normpath(nzb_dir):
        if helpers.makeDir(nzb_dir):
            sickbeard.NZB_DIR = os.path.normpath(nzb_dir)
            logger.log(u"Changed NZB folder to " + nzb_dir)
        else:
            return False

    return True


def change_TORRENT_DIR(torrent_dir):

    if torrent_dir == '':
        sickbeard.TORRENT_DIR = ''
        return True

    if os.path.normpath(sickbeard.TORRENT_DIR) != os.path.normpath(torrent_dir):
        if helpers.makeDir(torrent_dir):
            sickbeard.TORRENT_DIR = os.path.normpath(torrent_dir)
            logger.log(u"Changed torrent folder to " + torrent_dir)
        else:
            return False

    return True


def change_TV_DOWNLOAD_DIR(tv_download_dir):

    if tv_download_dir == '':
        sickbeard.TV_DOWNLOAD_DIR = ''
        return True

    if os.path.normpath(sickbeard.TV_DOWNLOAD_DIR) != os.path.normpath(tv_download_dir):
        if helpers.makeDir(tv_download_dir):
            sickbeard.TV_DOWNLOAD_DIR = os.path.normpath(tv_download_dir)
            logger.log(u"Changed TV download folder to " + tv_download_dir)
        else:
            return False

    return True


def change_SEARCH_FREQUENCY(freq):

    sickbeard.SEARCH_FREQUENCY = to_int(freq, default=sickbeard.DEFAULT_SEARCH_FREQUENCY)

    if sickbeard.SEARCH_FREQUENCY < sickbeard.MIN_SEARCH_FREQUENCY:
        sickbeard.SEARCH_FREQUENCY = sickbeard.MIN_SEARCH_FREQUENCY

    sickbeard.currentSearchScheduler.cycleTime = datetime.timedelta(minutes=sickbeard.SEARCH_FREQUENCY)
    sickbeard.backlogSearchScheduler.cycleTime = datetime.timedelta(minutes=sickbeard.get_backlog_cycle_time())


def change_VERSION_NOTIFY(version_notify):

    oldSetting = sickbeard.VERSION_NOTIFY

    sickbeard.VERSION_NOTIFY = version_notify

    if version_notify == False:
        sickbeard.NEWEST_VERSION_STRING = None

    if oldSetting == False and version_notify == True:
        sickbeard.versionCheckScheduler.action.run()  # @UndefinedVariable


def CheckSection(CFG, sec):
    """ Check if INI section exists, if not create it """
    try:
        CFG[sec]
        return True
    except:
        CFG[sec] = {}
        return False


def checkbox_to_value(option, value_on=1, value_off=0):
    """
    Turns checkbox option 'on' or 'true' to value_on (1)
    any other value returns value_off (0)
    """
    if option == 'on' or option == 'true':
        return value_on

    return value_off


def clean_host(host, default_port=None):
    """
    Returns host or host:port or empty string from a given url or host
    If no port is found and default_port is given use host:default_port
    """

    host = host.strip()

    if host:

        match_host_port = re.search(r'(?:http.*://)?(?P<host>[^:/]+).?(?P<port>[0-9]*).*', host)

        cleaned_host = match_host_port.group('host')
        cleaned_port = match_host_port.group('port')

        if cleaned_host:

            if cleaned_port:
                host = cleaned_host + ':' + cleaned_port

            elif default_port:
                host = cleaned_host + ':' + str(default_port)

            else:
                host = cleaned_host

        else:
            host = ''

    return host


def clean_hosts(hosts, default_port=None):

    cleaned_hosts = []

    for cur_host in [x.strip() for x in hosts.split(",")]:
        if cur_host:
            cleaned_host = clean_host(cur_host, default_port)
            if cleaned_host:
                cleaned_hosts.append(cleaned_host)

    if cleaned_hosts:
        cleaned_hosts = ",".join(cleaned_hosts)

    else:
        cleaned_hosts = ''

    return cleaned_hosts


def clean_url(url):
    """
    Returns an cleaned url starting with a scheme and folder with trailing /
    or an empty string
    """

    if url and url.strip():

        url = url.strip()

        if '://' not in url:
            url = '//' + url

        scheme, netloc, path, query, fragment = urlparse.urlsplit(url, 'http')

        if not path.endswith('/'):
            basename, ext = ek.ek(os.path.splitext, ek.ek(os.path.basename, path))  # @UnusedVariable
            if not ext:
                path = path + '/'

        cleaned_url = urlparse.urlunsplit((scheme, netloc, path, query, fragment))

    else:
        cleaned_url = ''

    return cleaned_url


def to_int(val, default=0):
    """ Return int value of val or default on error """

    try:
        val = int(val)
    except:
        val = default

    return val


################################################################################
# Check_setting_int                                                            #
################################################################################
def minimax(val, default, low, high):
    """ Return value forced within range """

    val = to_int(val, default=default)

    if val < low:
        return low
    if val > high:
        return high

    return val


################################################################################
# Check_setting_int                                                            #
################################################################################
def check_setting_int(config, cfg_name, item_name, def_val):
    try:
        my_val = int(config[cfg_name][item_name])
    except:
        my_val = def_val
        try:
            config[cfg_name][item_name] = my_val
        except:
            config[cfg_name] = {}
            config[cfg_name][item_name] = my_val
    logger.log(item_name + " -> " + str(my_val), logger.DEBUG)
    return my_val


################################################################################
# Check_setting_float                                                          #
################################################################################
def check_setting_float(config, cfg_name, item_name, def_val):
    try:
        my_val = float(config[cfg_name][item_name])
    except:
        my_val = def_val
        try:
            config[cfg_name][item_name] = my_val
        except:
            config[cfg_name] = {}
            config[cfg_name][item_name] = my_val

    logger.log(item_name + " -> " + str(my_val), logger.DEBUG)
    return my_val


################################################################################
# Check_setting_str                                                            #
################################################################################
def check_setting_str(config, cfg_name, item_name, def_val, log=True):
    try:
        my_val = config[cfg_name][item_name]
    except:
        my_val = def_val
        try:
            config[cfg_name][item_name] = my_val
        except:
            config[cfg_name] = {}
            config[cfg_name][item_name] = my_val

    if log:
        logger.log(item_name + " -> " + my_val, logger.DEBUG)
    else:
        logger.log(item_name + " -> ******", logger.DEBUG)
    return my_val


class ConfigMigrator():

    def __init__(self, config_obj):
        """
        Initializes a config migrator that can take the config from the version indicated in the config
        file up to the version required by SB
        """

        self.config_obj = config_obj

        # check the version of the config
        self.config_version = check_setting_int(config_obj, 'General', 'config_version', sickbeard.CONFIG_VERSION)
        self.expected_config_version = sickbeard.CONFIG_VERSION
        self.migration_names = {1: 'Custom naming',
                                2: 'Sync backup number with version number',
                                3: 'Rename omgwtfnzb variables',
                                4: 'Add newznab catIDs',
                                5: 'Metadata update'
                                }

    def migrate_config(self):
        """
        Calls each successive migration until the config is the same version as SB expects
        """

        if self.config_version > self.expected_config_version:
            logger.log_error_and_exit(u"Your config version (" + str(self.config_version) + ") has been incremented past what this version of Sick Beard supports (" + str(self.expected_config_version) + ").\n" + \
                                      "If you have used other forks or a newer version of Sick Beard, your config file may be unusable due to their modifications.")

        sickbeard.CONFIG_VERSION = self.config_version

        while self.config_version < self.expected_config_version:

            next_version = self.config_version + 1

            if next_version in self.migration_names:
                migration_name = ': ' + self.migration_names[next_version]
            else:
                migration_name = ''

            logger.log(u"Backing up config before upgrade")
            if not helpers.backupVersionedFile(sickbeard.CONFIG_FILE, self.config_version):
                logger.log_error_and_exit(u"Config backup failed, abort upgrading config")
            else:
                logger.log(u"Proceeding with upgrade")

            # do the migration, expect a method named _migrate_v<num>
            logger.log(u"Migrating config up to version " + str(next_version) + migration_name)
            getattr(self, '_migrate_v' + str(next_version))()
            self.config_version = next_version

            # save new config after migration
            sickbeard.CONFIG_VERSION = self.config_version
            logger.log(u"Saving config file to disk")
            sickbeard.save_config()

    # Migration v1: Custom naming
    def _migrate_v1(self):
        """
        Reads in the old naming settings from your config and generates a new config template from them.
        """

        sickbeard.NAMING_PATTERN = self._name_to_pattern()
        logger.log("Based on your old settings I'm setting your new naming pattern to: " + sickbeard.NAMING_PATTERN)

        sickbeard.NAMING_CUSTOM_ABD = bool(check_setting_int(self.config_obj, 'General', 'naming_dates', 0))

        if sickbeard.NAMING_CUSTOM_ABD:
            sickbeard.NAMING_ABD_PATTERN = self._name_to_pattern(True)
            logger.log("Adding a custom air-by-date naming pattern to your config: " + sickbeard.NAMING_ABD_PATTERN)
        else:
            sickbeard.NAMING_ABD_PATTERN = naming.name_abd_presets[0]

        sickbeard.NAMING_MULTI_EP = int(check_setting_int(self.config_obj, 'General', 'naming_multi_ep_type', 1))

        # see if any of their shows used season folders
        myDB = db.DBConnection()
        season_folder_shows = myDB.select("SELECT * FROM tv_shows WHERE flatten_folders = 0")

        # if any shows had season folders on then prepend season folder to the pattern
        if season_folder_shows:

            old_season_format = check_setting_str(self.config_obj, 'General', 'season_folders_format', 'Season %02d')

            if old_season_format:
                try:
                    new_season_format = old_season_format % 9
                    new_season_format = new_season_format.replace('09', '%0S')
                    new_season_format = new_season_format.replace('9', '%S')

                    logger.log(u"Changed season folder format from " + old_season_format + " to " + new_season_format + ", prepending it to your naming config")
                    sickbeard.NAMING_PATTERN = new_season_format + os.sep + sickbeard.NAMING_PATTERN

                except (TypeError, ValueError):
                    logger.log(u"Can't change " + old_season_format + " to new season format", logger.ERROR)

        # if no shows had it on then don't flatten any shows and don't put season folders in the config
        else:

            logger.log(u"No shows were using season folders before so I'm disabling flattening on all shows")

            # don't flatten any shows at all
            myDB.action("UPDATE tv_shows SET flatten_folders = 0")

        sickbeard.NAMING_FORCE_FOLDERS = naming.check_force_season_folders()

    def _name_to_pattern(self, abd=False):

        # get the old settings from the file
        use_periods = bool(check_setting_int(self.config_obj, 'General', 'naming_use_periods', 0))
        ep_type = check_setting_int(self.config_obj, 'General', 'naming_ep_type', 0)
        sep_type = check_setting_int(self.config_obj, 'General', 'naming_sep_type', 0)
        use_quality = bool(check_setting_int(self.config_obj, 'General', 'naming_quality', 0))

        use_show_name = bool(check_setting_int(self.config_obj, 'General', 'naming_show_name', 1))
        use_ep_name = bool(check_setting_int(self.config_obj, 'General', 'naming_ep_name', 1))

        # make the presets into templates
        naming_ep_type = ("%Sx%0E",
                          "s%0Se%0E",
                          "S%0SE%0E",
                          "%0Sx%0E")
        naming_sep_type = (" - ", " ")

        # set up our data to use
        if use_periods:
            show_name = '%S.N'
            ep_name = '%E.N'
            ep_quality = '%Q.N'
            abd_string = '%A.D'
        else:
            show_name = '%SN'
            ep_name = '%EN'
            ep_quality = '%QN'
            abd_string = '%A-D'

        if abd:
            ep_string = abd_string
        else:
            ep_string = naming_ep_type[ep_type]

        finalName = ""

        # start with the show name
        if use_show_name:
            finalName += show_name + naming_sep_type[sep_type]

        # add the season/ep stuff
        finalName += ep_string

        # add the episode name
        if use_ep_name:
            finalName += naming_sep_type[sep_type] + ep_name

        # add the quality
        if use_quality:
            finalName += naming_sep_type[sep_type] + ep_quality

        if use_periods:
            finalName = re.sub("\s+", ".", finalName)

        return finalName

    # Migration v2: Dummy migration to sync backup number with config version number
    def _migrate_v2(self):
        return

    # Migration v2: Rename omgwtfnzb variables
    def _migrate_v3(self):
        """
        Reads in the old naming settings from your config and generates a new config template from them.
        """
        # get the old settings from the file and store them in the new variable names
        sickbeard.OMGWTFNZBS_USERNAME = check_setting_str(self.config_obj, 'omgwtfnzbs', 'omgwtfnzbs_uid', '')
        sickbeard.OMGWTFNZBS_APIKEY = check_setting_str(self.config_obj, 'omgwtfnzbs', 'omgwtfnzbs_key', '')

    # Migration v4: Add default newznab catIDs
    def _migrate_v4(self):
        """ Update newznab providers so that the category IDs can be set independently via the config """

        new_newznab_data = []
        old_newznab_data = check_setting_str(self.config_obj, 'Newznab', 'newznab_data', '')

        if old_newznab_data:
            old_newznab_data_list = old_newznab_data.split("!!!")

            for cur_provider_data in old_newznab_data_list:
                try:
                    name, url, key, enabled = cur_provider_data.split("|")
                except ValueError:
                    logger.log(u"Skipping Newznab provider string: '" + cur_provider_data + "', incorrect format", logger.ERROR)
                    continue

                if name == 'Sick Beard Index':
                    key = '0'

                if name == 'NZBs.org':
                    catIDs = '5030,5040,5070,5090'
                else:
                    catIDs = '5030,5040'

                cur_provider_data_list = [name, url, key, catIDs, enabled]
                new_newznab_data.append("|".join(cur_provider_data_list))

            sickbeard.NEWZNAB_DATA = "!!!".join(new_newznab_data)

    # Migration v5: Metadata upgrade
    def _migrate_v5(self):
        """ Updates metadata values to the new format """

        """ Quick overview of what the upgrade does:

        new | old | description (new)
        ----+-----+--------------------
          1 |  1  | show metadata
          2 |  2  | episode metadata
          3 |  4  | show fanart
          4 |  3  | show poster
          5 |  -  | show banner
          6 |  5  | episode thumb
          7 |  6  | season poster
          8 |  -  | season banner
          9 |  -  | season all poster
         10 |  -  | season all banner

        Note that the ini places start at 1 while the list index starts at 0.
        old format: 0|0|0|0|0|0 -- 6 places
        new format: 0|0|0|0|0|0|0|0|0|0 -- 10 places

        Drop the use of use_banner option.
        Migrate the poster override to just using the banner option (applies to xbmc only).
        """

        metadata_xbmc = check_setting_str(self.config_obj, 'General', 'metadata_xbmc', '0|0|0|0|0|0')
        metadata_xbmc_12plus = check_setting_str(self.config_obj, 'General', 'metadata_xbmc_12plus', '0|0|0|0|0|0')
        metadata_mediabrowser = check_setting_str(self.config_obj, 'General', 'metadata_mediabrowser', '0|0|0|0|0|0')
        metadata_ps3 = check_setting_str(self.config_obj, 'General', 'metadata_ps3', '0|0|0|0|0|0')
        metadata_wdtv = check_setting_str(self.config_obj, 'General', 'metadata_wdtv', '0|0|0|0|0|0')
        metadata_tivo = check_setting_str(self.config_obj, 'General', 'metadata_tivo', '0|0|0|0|0|0')
        metadata_mede8er = check_setting_str(self.config_obj, 'General', 'metadata_mede8er', '0|0|0|0|0|0')

        use_banner = bool(check_setting_int(self.config_obj, 'General', 'use_banner', 0))

        def _migrate_metadata(metadata, metadata_name, use_banner):
            cur_metadata = metadata.split('|')
            # if target has the old number of values, do upgrade
            if len(cur_metadata) == 6:
                logger.log(u"Upgrading " + metadata_name + " metadata, old value: " + metadata)
                cur_metadata.insert(4, '0')
                cur_metadata.append('0')
                cur_metadata.append('0')
                cur_metadata.append('0')
                # swap show fanart, show poster
                cur_metadata[3], cur_metadata[2] = cur_metadata[2], cur_metadata[3]
                # if user was using use_banner to override the poster, instead enable the banner option and deactivate poster
                if metadata_name == 'XBMC' and use_banner:
                    cur_metadata[4], cur_metadata[3] = cur_metadata[3], '0'
                # write new format
                metadata = '|'.join(cur_metadata)
                logger.log(u"Upgrading " + metadata_name + " metadata, new value: " + metadata)

            elif len(cur_metadata) == 10:
                metadata = '|'.join(cur_metadata)
                logger.log(u"Keeping " + metadata_name + " metadata, value: " + metadata)

            else:
                logger.log(u"Skipping " + metadata_name + " metadata: '" + metadata + "', incorrect format", logger.ERROR)
                metadata = '0|0|0|0|0|0|0|0|0|0'
                logger.log(u"Setting " + metadata_name + " metadata, new value: " + metadata)

            return metadata

        sickbeard.METADATA_XBMC = _migrate_metadata(metadata_xbmc, 'XBMC', use_banner)
        sickbeard.METADATA_XBMC_12PLUS = _migrate_metadata(metadata_xbmc_12plus, 'XBMC 12+', use_banner)
        sickbeard.METADATA_MEDIABROWSER = _migrate_metadata(metadata_mediabrowser, 'MediaBrowser', use_banner)
        sickbeard.METADATA_PS3 = _migrate_metadata(metadata_ps3, 'PS3', use_banner)
        sickbeard.METADATA_WDTV = _migrate_metadata(metadata_wdtv, 'WDTV', use_banner)
        sickbeard.METADATA_TIVO = _migrate_metadata(metadata_tivo, 'TIVO', use_banner)
        sickbeard.METADATA_MEDE8ER = _migrate_metadata(metadata_mede8er, 'Mede8er', use_banner)

    # Migration v6: Synology notifier update
    def _migrate_v6(self):
        """ Updates Synology notifier to reflect that their now is an update library option instead misusing the enable option """

        # clone use_synoindex to update_library since this now has notification options
        sickbeard.SYNOINDEX_UPDATE_LIBRARY = bool(check_setting_int(self.config_obj, 'Synology', 'use_synoindex', 0))
