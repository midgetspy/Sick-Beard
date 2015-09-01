Sick Beard PVR
=====

This fork of the Sick Beard project adds in support for pvr recording software. Currently the only software supported is [NextPVR][nextPVR], although in theory others could be added.

I find it useful for recording shows that might not be available via NZB or Torrent files or if you'd prefer not to use those methods but still want Sick Beard to manage all of your TV shows.

Please see the original [Sick Beard][sickbeard] documentation for initial setup.  If you already have a configured and running Sick Beard instance, you should be able to grab this source, copy your config.ini and sickbeard.db files into this project and start it up.


## Configuration

In order to configure the new functionality, you need to set options in 3 places in the Config menu -

* **Search Settings** - Check the **Search PVRs** box and choose how HD channels will be determined along with how many days in advance recordings will be scheduled. Recommended setting is about 2 or 3 days.  Save your choices.

* **Search Providers** - Ensure that the PVR you want to use is checked in the **Priorities** section. You also need to configure any options listed in **Configure Built-In Providers** for the selected pvr. For NextPVR it is just the url where it is running.

* **Post Processing** - Choose what you would like to happen if a show is both recorded and downloaded. Your options are to do nothing and leave the recording, unschedule the recording if it has not yet recorded, or delete the recording if it already has recorded.

Any post processing such as commercial removal, video compression, renaming etc is currently left up to the PVR software.  Although, once that is complete, you can use the autoProcessTV script to import into Sick Beard.


[nextPVR]: http://nextpvr.com/
[sickbeard]: http://sickbeard.com/
