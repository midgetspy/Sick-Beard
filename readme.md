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
* [cherrypy][cherrypy]
* [Cheetah][cheetah]
* [simplejson][simplejson]
* [tvdb_api][tvdb_api]
* [tvnamer][tvnamer]
* [ConfigObj][configobj]
* [SABnzbd+][sabnzbd]
* [jQuery][jquery]
* [Python GNTP][pythongntp]

## Dependencies

To run Sick Beard from source you will need Python 2.5+ and Cheetah 2.1.0+. The [binary releases][googledownloads] are standalone.

## Bugs

If you find a bug please report it or it'll never get fixed. Verify that it hasn't [already been submitted][googleissues] and then [log a new bug][googlenewissue]. Be sure to provide as much information as possible.

[cherrypy]: http://www.cherrypy.org
[cheetah]: http://www.cheetahtemplate.org/
[simplejson]: http://code.google.com/p/simplejson/ 
[tvdb_api]: http://github.com/dbr/tvdb_api
[tvnamer]: http://github.com/dbr/tvnamer
[configobj]: http://www.voidspace.org.uk/python/configobj.html
[sabnzbd]: http://www.sabnzbd.org/
[jquery]: http://jquery.com
[pythongntp]: http://github.com/kfdm/gntp
[googledownloads]: http://code.google.com/p/sickbeard/downloads/list
[googleissues]: http://code.google.com/p/sickbeard/issues/list
[googlenewissue]: http://code.google.com/p/sickbeard/issues/entry