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
#  GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.

import sickbeard

import xbmc
import plex
import nmj
import nmjv2
import synoindex
import pytivo

import growl
import prowl
from . import libnotify
import pushover
import boxcar
import boxcar2
import nma

import tweet
import trakt

from sickbeard.common import *
from sickbeard import logger
from sickbeard.exceptions import ex

# home theater/nas
xbmc_notifier = xbmc.XBMCNotifier()
plex_notifier = plex.PLEXNotifier()
nmj_notifier = nmj.NMJNotifier()
nmjv2_notifier = nmjv2.NMJv2Notifier()
synoindex_notifier = synoindex.synoIndexNotifier()
pytivo_notifier = pytivo.pyTivoNotifier()
# devices
growl_notifier = growl.GrowlNotifier()
prowl_notifier = prowl.ProwlNotifier()
libnotify_notifier = libnotify.LibnotifyNotifier()
pushover_notifier = pushover.PushoverNotifier()
boxcar_notifier = boxcar.BoxcarNotifier()
boxcar2_notifier = boxcar2.Boxcar2Notifier()
nma_notifier = nma.NMA_Notifier()
# social
twitter_notifier = tweet.TwitterNotifier()
trakt_notifier = trakt.TraktNotifier()

notifiers = [
    libnotify_notifier,  # Libnotify notifier goes first because it doesn't involve blocking on network activity.
    xbmc_notifier,
    plex_notifier,
    nmj_notifier,
    nmjv2_notifier,
    synoindex_notifier,
    pytivo_notifier,
    growl_notifier,
    prowl_notifier,
    pushover_notifier,
    boxcar_notifier,
    boxcar2_notifier,
    nma_notifier,
    twitter_notifier,
    trakt_notifier,
]


def notify_download(ep_name):
    for n in notifiers:
        try:
            n.notify_download(ep_name)
        except Exception, e:
            logger.log(n.__class__.__name__ + ": " + ex(e), logger.ERROR)


def notify_snatch(ep_name):
    for n in notifiers:
        try:
            n.notify_snatch(ep_name)
        except Exception, e:
            logger.log(n.__class__.__name__ + ": " + ex(e), logger.ERROR)


def update_library(ep_obj):
    for n in notifiers:
        try:
            n.update_library(ep_obj=ep_obj)
        except Exception, e:
            logger.log(n.__class__.__name__ + ": " + ex(e), logger.ERROR)
