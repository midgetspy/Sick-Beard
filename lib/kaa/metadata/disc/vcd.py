# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# vcd.py - parse vcd track informations
# -----------------------------------------------------------------------------
# $Id: vcd.py 2971 2008-01-16 13:17:33Z dmeyer $
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

__all__ = ['Parser']

# kaa.metadata.disc imports
import core
import cdrom

class VCD(core.Disc):
    def __init__(self,device):
        core.Disc.__init__(self)
        self.offset = 0
        self.mime = 'video/vcd'
        self.type = 'CD'
        self.subtype = 'video'
        # parse disc
        self.parseDisc(device)


    def parseDisc(self, device):
        type = None
        if self.is_disc(device) != 2:
            raise core.ParseError()

        f = open(device)
        try:
            # read CD-XA001 at byte 1024 in sector 16
            f.seek(2048*16 + 1024, 0)
            if f.read(8) != 'CD-XA001':
                raise core.ParseError()
            # read VIDEO_CD at sector 150
            f.seek(2048*150, 0)
            typebuffer = f.read(8)
            if typebuffer != 'VIDEO_CD' and typebuffer != 'SUPERVCD':
                raise core.ParseError()
            # Read some bytes of the ISO9660 part to better guess VCD or SVCD.
            # Maybe this code is not needed and VIDEO_CD and SUPERVCD are enough.
            f.seek(2048*16, 0)
            iso9660 = f.read(2048*16)
            if typebuffer == 'VIDEO_CD' and iso9660.find('MPEGAV') > 0:
                type = 'VCD'
            elif typebuffer == 'SUPERVCD' and \
                 (iso9660.find('SVCD') > 0 or iso9660.find('MPEG2') > 0):
                type = 'SVCD'
            else:
                raise core.ParseError()
        finally:
            f.close()

        # read the tracks to generate the title list
        device = open(device)
        (first, last) = cdrom.audiocd_toc_header(device)

        lmin = 0
        lsec = 0

        num = 0
        for i in range(first, last + 2):
            if i == last + 1:
                min, sec, frames = cdrom.audiocd_leadout(device)
            else:
                min, sec, frames = cdrom.audiocd_toc_entry(device, i)
            if num:
                vi = core.VideoStream()
                # XXX add more static information here, it's also possible
                # XXX to scan for more informations like fps
                # XXX Settings to MPEG1/2 is a wild guess, maybe the track
                # XXX isn't playable at all (e.g. the menu)
                if type == 'VCD':
                    vi.codec = 'MPEG1'
                else:
                    vi.codec = 'MPEG2'
                vi.length = (min-lmin) * 60 + (sec-lsec)
                self.tracks.append(vi)
            num += 1
            lmin, lsec = min, sec
        device.close()


Parser = VCD
