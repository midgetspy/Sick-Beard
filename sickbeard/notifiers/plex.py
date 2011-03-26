import urllib
import sickbeard

from xml.dom import minidom
from sickbeard import logger, common

class PLEXNotifier:

    def test_notify(self, host=None):
        return self._test_notify(host, force=True)

    def notify_snatch(self, ep_name):
        pass

    def notify_download(self, ep_name):
        pass

    def update_library(self):
        if sickbeard.PLEX_UPDATE_LIBRARY:
            self._update_library()


    def _test_notify(self, host=None, force=False):
        if not sickbeard.USE_PLEX and not force:
            logger.log(u"Notification for Plex Media Server not enabled, skipping this notification", logger.DEBUG)
            return False
        else:
            if not host:
                host = sickbeard.PLEX_HOST

            try:
                url = "http://%s/library/sections" % host
                xml_sections = minidom.parse(urllib.urlopen(url))
                return True
            except Exception, e:
                logger.log(u"Error testing notifications: "+str(e).decode('utf-8'), logger.ERROR)
                return False


    def _update_library(self):
        if not sickbeard.USE_PLEX:
            logger.log(u"Notifications for Plex Media Server not enabled, skipping library update", logger.DEBUG)
            return False

        logger.log(u"Updating Plex Media Server library", logger.DEBUG)

        if not sickbeard.PLEX_HOST:
            logger.log(u"No host specified, no updates done", logger.DEBUG)
            return False

        logger.log(u"Plex Media Server updating " + sickbeard.PLEX_HOST, logger.DEBUG)

        url = "http://%s/library/sections" % sickbeard.PLEX_HOST
        xml_sections = minidom.parse(urllib.urlopen(url))
        sections = xml_sections.getElementsByTagName('Directory')

        for s in sections:
            if s.getAttribute('type') == "show":
                url = "http://%s/library/sections/%s/refresh" % (sickbeard.PLEX_HOST, s.getAttribute('key'))

                try:
                    x = urllib.urlopen(url)
                except Exception, e:
                    logger.log(u"Error updating library section: "+str(e).decode('utf-8'), logger.ERROR)
                    return False

        return True

notifier = PLEXNotifier
