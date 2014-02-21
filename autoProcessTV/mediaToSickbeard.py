#!/usr/bin/env python2

import sys
import os
import time
import ConfigParser
import logging

#Needed for importing logging & requests module
sickbeardPath = os.path.split(os.path.split(sys.argv[0])[0])[0]
sys.path.append(os.path.join( sickbeardPath, 'lib'))
sys.path.append(sickbeardPath)
configFilename = os.path.join(sickbeardPath, "config.ini")

import requests

config = ConfigParser.ConfigParser()

try:
    fp = open(configFilename, "r")
    config.readfp(fp)
    fp.close()
except IOError, e:
    print "Could not find/read Sickbeard config.ini: " + str(e)
    print 'Possibly wrong mediaToSickbeard.py location. Ensure the file is in the autoProcessTV subdir of your Sickbeard installation'
    time.sleep(3)
    sys.exit(1)

scriptlogger = logging.getLogger('mediaToSickbeard')
formatter = logging.Formatter('%(asctime)s %(levelname)-8s MEDIATOSICKBEARD :: %(message)s', '%b-%d %H:%M:%S')

# Get the log dir setting from SB config
logdirsetting = config.get("General", "log_dir") if config.get("General", "log_dir") else 'Logs'
# put the log dir inside the SickBeard dir, unless an absolute path
logdir = os.path.normpath(os.path.join(sickbeardPath, logdirsetting))
logfile = os.path.join(logdir, 'sickbeard.log')

try:
    handler = logging.FileHandler(logfile)
except:
    print 'Unable to open/create the log file at ' + logfile
    time.sleep(3)
    sys.exit()

handler.setFormatter(formatter)
scriptlogger.addHandler(handler)
scriptlogger.setLevel(logging.DEBUG)


def utorrent():
#    print 'Calling utorrent'
    if len(sys.argv) < 2:
        scriptlogger.error('No folder supplied - is this being called from uTorrent?')
        print "No folder supplied - is this being called from uTorrent?"
        time.sleep(3)
        sys.exit()

    dirName = sys.argv[1]
    nzbName = sys.argv[2]
    
    return (dirName, nzbName)
    
def transmission():
    
    dirName = os.getenv('TR_TORRENT_DIR')
    nzbName = os.getenv('TR_TORRENT_NAME')
    
    return (dirName, nzbName)
    
def deluge():

    if len(sys.argv) < 4:
        scriptlogger.error('No folder supplied - is this being called from Deluge?')
        print "No folder supplied - is this being called from Deluge?"
        time.sleep(3)
        sys.exit()
    
    dirName = sys.argv[3]
    nzbName = sys.argv[2]
    
    return (dirName, nzbName)

def blackhole():

    if None != os.getenv('TR_TORRENT_DIR'):
        scriptlogger.debug('Processing script triggered by Transmission')
        print "Processing script triggered by Transmission"
        scriptlogger.debug(u'TR_TORRENT_DIR: ' + os.getenv('TR_TORRENT_DIR'))
        scriptlogger.debug(u'TR_TORRENT_NAME: ' + os.getenv('TR_TORRENT_NAME'))
        dirName = os.getenv('TR_TORRENT_DIR')
        nzbName = os.getenv('TR_TORRENT_NAME')
    else:
        if len(sys.argv) < 2:
            scriptlogger.error('No folder supplied - Your client should invoke the script with a Dir and a Relese Name')
            print "No folder supplied - Your client should invoke the script with a Dir and a Relese Name"
            time.sleep(3)
            sys.exit()

        dirName = sys.argv[1]
        nzbName = sys.argv[2]

    return (dirName, nzbName)

#def sabnzb():
#    if len(sys.argv) < 2:
#        scriptlogger.error('No folder supplied - is this being called from SABnzbd?')
#        print "No folder supplied - is this being called from SABnzbd?"
#        sys.exit()
#    elif len(sys.argv) >= 3:
#        dirName = sys.argv[1]
#        nzbName = sys.argv[2]
#    else:
#        dirName = sys.argv[1]
#        
#    return (dirName, nzbName)    
#
#def hella():        
#    if len(sys.argv) < 4:
#        scriptlogger.error('No folder supplied - is this being called from HellaVCR?')
#        print "No folder supplied - is this being called from HellaVCR?"
#        sys.exit()
#    else:
#        dirName = sys.argv[3]
#        nzbName = sys.argv[2]
#        
#    return (dirName, nzbName)    

def main():

    scriptlogger.info(u'Starting external PostProcess script ' + __file__)

    host = config.get("General", "web_host")
    port = config.get("General", "web_port")
    username = config.get("General", "web_username")
    password = config.get("General", "web_password")
    try:
        ssl = int(config.get("General", "enable_https"))
    except (ConfigParser.NoOptionError, ValueError):
        ssl = 0
        
    try:
        web_root = config.get("General", "web_root")
    except ConfigParser.NoOptionError:
        web_root = ""
    
    tv_dir = config.get("General", "tv_download_dir")
    use_torrents = int(config.get("General", "use_torrents"))
    torrent_method = config.get("General", "torrent_method")
    
    if not use_torrents:
        scriptlogger.error(u'Enable Use Torrent on Sickbeard to use this Script. Aborting!')
        print u'Enable Use Torrent on Sickbeard to use this Script. Aborting!'
        time.sleep(3)
        sys.exit()
        
    if not torrent_method in ['utorrent', 'transmission', 'deluge', 'blackhole']:
        scriptlogger.error(u'Unknown Torrent Method. Aborting!')
        print u'Unknown Torrent Method. Aborting!'
        time.sleep(3)
        sys.exit()
    
    dirName, nzbName = eval(locals()['torrent_method'])()

    if dirName is None:
        scriptlogger.error(u'MediaToSickbeard script need a dir to be run. Aborting!')
        print u'MediaToSickbeard script need a dir to be run. Aborting!'
        time.sleep(3)
        sys.exit()

    if not os.path.isdir(dirName):
        scriptlogger.error(u'Folder ' + dirName + ' does not exist. Aborting AutoPostProcess.')
        print u'Folder ' + dirName + ' does not exist. Aborting AutoPostProcess.'
        time.sleep(3)
        sys.exit()

    if nzbName and os.path.isdir(os.path.join(dirName, nzbName)):
        dirName = os.path.join(dirName, nzbName)
        
    params = {}
        
    params['quiet'] = 1
    
    params['dir'] = dirName
    if nzbName != None:
        params['nzbName'] = nzbName
    
    if ssl:
        protocol = "https://"
    else:
        protocol = "http://"
    
    if host == '0.0.0.0':
        host = 'localhost'
    
    url = protocol + host + ":" + port + web_root + "/home/postprocess/processEpisode"
    
    scriptlogger.debug("Opening URL: " + url + ' with params=' + str(params))   
    print "Opening URL: " + url + ' with params=' + str(params)
    
    try:
        response = requests.get(url, auth=(username, password), params=params)
    except Exception, e:
        scriptlogger.error(u': Unknown exception raised when opening url: ' + ex(e))
        time.sleep(3)
        sys.exit()
    
    if response.status_code == 401:
        scriptlogger.error(u'Invalid Sickbeard Username or Password, check your config')
        print 'Invalid Sickbeard Username or Password, check your config'
        time.sleep(3)
        sys.exit()
    
    if response.status_code == 200:
        scriptlogger.info(u'Script ' + __file__ + ' Succesfull')
        print 'Script ' + __file__ + ' Succesfull'
        time.sleep(3)
        sys.exit()
        
if __name__ == '__main__':
    main()
