#!/usr/bin/env python

# Author: Marcos Junior
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
import logging

logger = logging.getLogger('transmissionToSickBeard')
logger.setLevel(logging.DEBUG)
loggerFormat = logging.Formatter('%(asctime)s %(levelname)s     TRANSMISSION-TO-SB :: %(message)s', '%Y-%m-%d %H:%M:%S')

loggerStd = logging.StreamHandler() #console output
loggerStd.setFormatter(loggerFormat)
loggerStd.setLevel(logging.DEBUG)

#loggerHdlr = logging.FileHandler(logfile) #file output
#loggerHdlr.setFormatter(loggerFormat)
#loggerHdlr.setLevel(logging.DEBUG)

logger.addHandler(loggerStd) 
#logger.addHandler(loggerHdlr) 

try:
    import syslog, logging.handlers, socket
    sysloggerFormat = logging.Formatter('transmissionToSickBeard[%(process)d]: %(message)s', '%Y-%m-%d %H:%M:%S')
    loggerSyslog = logging.handlers.SysLogHandler(facility=logging.handlers.SysLogHandler.LOG_DAEMON, address="/dev/log") #syslog output
    loggerSyslog.setLevel(logging.DEBUG)
    loggerSyslog.setFormatter(sysloggerFormat)
    logger.addHandler(loggerSyslog) 
except ImportError:
    pass

try:
    dir = os.environ['TR_TORRENT_DIR']
    torrent = os.environ['TR_TORRENT_NAME']
    hash = os.environ['TR_TORRENT_HASH']
    
    if 'movies' in dir:
        type = 'movies/'
    elif 'tv_shows' in dir:
        type = 'tv_shows/'
    else:
        logger.warning("Invalid torrent dir structure. Please read transmissionToSickBeard.py file.")
        sys.exit(1)
    
    config = ConfigParser.ConfigParser()
    configFilename = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessTV.cfg")
    logger.info("Loading config from {}".format(configFilename))
    
    if not os.path.isfile(configFilename):
        logger.error("You need an autoProcessTV.cfg file - did you rename and edit the .sample?")
        sys.exit(1)
    
    try:
        fp = open(configFilename, "r")
        config.readfp(fp)
        fp.close()
    except IOError, e:
        logger.error("Could not read configuration file: {}".format(str(e)))
        sys.exit(1)
    
    host = config.get("Transmission", "host")
    port = config.get("Transmission", "port")
    user = config.get("Transmission", "username")
    password = config.get("Transmission", "password")
    output = os.path.join(config.get("Transmission", "output"), type)
    

    tc = trpc.Client(host, port, user, password)
    torrent = tc.get_torrents(hash)[0]
    for each in torrent.files().values():
        if each['completed'] == each['size']:
            if each['name'].endswith(('.rar','.avi','.mkv','.mp4')) and 'sample' not in each['name'].lower() and '/subs' not in each['name'].lower():
                rarfile = os.path.join(dir, each['name'])
                if each['name'].endswith('.rar'):
                    file = os.path.basename(each['name'])
                    if 'part' not in each['name'] or 'part01' in each['name']:
                        logger.info('Extracting {}...'.format(rarfile))
                        retcode = subprocess.call(['7z', 'x', rarfile, '-aos', '-o' + output])
                        if retcode == 0:
                            logger.info('Successfully extracted {}'.format(rarfile))
                            if 'tv_shows' in type:
                                autoProcessTV.processEpisode(output)
                        else:
                            logger.error('Cannot extract {}'.format(rarfile))
                else:
                    file = os.path.basename(each['name'])
                    os.link(rarfile, os.path.join(output, file))
                    logger.info('Successfully created symlink to {}'.format(rarfile))
                    if 'tv_shows' in type:
                        autoProcessTV.processEpisode(output, file)

except KeyError, e:
    logger.error("Environment Variables not supplied - is this being called from Transmission?")
    sys.exit(1)