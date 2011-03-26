import urllib
import sickbeard

from xml.dom import minidom
from sickbeard import logger, common
from sickbeard.notifiers.xbmc import XBMCNotifier 

class PLEXNotifier(XBMCNotifier):

    def notify_snatch(self, ep_name):
        if sickbeard.PLEX_NOTIFY_ONSNATCH:
            self._notifyXBMC(ep_name, common.notifyStrings[common.NOTIFY_SNATCH])

    def notify_download(self, ep_name):
        if sickbeard.PLEX_NOTIFY_ONDOWNLOAD:
            self._notifyXBMC(ep_name, common.notifyStrings[common.NOTIFY_DOWNLOAD])

    def test_notify(self, host, username, password):
        return self._notifyXBMC("Testing Plex notifications from Sick Beard", "Test Notification", host, username, password, force=True)

    def update_library(self):
        if sickbeard.PLEX_UPDATE_LIBRARY:
            self._update_library()

    def _username(self):
        return sickbeard.PLEX_USERNAME

    def _password(self):
        return sickbeard.PLEX_PASSWORD

    def _use_me(self):
        return sickbeard.USE_PLEX

    def _hostname(self):
        return sickbeard.PLEX_HOST


    def _update_library(self):
        if not sickbeard.USE_PLEX:
            logger.log(u"Notifications for Plex Media Server not enabled, skipping library update", logger.DEBUG)
            return False

        logger.log(u"Updating Plex Media Server library", logger.DEBUG)

        if not sickbeard.PLEX_SERVER_HOST:
            logger.log(u"No host specified, no updates done", logger.DEBUG)
            return False

        logger.log(u"Plex Media Server updating " + sickbeard.PLEX_SERVER_HOST, logger.DEBUG)

        url = "http://%s/library/sections" % sickbeard.PLEX_SERVER_HOST
        xml_sections = minidom.parse(urllib.urlopen(url))
        sections = xml_sections.getElementsByTagName('Directory')

        for s in sections:
            if s.getAttribute('type') == "show":
                url = "http://%s/library/sections/%s/refresh" % (sickbeard.PLEX_SERVER_HOST, s.getAttribute('key'))

                try:
                    x = urllib.urlopen(url)
                except Exception, e:
                    logger.log(u"Error updating library section: "+str(e).decode('utf-8'), logger.ERROR)
                    return False

        return True

notifier = PLEXNotifier
