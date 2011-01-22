import sickbeard

import xbmc
import growl
import tweet
import prowl

from sickbeard.common import *

xbmc_notifier = xbmc.XBMCNotifier()
growl_notifier = growl.GrowlNotifier()
prowl_notifier = prowl.ProwlNotifier()
twitter_notifier = tweet.TwitterNotifier()

def notify_download(ep_name):
    xbmc_notifier.notify_download(ep_name)
    growl_notifier.notify_download(ep_name)
    prowl_notifier.notify_download(ep_name)
    twitter_notifier.notify_download(ep_name)

def notify_snatch(ep_name):
    xbmc_notifier.notify_snatch(ep_name)
    growl_notifier.notify_snatch(ep_name)
    prowl_notifier.notify_snatch(ep_name)
    twitter_notifier.notify_snatch(ep_name)

def notify(type, message):

    if type == NOTIFY_DOWNLOAD and sickbeard.XBMC_NOTIFY_ONDOWNLOAD == True:
            xbmc.notifyXBMC(message, notifyStrings[type])

    if type == NOTIFY_SNATCH and sickbeard.XBMC_NOTIFY_ONSNATCH:
            xbmc.notifyXBMC(message, notifyStrings[type])

    growl.sendGrowl(notifyStrings[type], message)
    
    prowl.sendProwl(message)

    if type == NOTIFY_DOWNLOAD:
        tweet.notifyTwitter(message)
