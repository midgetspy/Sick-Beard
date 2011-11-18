################################################################################
#  Copyright (C) 2002-2005,2007  Travis Shirk <travis@pobox.com>
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
################################################################################

eyeD3Version = "0.6.14";
eyeD3Maintainer = "Travis Shirk <travis@pobox.com>";

# Version constants
ID3_CURRENT_VERSION = 0x00; # The version of the linked tag, if any.
ID3_V1              = 0x10;
ID3_V1_0            = 0x11;
ID3_V1_1            = 0x12;
ID3_V2              = 0x20;
ID3_V2_2            = 0x21;
ID3_V2_3            = 0x22;
ID3_V2_4            = 0x24;
#ID3_V2_5            = 0x28; # This does not seem imminent.
ID3_DEFAULT_VERSION = ID3_V2_4;
ID3_ANY_VERSION     = ID3_V1 | ID3_V2;

import locale;
LOCAL_ENCODING = locale.getpreferredencoding(do_setlocale=False);
if not LOCAL_ENCODING or LOCAL_ENCODING == "ANSI_X3.4-1968":
    LOCAL_ENCODING = 'latin1';

import frames;
import mp3;
import tag;
from tag import *;
import utils;
