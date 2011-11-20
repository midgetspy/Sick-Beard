# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# cdrom.py - cdrom access module
# -----------------------------------------------------------------------------
# $Id: cdrom.py 3647 2008-10-25 19:52:16Z hmeine $
#
# -----------------------------------------------------------------------------
# kaa-Metadata - Media Metadata for Python
# Copyright (C) 2003-2006 Thomas Schueppel, Dirk Meyer
#
# First Edition: Dirk Meyer <dischi@freevo.org>
# Maintainer:    Dirk Meyer <dischi@freevo.org>
#
# Please see the file AUTHORS for a complete list of authors.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MER-
# CHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
# Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#
# -----------------------------------------------------------------------------

# python imports
import os
import re
import time
import array
import md5
from struct import pack, unpack
import logging
from fcntl import ioctl

CREATE_MD5_ID = 0

# cdrom module
try:
    import _cdrom
except ImportError:
    _cdrom = None

# get logging object
log = logging.getLogger('metadata')


def audiocd_open(device=None, flags=None):
    # Allow this function to be called with no arguments,
    # specifying that we should call cdrom.open() with
    # no arguments.
    if device == None:
        return _cdrom.open()
    elif flags == None:
        return _cdrom.open(device)
    else:
        return _cdrom.open(device, flags)


def audiocd_id(device):
    (first, last) = _cdrom.toc_header(device)

    track_frames = []
    checksum = 0

    for i in range(first, last + 1):
        (min, sec, frame) = _cdrom.toc_entry(device, i)
        n = min*60 + sec
        while n > 0:
            checksum += n % 10
            n = n / 10
        track_frames.append(min*60*75 + sec*75 + frame)

    (min, sec, frame) = _cdrom.leadout(device)
    track_frames.append(min*60*75 + sec*75 + frame)
    total_time = (track_frames[-1] / 75) - (track_frames[0] / 75)
    discid = ((checksum % 0xff) << 24 | total_time << 8 | last)
    return [discid, last] + track_frames[:-1] + [ track_frames[-1] / 75 ]


def audiocd_toc_header(device):
    return _cdrom.toc_header(device)


def audiocd_toc_entry(device, track):
    return _cdrom.toc_entry(device, track)


def audiocd_leadout(device):
    return _cdrom.leadout(device)


def _drive_status(device, handle_mix = 0):
    """
    check the current disc in device
    return: no disc (0), audio cd (1), data cd (2), blank cd (3)
    """
    CDROM_DRIVE_STATUS=0x5326
    CDSL_CURRENT=( (int ) ( ~ 0 >> 1 ) )
    CDROM_DISC_STATUS=0x5327
    CDS_AUDIO=100
    CDS_MIXED=105
    CDS_DISC_OK=4
    CDS_NO_DISC=0

    # FreeBSD ioctls - there is no CDROM.py
    # XXX 0xc0086305 below creates a warning, but 0xc0086305L
    # doesn't work. Suppress that warning for Linux users,
    # until a better solution can be found.
    if os.uname()[0] == 'FreeBSD':
        CDIOREADTOCENTRYS = 0xc0086305L
        CD_MSF_FORMAT = 2

    fd = None
    try:
        fd = os.open(device, os.O_RDONLY | os.O_NONBLOCK)
        if os.uname()[0] == 'FreeBSD':
            try:
                cd_toc_entry = array.array('c', '\000'*4096)
                (address, length) = cd_toc_entry.buffer_info()
                buf = pack('BBHP', CD_MSF_FORMAT, 0, length, address)
                s = ioctl(fd, CDIOREADTOCENTRYS, buf)
                s = CDS_DISC_OK
            except (OSError, IOError):
                s = CDS_NO_DISC
        else:
            s = ioctl(fd, CDROM_DRIVE_STATUS, CDSL_CURRENT)
    except (OSError, IOError):
        log.error('ERROR: no permission to read %s' % device)
        log.error('Media detection not possible, set drive to \'empty\'')

        # maybe we need to close the fd if ioctl fails, maybe
        # open fails and there is no fd, maye we aren't running
        # linux and don't have ioctl
        try:
            if fd:
                os.close(fd)
        except (OSError, IOError):
            pass
        return 0

    if not s == CDS_DISC_OK:
        # no disc, error, whatever
        try:
            os.close(fd)
        except (OSError, IOError):
            pass
        return 0

    if os.uname()[0] == 'FreeBSD':
        s = 0
        # We already have the TOC from above
        for i in range(0, 4096, 8):
            control = unpack('B', cd_toc_entry[i+1])[0] & 4
            track = unpack('B', cd_toc_entry[i+2])[0]
            if track == 0:
                break
            if control == 0 and s != CDS_MIXED:
                s = CDS_AUDIO
            elif control != 0:
                if s == CDS_AUDIO:
                    s = CDS_MIXED
                else:
                    s = 100 + control # ugly, but encodes Linux ioctl returns
            elif control == 5:
                s = CDS_MIXED

    else:
        s = ioctl(fd, CDROM_DISC_STATUS)
    os.close(fd)

    if s == CDS_MIXED and handle_mix:
        return 4
    if s == CDS_AUDIO or s == CDS_MIXED:
        return 1

    try:
        fd = open(device, 'rb')
        # try to read from the disc to get information if the disc
        # is a rw medium not written yet

        fd.seek(32768) # 2048 multiple boundary for FreeBSD
        # FreeBSD doesn't return IOError unless we try and read:
        fd.read(1)
    except IOError:
        # not readable
        fd.close()
        return 3

    # disc ok
    fd.close()
    return 2


_id_cache = {}

def status(device, handle_mix=0):
    """
    return the disc id of the device or None if no disc is there
    """
    if not _cdrom:
        log.debug("kaa.metadata not compiled with CDROM support")
        return 0, None

    global _id_cache
    try:
        if _id_cache[device][0] + 0.9 > time.time():
            return _id_cache[device][1:]
    except (KeyError, IndexError):
        pass

    disc_type = _drive_status(device, handle_mix=handle_mix)
    if disc_type == 0 or disc_type == 3:
        return 0, None

    elif disc_type == 1 or disc_type == 4:
        # audio disc
        discfd = audiocd_open(device)
        id = audiocd_id(discfd)
        id = '%08lx_%d' % (id[0], id[1])
        discfd.close()
    else:
        f = open(device,'rb')

        if os.uname()[0] == 'FreeBSD':
            # FreeBSD can only seek to 2048 multiple boundaries.
            # Below works on Linux and FreeBSD:
            f.seek(32768)
            id = f.read(829)
            label = id[40:72]
            id = id[813:829]
        else:
            f.seek(0x0000832d)
            id = f.read(16)
            f.seek(32808, 0)
            label = f.read(32)

        if CREATE_MD5_ID:
            id_md5 = md5.new()
            id_md5.update(f.read(51200))
            id = id_md5.hexdigest()

        f.close()

        m = re.match("^(.*[^ ]) *$", label)
        if m:
            id = '%s%s' % (id, m.group(1))
        id = re.compile('[^a-zA-Z0-9()_-]').sub('_', id)


    _id_cache[device] = time.time(), disc_type, id
    id = id.replace('/','_')
    return disc_type, id
