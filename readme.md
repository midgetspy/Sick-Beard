Sick Beard
=====

*Sick Beard is currently an alpha release. There may be severe bugs in it and at any given time it may not work at all.*

Sick Beard is a PVR for newsgroup users (with limited torrent support). It watches for new episodes of your favorite shows and when they are posted it downloads them, sorts and renames them, and optionally generates metadata for them. It currently supports Newzbin, TVBinz, NZBs.org, NZBMatrix, TVNZB, and EZTV.it and retrieves show information from theTVDB.com and TVRage.com.

Features include:

* automatic episode downloads for torrents and NZBs from any number of the 6 different supported index sites
* XBMC library updates, poster/fanart downloads, and NFO/TBN generation
* renames episode files for any show
* sends NZBs directly to SABnzbd, prioritizes and categorizes them properly
* available for any platform, uses simple HTTP interface
* can notify XBMC or use Growl to notify any Windows PC when new episodes are downloaded
* specials and double episode support


Sick Beard makes use of the following projects:
* [http://www.cherrypy.org][cherrypy]
* [http://www.cheetahtemplate.org/][Cheetah]
* [http://code.google.com/p/simplejson/][simplejson]
* [http://github.com/dbr/tvdb_api][tvdb_api]
* [http://github.com/dbr/tvnamer][tvnamer]
* [http://www.voidspace.org.uk/python/configobj.html][ConfigObj]
* [http://www.sabnzbd.org/][SABnzbd+]
* [http://jquery.com][jQuery]
* [http://github.com/kfdm/gntp][Python GNTP]


## Dependencies

To run Sick Beard from source you will need Python 2.5+ and Cheetah 2.1.0+. The [http://code.google.com/p/sickbeard/downloads/list][binary releases] are standalone.

## Bugs

If you find a bug please report it or it'll never get fixed. Verify that it hasn't [http://code.google.com/p/sickbeard/issues/list][already been submitted] and then [http://code.google.com/p/sickbeard/issues/entry][log a new bug]. Be sure to provide as much information as possible.