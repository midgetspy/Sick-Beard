import sickbeard

import xbmc
import growl
import tweet
import prowl

from sickbeard.common import *

xbmc_notifier = xbmc.XBMCNotifier()
growl_notifier = growl.GrowlNotifier()
twitter_notifier = tweet.TwitterNotifier()

def notify_download(ep_name):
    xbmc_notifier.notify_download(ep_name)
    growl_notifier.notify_download(ep_name)
    twitter_notifier.notify_download(ep_name)

def notify_snatch(ep_name):
    xbmc_notifier.notify_snatch(ep_name)
    growl_notifier.notify_snatch(ep_name)
    twitter_notifier.notify_snatch(ep_name)

def testProwl(prowl_api):
    prowl.sendProwl(prowl_api, "Sick Beard", "Test", "Testing Prowl notification settings from Sick Beard")

def notify(type, message):

    if type == NOTIFY_DOWNLOAD and sickbeard.XBMC_NOTIFY_ONDOWNLOAD == True:
            xbmc.notifyXBMC(message, notifyStrings[type])

    if type == NOTIFY_SNATCH and sickbeard.XBMC_NOTIFY_ONSNATCH:
            xbmc.notifyXBMC(message, notifyStrings[type])

    growl.sendGrowl(notifyStrings[type], message)
    
    prowl.sendProwl(message)

    if type == NOTIFY_DOWNLOAD:
        tweet.notifyTwitter(message)
