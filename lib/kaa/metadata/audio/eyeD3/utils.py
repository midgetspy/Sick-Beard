################################################################################
#  Copyright (C) 2003-2005  Travis Shirk <travis@pobox.com>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#  $Id: utils.py 3035 2008-02-06 12:54:48Z dmeyer $
################################################################################
from kaa.metadata.audio.eyeD3 import *;

def versionsToConstant(v):
   major = v[0];
   minor = v[1];
   rev = v[2];
   if major == 1:
      if minor == 0:
         return ID3_V1_0;
      elif minor == 1:
         return ID3_V1_1;
   elif major == 2:
      if minor == 2:
         return ID3_V2_2;
      if minor == 3:
         return ID3_V2_3;
      elif minor == 4:
         return ID3_V2_4;
   raise str("Invalid ID3 version: %s" % str(v));

def versionToString(v):
   if v & ID3_V1:
      if v == ID3_V1_0:
         return "v1.0";
      elif v == ID3_V1_1:
         return "v1.1";
      elif v == ID3_V1:
         return "v1.x";
   elif v & ID3_V2:
      if v == ID3_V2_2:
         return "v2.2";
      elif v == ID3_V2_3:
         return "v2.3";
      elif v == ID3_V2_4:
         return "v2.4";
      elif v == ID3_V2:
         return "v2.x";

   if v == ID3_ANY_VERSION:
      return "v1.x/v2.x";
   raise str("versionToString - Invalid ID3 version constant: %s" % hex(v));

def constantToVersions(v):
   if v & ID3_V1:
      if v == ID3_V1_0:
         return [1, 0, 0];
      elif v == ID3_V1_1:
         return [1, 1, 0];
      elif v == ID3_V1:
         return [1, 1, 0];
   elif v & ID3_V2:
      if v == ID3_V2_2:
         return [2, 2, 0];
      elif v == ID3_V2_3:
         return [2, 3, 0];
      elif v == ID3_V2_4:
         return [2, 4, 0];
      elif v == ID3_V2:
         return [2, 4, 0];
   raise str("constantToVersions - Invalid ID3 version constant: %s" % hex(v));

################################################################################
TRACE = 0;
prefix = "eyeD3 trace> ";
def TRACE_MSG(msg):
   if TRACE:
       try:
           print prefix + msg;
       except UnicodeEncodeError:
           pass;

STRICT_ID3 = 0;
def strictID3():
   return STRICT_ID3;
################################################################################

import os;

class FileHandler:
    R_CONT = 0;
    R_HALT = -1;

    # MUST return R_CONT or R_HALT
    def handleFile(self, f):
        pass

    # MUST for all files processed return 0 for success and a positive int
    # for error
    def handleDone(self):
        pass

class FileWalker:
    def __init__(self, handler, root, excludes = []):
        self._handler = handler;
        self._root = root;
        self._excludes = excludes;

    def go(self):
        for (root, dirs, files) in os.walk(self._root):
            for f in files:
                f = os.path.abspath(root + os.sep + f);
                if not self._isExcluded(f):
                    if self._handler.handleFile(f) == FileHandler.R_HALT:
                        return FileHandler.R_HALT;
        return self._handler.handleDone();

    def _isExcluded(self, path):
        for ex in self._excludes:
            match = re.compile(exd).search(path);
            if match and match.start() == 0:
                return 1;
        return 0;

################################################################################
# Time and memory string formatting
def format_track_time(curr, total=None):
    def time_tuple(ts):
        if ts is None or ts < 0:
            ts = 0
        hours = ts / 3600
        mins = (ts % 3600) / 60
        secs = (ts % 3600) % 60
        tstr = '%02d:%02d' % (mins, secs)
        if int(hours):
            tstr = '%02d:%s' % (hours, tstr)
        return (int(hours), int(mins), int(secs), tstr)

    hours, mins, secs, curr_str = time_tuple(curr)
    retval = curr_str
    if total:
        hours, mins, secs, total_str = time_tuple(total)
        retval += ' / %s' % total_str
    return retval

KB_BYTES = 1024
MB_BYTES = 1048576
GB_BYTES = 1073741824
KB_UNIT = 'KB'
MB_UNIT = 'MB'
GB_UNIT = 'GB'

def format_size(sz):
    unit = 'Bytes'
    if sz >= GB_BYTES:
        sz = float(sz) / float(GB_BYTES)
        unit = GB_UNIT
    elif sz >= MB_BYTES:
        sz = float(sz) / float(MB_BYTES)
        unit = MB_UNIT
    elif sz >= KB_BYTES:
        sz = float(sz) / float(KB_BYTES)
        unit = KB_UNIT
    return "%.2f %s" % (sz, unit)

def format_time_delta(td):
    days = td.days
    hours = td.seconds / 3600
    mins = (td.seconds % 3600) / 60
    secs = (td.seconds % 3600) % 60
    tstr = "%02d:%02d:%02d" % (hours, mins, secs)
    if days:
        tstr = "%d days %s" % (days, tstr)
    return tstr
