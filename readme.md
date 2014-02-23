Sick Beard
=====

*SickBeard TPB  is currently an alpha release. There may be severe bugs in it and at any given time it may not work at all.*

Sick Beard TPB is a PVR for torrent and newsgroup users. It watches for new episodes of your favorite shows and when they are posted it downloads them, sorts and renames them, and optionally generates metadata for them. It retrieves show information from theTVDB.com and TVRage.com.

Features include:

* automatically retrieves new episode torrent or nzb files
* can scan your existing library and then download any old seasons or episodes you're missing
* can watch for better versions and upgrade your existing episodes (to from TV DVD/BluRay for example)
* XBMC library updates, poster/fanart downloads, and NFO/TBN generation
* configurable episode renaming
* sends NZBs directly to SABnzbd, prioritizes and categorizes them properly
* available for any platform, uses simple HTTP interface
* can notify XBMC, Growl, or Twitter when new episodes are downloaded
* specials and double episode support


Sick Beard makes use of the following projects:

* [cherrypy][cherrypy]
* [Cheetah][cheetah]
* [simplejson][simplejson]
* [tvdb_api][tvdb_api]
* [ConfigObj][configobj]
* [SABnzbd+][sabnzbd]
* [jQuery][jquery]
* [Python GNTP][pythongntp]
* [SocksiPy][socks]
* [python-dateutil][dateutil]
* [jsonrpclib][jsonrpclib]
* [Subliminal][subliminal]

## Dependencies

To run Sick Beard from source you will need Python 2.6+ and Cheetah 2.1.0+. The [binary releases][googledownloads] are standalone.

## Bugs

If you find a bug please report here on Github [githubissue]. Verify that it hasn't already been submitted and then [log a new bug]. Be sure to provide a sickbeard log in debug mode where is the error evidence or it'll never get fixed.
[cherrypy]: http://www.cherrypy.org
[cheetah]: http://www.cheetahtemplate.org/
[simplejson]: http://code.google.com/p/simplejson/ 
[tvdb_api]: http://github.com/dbr/tvdb_api
[configobj]: http://www.voidspace.org.uk/python/configobj.html
[sabnzbd]: http://www.sabnzbd.org/
[jquery]: http://jquery.com
[pythongntp]: http://github.com/kfdm/gntp
[socks]: http://code.google.com/p/socksipy-branch/
[dateutil]: http://labix.org/python-dateutil
[googledownloads]: http://code.google.com/p/sickbeard/downloads/list
[githubissues]: https://github.com/mr-orange/Sick-Beard/issues?state=open
[githubnewissue]: https://github.com/mr-orange/Sick-Beard/issues/new
[jsonrpclib]: https://github.com/joshmarshall/jsonrpclib
[subliminal]: https://github.com/Diaoul/subliminal