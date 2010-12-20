import sickbeard

import xbmc
import growl
import tweet
import prowl

from sickbeard.common import *


def testGrowl(host, password):
    growl.sendGrowl("Test Growl", "Testing Growl settings from Sick Beard", "Test", host, password)

def testXBMC(host, username, password):
    xbmc.notifyXBMC("Testing XBMC notifications from Sick Beard", "Test Notification", host, username, password)

def testTwitter1():
    return tweet.get_authorization()

def testTwitter2(key):
    return tweet.get_credentials(key)

def testTwitter():
    return tweet.notifyTwitter("This is a test notification from Sick Beard", force=True)

def testProwl(prowl_api=None):
    prowl.sendProwl("Sick Beard", "Test", "Testing Prowl notification settings from Sick Beard", prowl_api)

def notify(type, message):

    if type == NOTIFY_DOWNLOAD and sickbeard.XBMC_NOTIFY_ONDOWNLOAD == True:
            xbmc.notifyXBMC(message, notifyStrings[type])

    if type == NOTIFY_SNATCH and sickbeard.XBMC_NOTIFY_ONSNATCH:
            xbmc.notifyXBMC(message, notifyStrings[type])

    growl.sendGrowl(notifyStrings[type], message)
    
    prowl.sendProwl(message)

    if type == NOTIFY_DOWNLOAD:
        tweet.notifyTwitter(message)
