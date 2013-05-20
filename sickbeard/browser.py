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
#  GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.

import os
import string
import cherrypy

from sickbeard import encodingKludge as ek

# use the built-in if it's available (python 2.6), if not use the included library
try:
    import json
except ImportError:
    from lib import simplejson as json

# this is for the drive letter code, it only works on windows
if os.name == 'nt':
    from ctypes import windll

# adapted from http://stackoverflow.com/questions/827371/is-there-a-way-to-list-all-the-available-drive-letters-in-python/827490
def getWinDrives():
    """ Return list of detected drives """
    assert os.name == 'nt'

    drives = []
    bitmask = windll.kernel32.GetLogicalDrives() #@UndefinedVariable
    for letter in string.uppercase:
        if bitmask & 1:
            drives.append(letter)
        bitmask >>= 1

    return drives


def foldersAtPath(path, includeParent=False):
    """ Returns a list of dictionaries with the folders contained at the given path
        Give the empty string as the path to list the contents of the root path
        under Unix this means "/", on Windows this will be a list of drive letters)
    """

    # walk up the tree until we find a valid path
    while path and not os.path.isdir(path):
        if path == os.path.dirname(path):
            path = ''
            break
        else:
            path = os.path.dirname(path)

    if path == "":
        if os.name == 'nt':
            entries = [{'current_path': 'Root'}]
            for letter in getWinDrives():
                letterPath = letter + ':\\'
                entries.append({'name': letterPath, 'path': letterPath})
            return entries
        else:
            path = '/'

    # fix up the path and find the parent
    path = os.path.abspath(os.path.normpath(path))
    parentPath = os.path.dirname(path)

    # if we're at the root then the next step is the meta-node showing our drive letters
    if path == parentPath and os.name == 'nt':
        parentPath = ""

    fileList = [{ 'name': filename, 'path': ek.ek(os.path.join, path, filename) } for filename in ek.ek(os.listdir, path)]
    fileList = filter(lambda entry: ek.ek(os.path.isdir, entry['path']), fileList)

    # prune out directories to proect the user from doing stupid things (already lower case the dir to reduce calls)
    hideList = ["boot", "bootmgr", "cache", "msocache", "recovery", "$recycle.bin", "recycler", "system volume information", "temporary internet files"] # windows specific
    hideList += [".fseventd", ".spotlight", ".trashes", ".vol", "cachedmessages", "caches", "trash"] # osx specific
    fileList = filter(lambda entry: entry['name'].lower() not in hideList, fileList)

    fileList = sorted(fileList, lambda x, y: cmp(os.path.basename(x['name']).lower(), os.path.basename(y['path']).lower()))

    entries = [{'current_path': path}]
    if includeParent and parentPath != path:
        entries.append({ 'name': "..", 'path': parentPath })
    entries.extend(fileList)

    return entries


class WebFileBrowser:

    @cherrypy.expose
    def index(self, path=''):
        cherrypy.response.headers['Content-Type'] = "application/json"
        return json.dumps(foldersAtPath(path, True))

    @cherrypy.expose
    def complete(self, term):
        cherrypy.response.headers['Content-Type'] = "application/json"
        paths = [entry['path'] for entry in foldersAtPath(os.path.dirname(term)) if 'path' in entry]
        return json.dumps( paths )
