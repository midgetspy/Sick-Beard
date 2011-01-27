import sickbeard

import xbmc
import growl
import tweet
try:
    from sickbeard.notifiers import libnotify
except ImportError: # No pynotify installed
    libnotify = None

from sickbeard.common import *

xbmc_notifier = xbmc.XBMCNotifier()
growl_notifier = growl.GrowlNotifier()
twitter_notifier = tweet.TwitterNotifier()

notifiers = [
    xbmc_notifier,
    growl_notifier,
    twitter_notifier,
]

if libnotify is not None:
    # Insert libnotify first because it shouldn't be delayed by notifications
    # going out over the network.
    libnotify_notifier = libnotify.LibnotifyNotifier()
    notifiers.insert(0, libnotify_notifier)

def notify_download(ep_name):
    for n in notifiers:
        n.notify_download(ep_name)

def notify_snatch(ep_name):
    for n in notifiers:
        n.notify_snatch(ep_name)

def notify(type, message):

    if type == NOTIFY_DOWNLOAD and sickbeard.XBMC_NOTIFY_ONDOWNLOAD == True:
            xbmc.notifyXBMC(message, notifyStrings[type])

    if type == NOTIFY_SNATCH and sickbeard.XBMC_NOTIFY_ONSNATCH:
            xbmc.notifyXBMC(message, notifyStrings[type])

    growl.sendGrowl(notifyStrings[type], message)

    if type == NOTIFY_DOWNLOAD:
        tweet.notifyTwitter(message)
