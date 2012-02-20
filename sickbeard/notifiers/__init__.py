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
import growl
import prowl
import tweet
from . import libnotify
import notifo
import boxcar
import nmj
import synoindex
import trakt
import pytivo
import nma

from sickbeard.common import *

xbmc_notifier = xbmc.XBMCNotifier()
plex_notifier = plex.PLEXNotifier()
growl_notifier = growl.GrowlNotifier()
prowl_notifier = prowl.ProwlNotifier()
twitter_notifier = tweet.TwitterNotifier()
notifo_notifier = notifo.NotifoNotifier()
boxcar_notifier = boxcar.BoxcarNotifier()
libnotify_notifier = libnotify.LibnotifyNotifier()
nmj_notifier = nmj.NMJNotifier()
synoindex_notifier = synoindex.synoIndexNotifier()
trakt_notifier = trakt.TraktNotifier()
pytivo_notifier = pytivo.pyTivoNotifier()
nma_notifier = nma.NMA_Notifier()

notifiers = [
    # Libnotify notifier goes first because it doesn't involve blocking on
    # network activity.
    libnotify_notifier,
    xbmc_notifier,
    plex_notifier,
    growl_notifier,
    prowl_notifier,
    twitter_notifier,
    nmj_notifier,
    synoindex_notifier,
    boxcar_notifier,
    trakt_notifier,
    pytivo_notifier,
    nma_notifier,
]

def notify_download(ep_name):
    for n in notifiers:
        n.notify_download(ep_name)
    notifo_notifier.notify_download(ep_name)

def notify_snatch(ep_name):
    for n in notifiers:
        n.notify_snatch(ep_name)
    notifo_notifier.notify_snatch(ep_name)

