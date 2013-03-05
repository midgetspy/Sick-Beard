#!/usr/bin/env python

# Author: Ryan Snyder
#
# This file is part of Sick Beard.
#
# Sick Beard is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Sick Beard is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.


'''
This script expects 'tv_shows' or 'movies' to be in the path that 
transmission is downloading to. Example: /nas/transmission/tv_shows/

It also moves/extracts files to a folder of that type.
Example: /nas/processing/tv_shows

Make sure this is how you have it set up and that the processing 
folders exist. 

'''


import sys, os, re, subprocess
import transmissionrpc as trpc
import autoProcessTV ,ConfigParser

try:
    dir = os.environ['TR_TORRENT_DIR']
    torrent = os.environ['TR_TORRENT_NAME']
    hash = os.environ['TR_TORRENT_HASH']
    print dir
    
    if 'movies' in dir:
        type = 'movies/'
    elif 'tv_shows' in dir:
        type = 'tv_shows/'
    else:
        exit()
    
    config = ConfigParser.ConfigParser()
    configFilename = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessTV.cfg")
    print "Loading config from", configFilename
    
    if not os.path.isfile(configFilename):
        print "ERROR: You need an autoProcessTV.cfg file - did you rename and edit the .sample?"
        sys.exit(-1)
    
    try:
        fp = open(configFilename, "r")
        config.readfp(fp)
        fp.close()
    except IOError, e:
        print "Could not read configuration file: ", str(e)
        sys.exit(1)
    
    host = config.get("Transmission", "host")
    port = config.get("Transmission", "port")
    user = config.get("Transmission", "username")
    password = config.get("Transmission", "password")
    output = config.get("Transmission", "output") + type
    

    tc = trpc.Client(host, port, user, password)
    torrent = tc.get_torrents(hash)[0]
    for each in torrent.files().values():
        if each['completed'] == each['size']:
            if each['name'].endswith(('.rar','.avi','.mkv','.mp4')) and 'sample' not in each['name'].lower() and '/subs' not in each['name'].lower():
                if each['name'].endswith('.rar'):
                    file = os.path.basename(each['name'])
                    if 'part' not in each['name'] or 'part01' in each['name']:
                        print file
                        print dir + each['name']
                        print output
                        subprocess.call(['7z', 'x', dir + each['name'], '-aos', '-o' + output])
                        print 'Successfully extracted {}'.format(dir + each['name'])
                        if 'tv_shows' in type:
                            autoProcessTV.processEpisode(output)                       
                else:
                    file = os.path.basename(each['name'])
                    os.link(dir + each['name'], output + file)
                    if 'tv_shows' in type:
                        autoProcessTV.processEpisode(output, file)

except KeyError, e:
    print "Environment Variables not supplied - is this being called from Transmission?"
    sys.exit()