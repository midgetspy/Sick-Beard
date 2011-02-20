import sickbeard

import xbmc
import growl
import prowl
import tweet
from . import libnotify
import notifo

from sickbeard.common import *

xbmc_notifier = xbmc.XBMCNotifier()
growl_notifier = growl.GrowlNotifier()
prowl_notifier = prowl.ProwlNotifier()
twitter_notifier = tweet.TwitterNotifier()
notifo_notifier = notifo.NotifoNotifier()
libnotify_notifier = libnotify.LibnotifyNotifier()

notifiers = [
    # Libnotify notifier goes first because it doesn't involve blocking on
    # network activity.
    libnotify_notifier,
    xbmc_notifier,
    growl_notifier,
    prowl_notifier,
    twitter_notifier,
]

def notify_download(ep_name):
    for n in notifiers:
        n.notify_download(ep_name)
    notifo_notifier.notify_download(ep_name)

def notify_snatch(ep_name):
    for n in notifiers:
        n.notify_snatch(ep_name)
    notifo_notifier.notify_snatch(ep_name)

def notify(type, message):

    if type == NOTIFY_DOWNLOAD and sickbeard.XBMC_NOTIFY_ONDOWNLOAD == True:
            xbmc.notifyXBMC(message, notifyStrings[type])

    if type == NOTIFY_SNATCH and sickbeard.XBMC_NOTIFY_ONSNATCH:
            xbmc.notifyXBMC(message, notifyStrings[type])

    growl.sendGrowl(notifyStrings[type], message)
    
    prowl.sendProwl(message)

    notifo.notifyNotifo(message)

    if type == NOTIFY_DOWNLOAD:
        tweet.notifyTwitter(message)
