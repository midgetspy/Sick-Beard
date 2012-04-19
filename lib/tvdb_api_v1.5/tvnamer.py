#!/usr/bin/env python
#encoding:utf-8
#author:dbr/Ben
#project:tvdb_api
#repository:http://github.com/dbr/tvdb_api
#license:Creative Commons GNU GPL v2
# (http://creativecommons.org/licenses/GPL/2.0/)

"""
tvnamer.py
Automatic TV episode namer.
Uses data from www.thetvdb.com via tvdb_api
"""

__author__ = "dbr/Ben"
__version__ = "1.1"

import os, sys, re
from optparse import OptionParser

from tvdb_api import (tvdb_error, tvdb_shownotfound, tvdb_seasonnotfound,
	tvdb_episodenotfound, tvdb_episodenotfound, tvdb_attributenotfound, tvdb_userabort)
from tvdb_api import Tvdb

config = {}

### Start user config

# The format of the renamed files (with and without episode names)
config['with_ep_name'] = '%(seriesname)s - [%(seasno)02dx%(epno)02d] - %(epname)s.%(ext)s'
config['without_ep_name'] = '%(seriesname)s - [%(seasno)02dx%(epno)02d].%(ext)s'

# Whitelist of valid filename characters
config['valid_filename_chars'] = """0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!@£$%^&*()_+=-[]{}"'.,<>`~? """

# Force the stripping of invalid Windows characters, even if the current 
# platform is not detected as Windows
config['force_windows_compliant_filenames'] = False

### End user config

if sys.platform == "win32" or config['force_windows_compliant_filenames']:
	# " * : < > ? | \ are all invalid on Windows
	config['valid_filename_chars'] = "".join([x for x in config['valid_filename_chars'] if x not in "\"*:<>?|\\"])


# Regex's to parse filenames with. Each one is a tuple containing a filename parsing
# regex and an episode splitting regex. The filename parsing regex must have 3 groups:
# seriesname, season number and episode numbers. The episode numbers should be splittable
# by the second regex. Use (?: optional) non-capturing groups if you need others.
config['name_parse_multi_ep'] = [
	# foo_[s01]_[e01]_[e02]
	(re.compile('''^(.+?)[ \._\-]\[[Ss](\d+)\]((?:_\[[Ee]\d+\])+)[^\\/]*$'''),
	 re.compile('''_\[[Ee](\d+)\]''')),
	# foo.1x09x10 or foo.1x09-10
	(re.compile('''^(.+?)[ \._\-]\[?([0-9]+)((?:[x-]\d+)+)[^\\/]*$'''),
	 re.compile('''[x-](\d+)''')),
	# foo.s01.e01.e02, foo.s01e01e02, foo.s01_e01_e02, etc
	(re.compile('''^(.+?)[ \._\-][Ss]([0-9]+)((?:[\.\-_ ]?[Ee]\d+)+)[^\\/]*$'''),
	 re.compile('''[\.\-_ ]?[Ee](\d+)''')),
    # foo.205 (single eps only)
    (re.compile('''^(.+)[ \._\-]([0-9]{1})([0-9]{2})[\._ -][^\\/]*$'''),
     re.compile("(\d{2})")),
    # foo.0205 (single eps only)
    (re.compile('''^(.+)[ \._\-]([0-9]{2})([0-9]{2,3})[\._ -][^\\/]*$'''),
     re.compile("(\d{2,3})"))
]



def findFiles(args, recursive=False, verbose=False):
	"""
	Takes a list of files/folders, grabs files inside them. Does not recurse
	more than one level (if a folder is supplied, it will list files within),
	unless recurse is True, in which case it will recursively find all files.
	"""
	allfiles = []
	for cfile in args:
		if os.path.isdir(cfile):
			for sf in os.listdir(cfile):
				newpath = os.path.join(cfile, sf)
				if os.path.isfile(newpath):
					allfiles.append(newpath)
				else:
					if recursive:
						if verbose:
							print "Recursively scanning %s" % (newpath)
						allfiles.extend(
							findFiles([newpath], recursive=recursive, verbose=verbose)
						)
					#end if recursive
				#end if isfile
			#end for sf
		elif os.path.isfile(cfile):
			allfiles.append(cfile)
		#end if isdir
	#end for cfile
	return allfiles
#end findFiles

def processSingleName(name, verbose=False):
	filepath, filename = os.path.split(name)
	filename, ext = os.path.splitext(filename)

	# Remove leading . from extension
	ext = ext.replace(".", "", 1)

	for r in config['name_parse_multi_ep']:
		match = r[0].match(filename)
		if match:

			seriesname, seasno, eps = match.groups()
	
			#remove ._- characters from name (- removed only if next to end of line)
			seriesname = re.sub("[\._]|\-(?=$)", " ", seriesname).strip()
	
			allEps = re.findall(r[1], eps)
	
			return{'file_seriesname':seriesname,
				'seasno':int(seasno),
				'epno':[int(x) for x in allEps],
				'filepath':filepath,
				'filename':filename,
				'ext':ext
			}
	else:
		#print "Invalid name: %s" % (name)
		return None
	#end for r

def processNames(names, verbose=False):
	"""
	Takes list of names, runs them though the config['name_parse'] regexs
	"""
	allEps = []
	for f in names:
		cur = processSingleName(f, verbose=verbose)
		if cur is not None:
			allEps.append(cur)
	return allEps
#end processNames

def formatName(cfile):
	"""
	Takes a file dict and renames files using the configured format
	"""
	if cfile['epname']:
		n = config['with_ep_name'] % (cfile)
	else:
		n = config['without_ep_name'] % (cfile)
	#end if epname
	return n
#end formatName

def cleanName(name):
	"""
	Cleans the supplied filename for renaming-to
	"""
	name = name.encode('ascii', 'ignore') # convert unicode to ASCII

	return ''.join([c for c in name if c in config['valid_filename_chars']])
#end cleanName

def renameFile(oldfile, newfile, force=False):
	"""
	Renames files, does not overwrite files unless forced
	"""
	new_exists = os.access(newfile, os.F_OK)
	if new_exists:
		sys.stderr.write("New filename already exists.. ")
		if force:
			sys.stderr.write("overwriting\n")
			os.rename(oldfile, newfile)
		else:
			sys.stderr.write("skipping\n")
			return False
		#end if force
	else:
		os.rename(oldfile, newfile)
		return True
	#end if new_exists

def processFile(t, opts, cfile):
	try:
		# Ask for episode name from tvdb_api
		epname = t[ cfile['file_seriesname'] ][ cfile['seasno'] ][ cfile['epno'] ]['episodename']
	except tvdb_shownotfound:
		# No such show found.
		# Use the show-name from the files name, and None as the ep name
		sys.stderr.write("! Warning: Show \"%s\" not found (for file %s.%s)\n" % (
			cfile['file_seriesname'],
			cfile['filename'],
			cfile['ext'])
		)

		cfile['seriesname'] = cfile['file_seriesname']
		cfile['epname'] = None
	except (tvdb_seasonnotfound, tvdb_episodenotfound, tvdb_attributenotfound):
		# The season, episode or name wasn't found, but the show was.
		# Use the corrected show-name, but no episode name.
		sys.stderr.write("! Warning: Episode name not found for %s (in %s)\n" % (
			cfile['file_seriesname'],
			cfile['filepath'])
		)

		cfile['seriesname'] = t[ cfile['file_seriesname'] ]['seriesname']
		cfile['epname'] = None
	except tvdb_error, errormsg:
		# Error communicating with thetvdb.com
		sys.stderr.write(
			"! Warning: Error contacting www.thetvdb.com:\n%s\n" % (errormsg)
		)

		cfile['seriesname'] = cfile['file_seriesname']
		cfile['epname'] = None
	except tvdb_userabort, errormsg:
		# User aborted selection (q or ^c)
		print "\n", errormsg
		sys.exit(1)
	else:
		cfile['epname'] = epname
		cfile['seriesname'] = t[ cfile['file_seriesname'] ]['seriesname'] # get the corrected seriesname

	# Format new filename, strip unwanted characters
	newname = formatName(cfile)
	newname = cleanName(newname)

	# Append new filename (with extension) to path
	oldfile = os.path.join(
		cfile['filepath'],
		cfile['filename'] + "." + cfile['ext']
	)
	# Join path to new file name
	newfile = os.path.join(
		cfile['filepath'],
		newname
	)

	# Show new/old filename
	print "#" * 20
	print "Old name: %s" % (cfile['filename'] + "." + cfile['ext'])
	print "New name: %s" % (newname)

	# Either always rename, or prompt user
	if opts.always or (not opts.interactive):
		rename_result = renameFile(oldfile, newfile, force=opts.force)
		if rename_result:
			print "..auto-renaming"
		else:
			print "..not renamed"
		#end if rename_result

		return # next filename!
	#end if always

	ans = None
	while ans not in ['y', 'n', 'a', 'q', '']:
		print "Rename?"
		print "([y]/n/a/q)",
		try:
			ans = raw_input().strip()
		except KeyboardInterrupt, errormsg:
			print "\n", errormsg
			sys.exit(1)
		#end try
	#end while

	if len(ans) == 0:
		print "Renaming (default)"
		rename_result = renameFile(oldfile, newfile, force=opts.force)
	elif ans[0] == "a":
		opts.always = True
		rename_result = renameFile(oldfile, newfile, force=opts.force)
	elif ans[0] == "q":
		print "Aborting"
		sys.exit(1)
	elif ans[0] == "y":
		rename_result = renameFile(oldfile, newfile, force=opts.force)
	elif ans[0] == "n":
		print "Skipping"
		return
	else:
		print "Invalid input, skipping"
	#end if ans
	if rename_result:
		print "..renamed"
	else:
		print "..not renamed"
	#end if rename_result
#end processFile

def main():
	parser = OptionParser(usage="%prog [options] <file or directories>")

	parser.add_option("-d", "--debug", action="store_true", default=False, dest="debug",
						help="show debugging info")
	parser.add_option("-b", "--batch", action="store_false", dest="interactive",
						help="selects first search result, requires no human intervention once launched", default=False)
	parser.add_option("-i", "--interactive", action="store_true", dest="interactive", default=True,
						help="interactivly select correct show from search results [default]")
	parser.add_option("-s", "--selectfirst", action="store_true", dest="selectfirst", default=False,
						help="automatically select first series search result (instead of showing the select-series interface)")
	parser.add_option("-r", "--recursive", action="store_true", dest="recursive", default=True,
						help="recursivly search supplied directories for files to rename")
	parser.add_option("-a", "--always", action="store_true", default=False, dest="always",
						help="always renames files (but still lets user select correct show). Can be changed during runtime with the 'a' prompt-option")
	parser.add_option("-f", "--force", action="store_true", default=False, dest="force",
						help="forces file to be renamed, even if it will overwrite an existing file")

	opts, args = parser.parse_args()

	if len(args) == 0:
		parser.error("No filenames or directories supplied")
	#end if len(args)

	allFiles = findFiles(args, opts.recursive, verbose=opts.debug)
	validFiles = processNames(allFiles, verbose=opts.debug)

	if len(validFiles) == 0:
		sys.stderr.write("No valid files found\n")
		sys.exit(2)

	print "#" * 20
	print "# Starting tvnamer"
	print "# Processing %d files" % (len(validFiles))

	t = Tvdb(debug=opts.debug, interactive=opts.interactive, select_first=opts.selectfirst)

	print "# ..got tvdb mirrors"
	print "# Starting to process files"
	print "#" * 20

	for cfile in validFiles:
		print "# Processing %(file_seriesname)s (season: %(seasno)d, episode %(epno)d)" % (cfile)
		processFile(t, opts, cfile)
	print "# Done"
#end main

if __name__ == "__main__":
	main()
