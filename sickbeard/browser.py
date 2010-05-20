import os
import glob
import string
import cherrypy

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
	assert os.name == 'nt'

	drives = []
	bitmask = windll.kernel32.GetLogicalDrives()
	for letter in string.uppercase:
		if bitmask & 1:
			drives.append(letter)
		bitmask >>= 1

	return drives

# Returns a list of dictionaries with the folders contained at the given path
# Give the empty string as the path to list the contents of the root path
# (under Unix this means "/", on Windows this will be a list of drive letters)
def foldersAtPath(path, includeParent = False):
	assert os.path.isabs(path) or path == ""

	if path == "":
		if os.name == 'nt':
			entries = []
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

	fileList = [{ 'name': filename, 'path': os.path.join(path, filename) } for filename in os.listdir(path)]
	fileList = filter(lambda entry: os.path.isdir(entry['path']), fileList)
	fileList = sorted(fileList, lambda x, y: cmp(os.path.basename(x['name']).lower(), os.path.basename(y['path']).lower()))

	entries = []
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
    def complete(self, q, limit=10, timestamp=None):
        cherrypy.response.headers['Content-Type'] = "text/plain"
        paths = [entry['path'] for entry in foldersAtPath(os.path.dirname(q))]
        return "\n".join(paths[0:int(limit)])
