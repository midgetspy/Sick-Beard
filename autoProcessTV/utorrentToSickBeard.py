#!/usr/bin/env python

# Author: Marcos Almeida Jr
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
This script extracts downloaded torrent and notify sb.

Configure uTorrent to pass the following command line:
/path/to/Sick-Beard/autoProcessTV/utorrentToSickBeard.py "%I" "%D"

You need to have installed unrar or 7z on your shell path.
'''


import sys, os, re, subprocess,inspect,logging
import autoProcessTV, ConfigParser, glob
import threading

scriptDir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))) 
logfile = os.path.abspath(os.path.join(scriptDir, "..", "Logs", "sickbeard.log"))

loggerHeader = "UTORRENT-TO-SB :: "
logger = logging.getLogger('utorrentToSickbeard')
logger.setLevel(logging.DEBUG)
loggerFormat = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s', '%b-%d %H:%M:%S')

loggerStd = logging.StreamHandler() #console output
loggerStd.setFormatter(loggerFormat)
loggerStd.setLevel(logging.DEBUG)

loggerHdlr = logging.FileHandler(logfile) #file output
loggerHdlr.setFormatter(loggerFormat)
loggerHdlr.setLevel(logging.DEBUG)

logger.addHandler(loggerStd) 
logger.addHandler(loggerHdlr) 

try:
    dir = None
    hash = ""
    
    for item in sys.argv:
        if os.path.isdir(item):
            dir = os.path.abspath(item)
        elif not os.path.isfile(item):
            hash = item

    if not dir:
        logger.warning(loggerHeader + "Parameters not supplied - is this being called from uTorrrent? Check the documentation on utorrentToSickBeard.py.")
        exit()
        
    logger.debug(loggerHeader + "Torrent Dir: " + dir)
    logger.debug(loggerHeader + "Torrent Hash: " + hash)
    logger.info(loggerHeader + "Searching files at " + os.path.join(dir, "*"))
    
    for file in glob.glob(os.path.join(dir, "*")):
        if file.lower().endswith(('.rar', '.zip', '.7z','.avi','.mkv','.mp4')) and 'sample' not in file.lower() and '/subs' not in file.lower():
            if file.lower().endswith(('.rar', '.zip', '.7z')):
                file = os.path.basename(file)
                filePath = os.path.join(dir, file)
                if 'part' not in file.lower() or 'part01' in file.lower():
                    returnCode7z = -1
                    returnCodeUnrar = -1
                    try:
                        returnCode7z = subprocess.call(['7z', 'x', filePath, '-aos', '-o' + dir])
                    except:
                        returnCode7z = -2
                    if returnCode7z != 0 :
                        try: 
                            returnCodeUnrar = subprocess.call(['unrar', 'x', filePath, dir])
                        except:
                            returnCodeUnrar = -2
                    if returnCode7z == -2 and returnCodeUnrar == -2:
                        logger.error(loggerHeader + "Cannot find 7z or unrar on your shell path")
                        sys.exit(1)
                        
                    if returnCode7z != 0 and returnCodeUnrar != 0:
                        logger.error(loggerHeader + "Unable to extract {}".format(file))
                    else:
                        logger.info(loggerHeader + "Successfully extracted {}".format(file))
                        autoProcessTV.processEpisode(dir)            
            else:
                autoProcessTV.processEpisode(dir)  
    logger.info(loggerHeader + "Processing from uTorrent finished.")
    sys.exit(0)
except Exception, e:
    logger.error(str(e))
    sys.exit(1)

