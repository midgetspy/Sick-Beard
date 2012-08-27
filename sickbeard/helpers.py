# Author: Nic Wolfe <nic@wolfeden.ca>
# URL: http://code.google.com/p/sickbeard/
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

import StringIO, zlib, gzip
import os
import stat
import urllib, urllib2
import re, socket
import shutil
import traceback
import time, sys

from httplib import BadStatusLine

from xml.dom.minidom import Node

import sickbeard

from sickbeard.exceptions import MultipleShowObjectsException, ex
from sickbeard import logger, classes
from sickbeard.common import USER_AGENT, mediaExtensions, XML_NSMAP

from sickbeard import db
from sickbeard import encodingKludge as ek

from lib.tvdb_api import tvdb_api, tvdb_exceptions

import xml.etree.cElementTree as etree

urllib._urlopener = classes.SickBeardURLopener()

def indentXML(elem, level=0):
    '''
    Does our pretty printing, makes Matt very happy
    '''
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indentXML(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        # Strip out the newlines from text
        if elem.text:
            elem.text = elem.text.replace('\n', ' ')
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

def replaceExtension(file, newExt):
    '''
    >>> replaceExtension('foo.avi', 'mkv')
    'foo.mkv'
    >>> replaceExtension('.vimrc', 'arglebargle')
    '.vimrc'
    >>> replaceExtension('a.b.c', 'd')
    'a.b.d'
    >>> replaceExtension('', 'a')
    ''
    >>> replaceExtension('foo.bar', '')
    'foo.'
    '''
    sepFile = file.rpartition(".")
    if sepFile[0] == "":
        return file
    else:
        return sepFile[0] + "." + newExt

def isMediaFile (file):
    # ignore samples
    if re.search('(^|[\W_])sample\d*[\W_]', file):
        return False

    # ignore MAC OS's retarded "resource fork" files
    if file.startswith('._'):
        return False

    sepFile = file.rpartition(".")
    if sepFile[2].lower() in mediaExtensions:
        return True
    else:
        return False

def sanitizeFileName (name):
    '''
    >>> sanitizeFileName('a/b/c')
    'a-b-c'
    >>> sanitizeFileName('abc')
    'abc'
    >>> sanitizeFileName('a"b')
    'ab'
    >>> sanitizeFileName('.a.b..')
    'a.b'
    '''
    
    # remove bad chars from the filename
    name = re.sub(r'[\\/\*]', '-', name)
    name = re.sub(r'[:"<>|?]', '', name)
    
    # remove leading/trailing periods and spaces
    name = name.strip(' .')
    
    return name


def getURL (url, headers=[]):
    """
    Returns a byte-string retrieved from the url provider.
    """

    opener = urllib2.build_opener()
    opener.addheaders = [('User-Agent', USER_AGENT), ('Accept-Encoding', 'gzip,deflate')]
    for cur_header in headers:
        opener.addheaders.append(cur_header)

    try:
        usock = opener.open(url)
        url = usock.geturl()
        encoding = usock.info().get("Content-Encoding")

        if encoding in ('gzip', 'x-gzip', 'deflate'):
            content = usock.read()
            if encoding == 'deflate':
                data = StringIO.StringIO(zlib.decompress(content))
            else:
                data = gzip.GzipFile('', 'rb', 9, StringIO.StringIO(content))
            result = data.read()

        else:
            result = usock.read()

        usock.close()

    except urllib2.HTTPError, e:
        logger.log(u"HTTP error " + str(e.code) + " while loading URL " + url, logger.WARNING)
        return None
    except urllib2.URLError, e:
        logger.log(u"URL error " + str(e.reason) + " while loading URL " + url, logger.WARNING)
        return None
    except BadStatusLine:
        logger.log(u"BadStatusLine error while loading URL " + url, logger.WARNING)
        return None
    except socket.timeout:
        logger.log(u"Timed out while loading URL " + url, logger.WARNING)
        return None
    except ValueError:
        logger.log(u"Unknown error while loading URL " + url, logger.WARNING)
        return None
    except Exception:
        logger.log(u"Unknown exception while loading URL " + url + ": " + traceback.format_exc(), logger.WARNING)
        return None

    return result

def findCertainShow (showList, tvdbid):
    results = filter(lambda x: x.tvdbid == tvdbid, showList)
    if len(results) == 0:
        return None
    elif len(results) > 1:
        raise MultipleShowObjectsException()
    else:
        return results[0]

def findCertainTVRageShow (showList, tvrid):

    if tvrid == 0:
        return None

    results = filter(lambda x: x.tvrid == tvrid, showList)

    if len(results) == 0:
        return None
    elif len(results) > 1:
        raise MultipleShowObjectsException()
    else:
        return results[0]


def makeDir (dir):
    if not ek.ek(os.path.isdir, dir):
        try:
            ek.ek(os.makedirs, dir)
        except OSError:
            return False
    return True

def makeShowNFO(showID, showDir):

    logger.log(u"Making NFO for show "+str(showID)+" in dir "+showDir, logger.DEBUG)

    if not makeDir(showDir):
        logger.log(u"Unable to create show dir, can't make NFO", logger.ERROR)
        return False

    showObj = findCertainShow(sickbeard.showList, showID)
    if not showObj:
        logger.log(u"This should never have happened, post a bug about this!", logger.ERROR)
        raise Exception("BAD STUFF HAPPENED")

    tvdb_lang = showObj.lang
    # There's gotta be a better way of doing this but we don't wanna
    # change the language value elsewhere
    ltvdb_api_parms = sickbeard.TVDB_API_PARMS.copy()

    if tvdb_lang and not tvdb_lang == 'en':
        ltvdb_api_parms['language'] = tvdb_lang

    t = tvdb_api.Tvdb(actors=True, **ltvdb_api_parms)

    try:
        myShow = t[int(showID)]
    except tvdb_exceptions.tvdb_shownotfound:
        logger.log(u"Unable to find show with id " + str(showID) + " on tvdb, skipping it", logger.ERROR)
        raise

    except tvdb_exceptions.tvdb_error:
        logger.log(u"TVDB is down, can't use its data to add this show", logger.ERROR)
        raise

    # check for title and id
    try:
        if myShow["seriesname"] == None or myShow["seriesname"] == "" or myShow["id"] == None or myShow["id"] == "":
            logger.log(u"Incomplete info for show with id " + str(showID) + " on tvdb, skipping it", logger.ERROR)

            return False
    except tvdb_exceptions.tvdb_attributenotfound:
        logger.log(u"Incomplete info for show with id " + str(showID) + " on tvdb, skipping it", logger.ERROR)

        return False

    tvNode = buildNFOXML(myShow)
    # Make it purdy
    indentXML( tvNode )
    nfo = etree.ElementTree( tvNode )

    logger.log(u"Writing NFO to "+os.path.join(showDir, "tvshow.nfo"), logger.DEBUG)
    nfo_filename = os.path.join(showDir, "tvshow.nfo").encode('utf-8')
    nfo_fh = open(nfo_filename, 'w')
    nfo.write( nfo_fh, encoding="utf-8" )

    return True

def buildNFOXML(myShow):
    '''
    Build an etree.Element of the root node of an NFO file with the
    data from `myShow`, a TVDB show object.

    >>> from collections import defaultdict
    >>> from xml.etree.cElementTree import tostring
    >>> show = defaultdict(lambda: None, _actors=[])
    >>> tostring(buildNFOXML(show))
    '<tvshow xsd="http://www.w3.org/2001/XMLSchema" xsi="http://www.w3.org/2001/XMLSchema-instance"><title /><rating /><plot /><episodeguide><url /></episodeguide><mpaa /><id /><genre /><premiered /><studio /></tvshow>'
    >>> show['seriesname'] = 'Peaches'
    >>> tostring(buildNFOXML(show))
    '<tvshow xsd="http://www.w3.org/2001/XMLSchema" xsi="http://www.w3.org/2001/XMLSchema-instance"><title>Peaches</title><rating /><plot /><episodeguide><url /></episodeguide><mpaa /><id /><genre /><premiered /><studio /></tvshow>'
    >>> show['contentrating'] = 'PG'
    >>> tostring(buildNFOXML(show))
    '<tvshow xsd="http://www.w3.org/2001/XMLSchema" xsi="http://www.w3.org/2001/XMLSchema-instance"><title>Peaches</title><rating /><plot /><episodeguide><url /></episodeguide><mpaa>PG</mpaa><id /><genre /><premiered /><studio /></tvshow>'
    >>> show['genre'] = 'Fruit|Edibles'
    >>> tostring(buildNFOXML(show))
    '<tvshow xsd="http://www.w3.org/2001/XMLSchema" xsi="http://www.w3.org/2001/XMLSchema-instance"><title>Peaches</title><rating /><plot /><episodeguide><url /></episodeguide><mpaa>PG</mpaa><id /><genre>Fruit / Edibles</genre><premiered /><studio /></tvshow>'
    '''
    tvNode = etree.Element( "tvshow" )
    for ns in XML_NSMAP.keys():
        tvNode.set(ns, XML_NSMAP[ns])

    title = etree.SubElement( tvNode, "title" )
    if myShow["seriesname"] != None:
        title.text = myShow["seriesname"]

    rating = etree.SubElement( tvNode, "rating" )
    if myShow["rating"] != None:
        rating.text = myShow["rating"]

    plot = etree.SubElement( tvNode, "plot" )
    if myShow["overview"] != None:
        plot.text = myShow["overview"]

    episodeguide = etree.SubElement( tvNode, "episodeguide" )
    episodeguideurl = etree.SubElement( episodeguide, "url" )
    if myShow["id"] != None:
        showurl = sickbeard.TVDB_BASE_URL + '/series/' + myShow["id"] + '/all/en.zip'
        episodeguideurl.text = showurl

    mpaa = etree.SubElement( tvNode, "mpaa" )
    if myShow["contentrating"] != None:
        mpaa.text = myShow["contentrating"]

    tvdbid = etree.SubElement( tvNode, "id" )
    if myShow["id"] != None:
        tvdbid.text = myShow["id"]

    genre = etree.SubElement( tvNode, "genre" )
    if myShow["genre"] != None:
        genre.text = " / ".join([x for x in myShow["genre"].split('|') if x != ''])

    premiered = etree.SubElement( tvNode, "premiered" )
    if myShow["firstaired"] != None:
        premiered.text = myShow["firstaired"]

    studio = etree.SubElement( tvNode, "studio" )
    if myShow["network"] != None:
        studio.text = myShow["network"]

    for actor in myShow['_actors']:

        cur_actor = etree.SubElement( tvNode, "actor" )

        cur_actor_name = etree.SubElement( cur_actor, "name" )
        cur_actor_name.text = actor['name']
        cur_actor_role = etree.SubElement( cur_actor, "role" )
        cur_actor_role_text = actor['role']

        if cur_actor_role_text != None:
            cur_actor_role.text = cur_actor_role_text

        cur_actor_thumb = etree.SubElement( cur_actor, "thumb" )
        cur_actor_thumb_text = actor['image']

        if cur_actor_thumb_text != None:
            cur_actor_thumb.text = cur_actor_thumb_text

    return tvNode


def searchDBForShow(regShowName):

    showNames = [re.sub('[. -]', ' ', regShowName)]

    myDB = db.DBConnection()

    yearRegex = "([^()]+?)\s*(\()?(\d{4})(?(2)\))$"

    for showName in showNames:

        sqlResults = myDB.select("SELECT * FROM tv_shows WHERE show_name LIKE ? OR tvr_name LIKE ?", [showName, showName])

        if len(sqlResults) == 1:
            return (int(sqlResults[0]["tvdb_id"]), sqlResults[0]["show_name"])

        else:

            # if we didn't get exactly one result then try again with the year stripped off if possible
            match = re.match(yearRegex, showName)
            if match and match.group(1):
                logger.log(u"Unable to match original name but trying to manually strip and specify show year", logger.DEBUG)
                sqlResults = myDB.select("SELECT * FROM tv_shows WHERE (show_name LIKE ? OR tvr_name LIKE ?) AND startyear = ?", [match.group(1)+'%', match.group(1)+'%', match.group(3)])

            if len(sqlResults) == 0:
                logger.log(u"Unable to match a record in the DB for "+showName, logger.DEBUG)
                continue
            elif len(sqlResults) > 1:
                logger.log(u"Multiple results for "+showName+" in the DB, unable to match show name", logger.DEBUG)
                continue
            else:
                return (int(sqlResults[0]["tvdb_id"]), sqlResults[0]["show_name"])


    return None

def sizeof_fmt(num):
    '''
    >>> sizeof_fmt(2)
    '2.0 bytes'
    >>> sizeof_fmt(1024)
    '1.0 KB'
    >>> sizeof_fmt(2048)
    '2.0 KB'
    >>> sizeof_fmt(2**20)
    '1.0 MB'
    >>> sizeof_fmt(1234567)
    '1.2 MB'
    '''
    for x in ['bytes','KB','MB','GB','TB']:
        if num < 1024.0:
            return "%3.1f %s" % (num, x)
        num /= 1024.0

def listMediaFiles(dir):

    if not dir or not ek.ek(os.path.isdir, dir):
        return []

    files = []
    for curFile in ek.ek(os.listdir, dir):
        fullCurFile = ek.ek(os.path.join, dir, curFile)

        # if it's a dir do it recursively
        if ek.ek(os.path.isdir, fullCurFile) and not curFile.startswith('.') and not curFile == 'Extras':
            files += listMediaFiles(fullCurFile)

        elif isMediaFile(curFile):
            files.append(fullCurFile)

    return files

def copyFile(srcFile, destFile):
    ek.ek(shutil.copyfile, srcFile, destFile)
    try:
        ek.ek(shutil.copymode, srcFile, destFile)
    except OSError:
        pass

def moveFile(srcFile, destFile):
    try:
        ek.ek(os.rename, srcFile, destFile)
        fixSetGroupID(destFile)
    except OSError:
        copyFile(srcFile, destFile)
        ek.ek(os.unlink, srcFile)

def make_dirs(path):
    """
    Creates any folders that are missing and assigns them the permissions of their
    parents
    """

    logger.log(u"Checking if the path " + path + " already exists", logger.DEBUG)

    if not ek.ek(os.path.isdir, path):
        # Windows, create all missing folders
        if os.name == 'nt' or os.name == 'ce':
            try:
                logger.log(u"Folder " + path + " didn't exist, creating it", logger.DEBUG)
                ek.ek(os.makedirs, path)
            except (OSError, IOError), e:
                logger.log(u"Failed creating " + path + " : " + ex(e), logger.ERROR)
                return False

        # not Windows, create all missing folders and set permissions
        else:
            sofar = ''
            folder_list = path.split(os.path.sep)

            # look through each subfolder and make sure they all exist
            for cur_folder in folder_list:
                sofar += cur_folder + os.path.sep;

                # if it exists then just keep walking down the line
                if ek.ek(os.path.isdir, sofar):
                    continue

                try:
                    logger.log(u"Folder " + sofar + " didn't exist, creating it", logger.DEBUG)
                    ek.ek(os.mkdir, sofar)
                    # use normpath to remove end separator, otherwise checks permissions against itself
                    chmodAsParent(ek.ek(os.path.normpath, sofar))
                except (OSError, IOError), e:
                    logger.log(u"Failed creating " + sofar + " : " + ex(e), logger.ERROR)
                    return False

    return True

def rename_ep_file(cur_path, new_path):
    """
    Creates all folders needed to move a file to its new location, renames it, then cleans up any folders
    left that are now empty.
    
    cur_path: The absolute path to the file you want to move/rename
    new_path: The absolute path to the destination for the file WITHOUT THE EXTENSION
    """
    
    logger.log(u"Renaming file from "+cur_path+" to "+new_path)
    
    new_dest_dir, new_dest_name = os.path.split(new_path) #@UnusedVariable
    cur_file_name, cur_file_ext = os.path.splitext(cur_path) #@UnusedVariable
    
    # put the extension on the incoming file
    new_path += cur_file_ext
    
    make_dirs(os.path.dirname(new_path))
    
    # move the file
    try:
        ek.ek(os.rename, cur_path, new_path)
    except (OSError, IOError), e:
        logger.log(u"Failed renaming " + cur_path + " to " + new_path + ": " + ex(e), logger.ERROR)
        return False
    
    # clean up any old folders that are empty
    delete_empty_folders(ek.ek(os.path.dirname, cur_path))
    
    return True
    

def delete_empty_folders(check_empty_dir):
    """
    Walks backwards up the path and deletes any empty folders found.
    
    check_empty_dir: The path to clean (absolute path to a folder)
    """
    
    logger.log(u"Trying to clean any empty folders under "+check_empty_dir)
    
    # as long as the folder exists and doesn't contain any files, delete it
    while os.path.isdir(check_empty_dir) and not os.listdir(check_empty_dir):
        logger.log(u"Deleting empty folder: "+check_empty_dir)
        try:
            os.rmdir(check_empty_dir)
        except (WindowsError, OSError), e:
            logger.log(u"Unable to delete "+check_empty_dir+": "+repr(e)+" / "+str(e), logger.WARNING)
            break
        check_empty_dir = os.path.dirname(check_empty_dir)


def chmodAsParent(childPath):
    if os.name == 'nt' or os.name == 'ce':
        return

    parentPath = ek.ek(os.path.dirname, childPath)
    
    if not parentPath:
        logger.log(u"No parent path provided in "+childPath+", unable to get permissions from it", logger.DEBUG)
        return
    
    parentMode = stat.S_IMODE(os.stat(parentPath)[stat.ST_MODE])
    
    childPathStat = ek.ek(os.stat, childPath)
    childPath_mode = stat.S_IMODE(childPathStat[stat.ST_MODE])

    if ek.ek(os.path.isfile, childPath):
        childMode = fileBitFilter(parentMode)
    else:
        childMode = parentMode

    if childPath_mode == childMode:
        return

    childPath_owner = childPathStat.st_uid
    user_id = os.geteuid()

    if user_id !=0 and user_id != childPath_owner:
        logger.log(u"Not running as root or owner of "+childPath+", not trying to set permissions", logger.DEBUG)
        return

    try:
        ek.ek(os.chmod, childPath, childMode)
        logger.log(u"Setting permissions for %s to %o as parent directory has %o" % (childPath, childMode, parentMode), logger.DEBUG)
    except OSError:
        logger.log(u"Failed to set permission for %s to %o" % (childPath, childMode), logger.ERROR)

def fileBitFilter(mode):
    for bit in [stat.S_IXUSR, stat.S_IXGRP, stat.S_IXOTH, stat.S_ISUID, stat.S_ISGID]:
        if mode & bit:
            mode -= bit

    return mode

def fixSetGroupID(childPath):
    if os.name == 'nt' or os.name == 'ce':
        return

    parentPath = ek.ek(os.path.dirname, childPath)
    parentStat = os.stat(parentPath)
    parentMode = stat.S_IMODE(parentStat[stat.ST_MODE])

    if parentMode & stat.S_ISGID:
        parentGID = parentStat[stat.ST_GID]
        childStat = ek.ek(os.stat, childPath)
        childGID = childStat[stat.ST_GID]

        if childGID == parentGID:
            return

        childPath_owner = childStat.st_uid
        user_id = os.geteuid()

        if user_id !=0 and user_id != childPath_owner:
            logger.log(u"Not running as root or owner of "+childPath+", not trying to set the set-group-ID", logger.DEBUG)
            return

        try:
            ek.ek(os.chown, childPath, -1, parentGID)  #@UndefinedVariable - only available on UNIX
            logger.log(u"Respecting the set-group-ID bit on the parent directory for %s" % (childPath), logger.DEBUG)
        except OSError:
            logger.log(u"Failed to respect the set-group-ID bit on the parent directory for %s (setting group ID %i)" % (childPath, parentGID), logger.ERROR)

def sanitizeSceneName (name, ezrss=False):
    """
    Takes a show name and returns the "scenified" version of it.
    
    ezrss: If true the scenified version will follow EZRSS's cracksmoker rules as best as possible
    
    Returns: A string containing the scene version of the show name given.
    """

    if not ezrss:
        bad_chars = u",:()'!?\u2019"
    # ezrss leaves : and ! in their show names as far as I can tell
    else:
        bad_chars = u",()'?\u2019"

    # strip out any bad chars
    for x in bad_chars:
        name = name.replace(x, "")

    # tidy up stuff that doesn't belong in scene names
    name = name.replace("- ", ".").replace(" ", ".").replace("&", "and").replace('/','.')
    name = re.sub("\.\.*", ".", name)

    if name.endswith('.'):
        name = name[:-1]

    return name

def create_https_certificates(ssl_cert, ssl_key):
    """
    Create self-signed HTTPS certificares and store in paths 'ssl_cert' and 'ssl_key'
    """
    try:
        from OpenSSL import crypto #@UnresolvedImport
        from lib.certgen import createKeyPair, createCertRequest, createCertificate, TYPE_RSA, serial #@UnresolvedImport
    except:
        logger.log(u"pyopenssl module missing, please install for https access", logger.WARNING)
        return False

    # Create the CA Certificate
    cakey = createKeyPair(TYPE_RSA, 1024)
    careq = createCertRequest(cakey, CN='Certificate Authority')
    cacert = createCertificate(careq, (careq, cakey), serial, (0, 60*60*24*365*10)) # ten years

    cname = 'SickBeard'
    pkey = createKeyPair(TYPE_RSA, 1024)
    req = createCertRequest(pkey, CN=cname)
    cert = createCertificate(req, (cacert, cakey), serial, (0, 60*60*24*365*10)) # ten years

    # Save the key and certificate to disk
    try:
        open(ssl_key, 'w').write(crypto.dump_privatekey(crypto.FILETYPE_PEM, pkey))
        open(ssl_cert, 'w').write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
    except:
        logger.log(u"Error creating SSL key and certificate", logger.ERROR)
        return False

    return True

if __name__ == '__main__':
    import doctest
    doctest.testmod()

def get_xml_text(node):
    text = ""
    for child_node in node.childNodes:
        if child_node.nodeType in (Node.CDATA_SECTION_NODE, Node.TEXT_NODE):
            text += child_node.data
    return text.strip()

def backupVersionedFile(oldFile, version):
    numTries = 0
    
    newFile = oldFile + '.' + 'v'+str(version)
    
    while not ek.ek(os.path.isfile, newFile):
        if not ek.ek(os.path.isfile, oldFile):
            break

        try:
            logger.log(u"Attempting to back up "+oldFile+" before migration...")
            shutil.copy(oldFile, newFile)
            logger.log(u"Done backup, proceeding with migration.")
            break
        except Exception, e:
            logger.log(u"Error while trying to back up "+oldFile+": "+ex(e))
            numTries += 1
            time.sleep(1)
            logger.log(u"Trying again.")

        if numTries >= 10:
            logger.log(u"Unable to back up "+oldFile+", please do it manually.")
            sys.exit(1)
