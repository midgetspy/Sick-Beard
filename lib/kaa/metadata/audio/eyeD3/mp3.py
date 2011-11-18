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
from binfuncs import *;
from utils import *;
from math import log10

#######################################################################
class Mp3Exception(Exception):
   '''Error reading mp3'''


#                   MPEG1  MPEG2  MPEG2.5
SAMPLE_FREQ_TABLE = ((44100, 22050, 11025),
                     (48000, 24000, 12000),
                     (32000, 16000, 8000),
                     (None,  None,  None));

#              V1/L1  V1/L2 V1/L3 V2/L1 V2/L2&L3 
BIT_RATE_TABLE = ((0,    0,    0,    0,    0),
                  (32,   32,   32,   32,   8),
                  (64,   48,   40,   48,   16),
                  (96,   56,   48,   56,   24),
                  (128,  64,   56,   64,   32),
                  (160,  80,   64,   80,   40),
                  (192,  96,   80,   96,   44),
                  (224,  112,  96,   112,  56),
                  (256,  128,  112,  128,  64),
                  (288,  160,  128,  144,  80),
                  (320,  192,  160,  160,  96),
                  (352,  224,  192,  176,  112),
                  (384,  256,  224,  192,  128),
                  (416,  320,  256,  224,  144),
                  (448,  384,  320,  256,  160),
                  (None, None, None, None, None));

#                             L1    L2    L3
TIME_PER_FRAME_TABLE = (None, 384, 1152, 1152);

# Emphasis constants
EMPHASIS_NONE = "None";
EMPHASIS_5015 = "50/15 ms";
EMPHASIS_CCIT = "CCIT J.17";

# Mode constants
MODE_STEREO              = "Stereo";
MODE_JOINT_STEREO        = "Joint stereo";
MODE_DUAL_CHANNEL_STEREO = "Dual channel stereo";
MODE_MONO                = "Mono";

# Xing flag bits
FRAMES_FLAG    = 0x0001
BYTES_FLAG     = 0x0002
TOC_FLAG       = 0x0004
VBR_SCALE_FLAG = 0x0008

#######################################################################
# Pass in a 4 byte integer to determine if it matches a valid mp3 frame
# header.
def is_valid_mp_header(header):
    # Test for the mp3 frame sync: 11 set bits.
    sync = (header >> 16)
    if sync & 0xFFE0 != 0xFFE0:
        # ffe0 is 11 sync bits, and supports identifying mpeg v2.5
        return False

    version = (header >> 19) & 0x3
    if version == 1:
        # This is a "reserved" version
        TRACE_MSG("invalid mpeg version")
        return False

    layer = (header >> 17) & 0x3
    if layer == 0:
        # This is a "reserved" layer
        TRACE_MSG("invalid mpeg layer")
        return False

    bitrate = (header >> 12) & 0xf
    if bitrate in (0, 0xf):
        # free and bad bitrate values
        TRACE_MSG("invalid mpeg bitrate")
        return False

    sample_rate = (header >> 10) & 0x3
    if sample_rate == 0x3:
        # this is a "reserved" sample rate
        TRACE_MSG("invalid mpeg sample rate")
        return False

    return True


# kaa.metadata addition: custom version of find_header which performs
# significantly better (and is more correct, handling the case in which
# the header spans a 64k boundary).
def find_header(fp, start_pos=0):
    import struct
    fp.seek(start_pos)
    data = carry = ''
    while True:
        # Offset start_pos with any data we've already processed.
        start_pos += len(data) - len(carry)
        data, carry = carry + fp.read(64*1024), ''
        if not data:
            break
        elif data == '\xff' * len(data):
            # Lame catch for a pathological edge case in which the data
            # is all 0xff.
            continue

        pos = -1
        while pos < len(data):
            pos = data.find('\xff', pos+1)
            if pos < 0:
                break
            elif pos+4 <= len(data):
                header_bytes = data[pos:pos+4]
                header = struct.unpack('!I', header_bytes)[0]
                if is_valid_mp_header(header):
                    return pos + start_pos, header, header_bytes
            else:
                # Carry over all remaining data starting at the '\xff' we just
                # found, in order to catch headers spanning a block boundary.
                carry = data[pos:]

    return None, None, None


def __EYED3_ORIG_find_header(fp, start_pos=0):
    def find_sync(fp, start_pos=0):
        CHUNK_SIZE = 65536

        fp.seek(start_pos)
        data = fp.read(CHUNK_SIZE)
        data_len = len(data)

        while data:
            sync_pos = data.find('\xff', 0)
            if sync_pos >= 0:
                header = data[sync_pos:sync_pos + 4]
                if len(header) == 4:
                    return (start_pos + sync_pos, header)
            data = fp.read(CHUNK_SIZE)
            data_len = len(data)
        return (None, None)
    sync_pos, header_bytes = find_sync(fp, start_pos)
    while sync_pos is not None:
        header = bytes2dec(header_bytes)
        if is_valid_mp_header(header):
            return (sync_pos, header, header_bytes)
        sync_pos, header_bytes = find_sync(fp, start_pos + sync_pos + 2)
    return (None, None, None)

def computeTimePerFrame(frameHeader):
   return (float(TIME_PER_FRAME_TABLE[frameHeader.layer]) /
           float(frameHeader.sampleFreq))

#######################################################################
class Header:
   def __init__(self, header_data=None):
       self.version = None
       self.layer = None
       self.errorProtection = None
       self.bitRate = None
       self.playTime = None
       self.sampleFreq = None
       self.padding = None
       self.privateBit = None
       self.copyright = None
       self.original = None
       self.emphasis = None
       self.mode = None
       # This value is left as is: 0<=modeExtension<=3.
       # See http://www.dv.co.yu/mpgscript/mpeghdr.htm for how to interpret
       self.modeExtension = None

       if header_data:
           self.decode(header_data)

   # This may throw an Mp3Exception if the header is malformed.
   def decode(self, header):
      if not is_valid_mp_header(header):
         raise Mp3Exception("Invalid MPEG header");

      # MPEG audio version from bits 19 and 20.
      version = (header >> 19) & 0x3
      self.version = [2.5, None, 2.0, 1.0][version]
      if self.version is None:
         raise Mp3Exception("Illegal MPEG version");

      # MPEG layer
      self.layer = 4 - ((header >> 17) & 0x3)
      if self.layer == 4:
         raise Mp3Exception("Illegal MPEG layer");

      # Decode some simple values.
      self.errorProtection = not (header >> 16) & 0x1;
      self.padding = (header >> 9) & 0x1;
      self.privateBit = (header >> 8) & 0x1;
      self.copyright = (header >> 3) & 0x1;
      self.original = (header >> 2) & 0x1;

      # Obtain sampling frequency.
      sampleBits = (header >> 10) & 0x3;
      if self.version == 2.5:
         freqCol = 2;
      else:
         freqCol = int(self.version - 1);
      self.sampleFreq = SAMPLE_FREQ_TABLE[sampleBits][freqCol];
      if not self.sampleFreq:
         raise Mp3Exception("Illegal MPEG sampling frequency");

      # Compute bitrate.
      bitRateIndex = (header >> 12) & 0xf;
      if int(self.version) == 1 and self.layer == 1:
         bitRateCol = 0;
      elif int(self.version) == 1 and self.layer == 2:
         bitRateCol = 1;
      elif int(self.version) == 1 and self.layer == 3:
         bitRateCol = 2;
      elif int(self.version) == 2 and self.layer == 1:
         bitRateCol = 3;
      elif int(self.version) == 2 and (self.layer == 2 or \
                                       self.layer == 3):
         bitRateCol = 4;
      else:
         raise Mp3Exception("Mp3 version %f and layer %d is an invalid "\
                            "combination" % (self.version, self.layer));
      self.bitRate = BIT_RATE_TABLE[bitRateIndex][bitRateCol];
      if self.bitRate == None:
         raise Mp3Exception("Invalid bit rate");
      # We know know the bit rate specified in this frame, but if the file
      # is VBR we need to obtain the average from the Xing header.
      # This is done by the caller since right now all we have is the frame
      # header.

      # Emphasis; whatever that means??
      emph = header & 0x3;
      if emph == 0:
         self.emphasis = EMPHASIS_NONE;
      elif emph == 1:
         self.emphasis = EMPHASIS_5015;
      elif emph == 2:
         self.emphasis = EMPHASIS_CCIT;
      elif strictID3():
         raise Mp3Exception("Illegal mp3 emphasis value: %d" % emph);

      # Channel mode.
      modeBits = (header >> 6) & 0x3;
      if modeBits == 0:
         self.mode = MODE_STEREO;
      elif modeBits == 1:
         self.mode = MODE_JOINT_STEREO;
      elif modeBits == 2:
         self.mode = MODE_DUAL_CHANNEL_STEREO;
      else:
         self.mode = MODE_MONO;
      self.modeExtension = (header >> 4) & 0x3;

      # Layer II has restrictions wrt to mode and bit rate.  This code
      # enforces them.
      if self.layer == 2:
         m = self.mode;
         br = self.bitRate;
         if (br == 32 or br == 48 or br == 56 or br == 80) and \
            (m != MODE_MONO):
            raise Mp3Exception("Invalid mode/bitrate combination for layer "\
                               "II");
         if (br == 224 or br == 256 or br == 320 or br == 384) and \
            (m == MODE_MONO):
            raise Mp3Exception("Invalid mode/bitrate combination for layer "\
                               "II");

      br = self.bitRate * 1000;
      sf = self.sampleFreq;
      p  = self.padding;
      if self.layer == 1:
         # Layer 1 uses 32 bit slots for padding.
         p  = self.padding * 4;
         self.frameLength = int((((12 * br) / sf) + p) * 4);
      else:
         # Layer 2 and 3 uses 8 bit slots for padding.
         p  = self.padding * 1;
         self.frameLength = int(((144 * br) / sf) + p);

      # Dump the state.
      TRACE_MSG("MPEG audio version: " + str(self.version));
      TRACE_MSG("MPEG audio layer: " + ("I" * self.layer));
      TRACE_MSG("MPEG sampling frequency: " + str(self.sampleFreq));
      TRACE_MSG("MPEG bit rate: " + str(self.bitRate));
      TRACE_MSG("MPEG channel mode: " + self.mode);
      TRACE_MSG("MPEG channel mode extension: " + str(self.modeExtension));
      TRACE_MSG("MPEG CRC error protection: " + str(self.errorProtection));
      TRACE_MSG("MPEG original: " + str(self.original));
      TRACE_MSG("MPEG copyright: " + str(self.copyright));
      TRACE_MSG("MPEG private bit: " + str(self.privateBit));
      TRACE_MSG("MPEG padding: " + str(self.padding));
      TRACE_MSG("MPEG emphasis: " + str(self.emphasis));
      TRACE_MSG("MPEG frame length: " + str(self.frameLength));

#######################################################################
class XingHeader:
   numFrames = int();
   numBytes = int();
   toc = [0] * 100;
   vbrScale = int();

   # Pass in the first mp3 frame from the file as a byte string.
   # If an Xing header is present in the file it'll be in the first mp3
   # frame.  This method returns true if the Xing header is found in the
   # frame, and false otherwise.
   def decode(self, frame):
      # mp3 version
      version = (ord(frame[1]) >> 3) & 0x1;
      # channel mode.
      mode = (ord(frame[3]) >> 6) & 0x3;

      # Find the start of the Xing header.
      if version:
         if mode != 3:
            pos = 32 + 4;
         else:
            pos = 17 + 4;
      else:
         if mode != 3:
            pos = 17 + 4;
         else:
            pos = 9 + 4;
      head = frame[pos:pos+4]
      self.vbr = (head == 'Xing') and True or False
      if head not in ['Xing', 'Info']:
          return 0
      TRACE_MSG("%s header detected @ %x" % (head, pos));
      pos += 4;

      # Read Xing flags.
      headFlags = bin2dec(bytes2bin(frame[pos:pos + 4]));
      pos += 4;
      TRACE_MSG("%s header flags: 0x%x" % (head, headFlags));

      # Read frames header flag and value if present
      if headFlags & FRAMES_FLAG:
         self.numFrames = bin2dec(bytes2bin(frame[pos:pos + 4]));
         pos += 4;
         TRACE_MSG("%s numFrames: %d" % (head, self.numFrames));

      # Read bytes header flag and value if present
      if headFlags & BYTES_FLAG:
         self.numBytes = bin2dec(bytes2bin(frame[pos:pos + 4]));
         pos += 4;
         TRACE_MSG("%s numBytes: %d" % (head, self.numBytes));

      # Read TOC header flag and value if present
      if headFlags & TOC_FLAG:
         i = 0;
         self.toc = frame[pos:pos + 100];
         pos += 100;
         TRACE_MSG("%s TOC (100 bytes): PRESENT" % head);
      else:
         TRACE_MSG("%s TOC (100 bytes): NOT PRESENT" % head);

      # Read vbr scale header flag and value if present
      if headFlags & VBR_SCALE_FLAG and head == 'Xing':
         self.vbrScale = bin2dec(bytes2bin(frame[pos:pos + 4]));
         pos += 4;
         TRACE_MSG("%s vbrScale: %d" % (head, self.vbrScale));

      return 1;

#######################################################################
class LameTag(dict):
   """Mp3 Info tag (AKA LAME Tag)

   Lame (and some other encoders) write a tag containing various bits of info
   about the options used at encode time.  If available, the following are
   parsed and stored in the LameTag dict:

   encoder_version: short encoder version [str]
   tag_revision:    revision number of the tag [int]
   vbr_method:      VBR method used for encoding [str]
   lowpass_filter:  lowpass filter frequency in Hz [int]
   replaygain:      if available, radio and audiofile gain (see below) [dict]
   encoding_flags:  encoding flags used [list]
   nogap:           location of gaps when --nogap was used [list]
   ath_type:        ATH type [int]
   bitrate:         bitrate and type (Constant, Target, Minimum) [tuple]
   encoder_delay:   samples added at the start of the mp3 [int]
   encoder_padding: samples added at the end of the mp3 [int]
   noise_shaping:   noise shaping method [int]
   stereo_mode:     stereo mode used [str]
   unwise_settings: whether unwise settings were used [boolean]
   sample_freq:     source sample frequency [str]
   mp3_gain:        mp3 gain adjustment (rarely used) [float]
   preset:          preset used [str]
   surround_info:   surround information [str]
   music_length:    length in bytes of original mp3 [int]
   music_crc:       CRC-16 of the mp3 music data [int]
   infotag_crc:     CRC-16 of the info tag [int]

   Prior to ~3.90, Lame simply stored the encoder version in the first frame.
   If the infotag_crc is invalid, then we try to read this version string.  A
   simple way to tell if the LAME Tag is complete is to check for the
   infotag_crc key.

   Replay Gain data is only available since Lame version 3.94b.  If set, the
   replaygain dict has the following structure:

      peak_amplitude: peak signal amplitude [float]
      radio:
         name:       name of the gain adjustment [str]
         adjustment: gain adjustment [float]
         originator: originator of the gain adjustment [str]
      audiofile: [same as radio]

   Note that as of 3.95.1, Lame uses 89dB as a reference level instead of the
   83dB that is specified in the Replay Gain spec.  This is not automatically
   compensated for.  You can do something like this if you want:

      import eyeD3
      af = eyeD3.Mp3AudioFile('/path/to/some.mp3')
      lamever = af.lameTag['encoder_version']
      name, ver = lamever[:4], lamever[4:]
      gain = af.lameTag['replaygain']['radio']['adjustment']
      if name == 'LAME' and eyeD3.mp3.lamevercmp(ver, '3.95') > 0:
          gain -= 6

   Radio and Audiofile Replay Gain are often referrered to as Track and Album
   gain, respectively.  See http://replaygain.hydrogenaudio.org/ for futher
   details on Replay Gain.

   See http://gabriel.mp3-tech.org/mp3infotag.html for the gory details of the
   LAME Tag.
   """

   # from the LAME source:
   # http://lame.cvs.sourceforge.net/*checkout*/lame/lame/libmp3lame/VbrTag.c
   _crc16_table = [
      0x0000, 0xC0C1, 0xC181, 0x0140, 0xC301, 0x03C0, 0x0280, 0xC241,
      0xC601, 0x06C0, 0x0780, 0xC741, 0x0500, 0xC5C1, 0xC481, 0x0440,
      0xCC01, 0x0CC0, 0x0D80, 0xCD41, 0x0F00, 0xCFC1, 0xCE81, 0x0E40,
      0x0A00, 0xCAC1, 0xCB81, 0x0B40, 0xC901, 0x09C0, 0x0880, 0xC841,
      0xD801, 0x18C0, 0x1980, 0xD941, 0x1B00, 0xDBC1, 0xDA81, 0x1A40,
      0x1E00, 0xDEC1, 0xDF81, 0x1F40, 0xDD01, 0x1DC0, 0x1C80, 0xDC41,
      0x1400, 0xD4C1, 0xD581, 0x1540, 0xD701, 0x17C0, 0x1680, 0xD641,
      0xD201, 0x12C0, 0x1380, 0xD341, 0x1100, 0xD1C1, 0xD081, 0x1040,
      0xF001, 0x30C0, 0x3180, 0xF141, 0x3300, 0xF3C1, 0xF281, 0x3240,
      0x3600, 0xF6C1, 0xF781, 0x3740, 0xF501, 0x35C0, 0x3480, 0xF441,
      0x3C00, 0xFCC1, 0xFD81, 0x3D40, 0xFF01, 0x3FC0, 0x3E80, 0xFE41,
      0xFA01, 0x3AC0, 0x3B80, 0xFB41, 0x3900, 0xF9C1, 0xF881, 0x3840,
      0x2800, 0xE8C1, 0xE981, 0x2940, 0xEB01, 0x2BC0, 0x2A80, 0xEA41,
      0xEE01, 0x2EC0, 0x2F80, 0xEF41, 0x2D00, 0xEDC1, 0xEC81, 0x2C40,
      0xE401, 0x24C0, 0x2580, 0xE541, 0x2700, 0xE7C1, 0xE681, 0x2640,
      0x2200, 0xE2C1, 0xE381, 0x2340, 0xE101, 0x21C0, 0x2080, 0xE041,
      0xA001, 0x60C0, 0x6180, 0xA141, 0x6300, 0xA3C1, 0xA281, 0x6240,
      0x6600, 0xA6C1, 0xA781, 0x6740, 0xA501, 0x65C0, 0x6480, 0xA441,
      0x6C00, 0xACC1, 0xAD81, 0x6D40, 0xAF01, 0x6FC0, 0x6E80, 0xAE41,
      0xAA01, 0x6AC0, 0x6B80, 0xAB41, 0x6900, 0xA9C1, 0xA881, 0x6840,
      0x7800, 0xB8C1, 0xB981, 0x7940, 0xBB01, 0x7BC0, 0x7A80, 0xBA41,
      0xBE01, 0x7EC0, 0x7F80, 0xBF41, 0x7D00, 0xBDC1, 0xBC81, 0x7C40,
      0xB401, 0x74C0, 0x7580, 0xB541, 0x7700, 0xB7C1, 0xB681, 0x7640,
      0x7200, 0xB2C1, 0xB381, 0x7340, 0xB101, 0x71C0, 0x7080, 0xB041,
      0x5000, 0x90C1, 0x9181, 0x5140, 0x9301, 0x53C0, 0x5280, 0x9241,
      0x9601, 0x56C0, 0x5780, 0x9741, 0x5500, 0x95C1, 0x9481, 0x5440,
      0x9C01, 0x5CC0, 0x5D80, 0x9D41, 0x5F00, 0x9FC1, 0x9E81, 0x5E40,
      0x5A00, 0x9AC1, 0x9B81, 0x5B40, 0x9901, 0x59C0, 0x5880, 0x9841,
      0x8801, 0x48C0, 0x4980, 0x8941, 0x4B00, 0x8BC1, 0x8A81, 0x4A40,
      0x4E00, 0x8EC1, 0x8F81, 0x4F40, 0x8D01, 0x4DC0, 0x4C80, 0x8C41,
      0x4400, 0x84C1, 0x8581, 0x4540, 0x8701, 0x47C0, 0x4680, 0x8641,
      0x8201, 0x42C0, 0x4380, 0x8341, 0x4100, 0x81C1, 0x8081, 0x4040]

   ENCODER_FLAGS = {
      'NSPSYTUNE'   : 0x0001,
      'NSSAFEJOINT' : 0x0002,
      'NOGAP_NEXT'  : 0x0004,
      'NOGAP_PREV'  : 0x0008,}

   PRESETS = {
      0:    'Unknown',
      # 8 to 320 are reserved for ABR bitrates
      410:  'V9',
      420:  'V8',
      430:  'V7',
      440:  'V6',
      450:  'V5',
      460:  'V4',
      470:  'V3',
      480:  'V2',
      490:  'V1',
      500:  'V0',
      1000: 'r3mix',
      1001: 'standard',
      1002: 'extreme',
      1003: 'insane',
      1004: 'standard/fast',
      1005: 'extreme/fast',
      1006: 'medium',
      1007: 'medium/fast',}

   REPLAYGAIN_NAME = {
      0: 'Not set',
      1: 'Radio',
      2: 'Audiofile',}

   REPLAYGAIN_ORIGINATOR = {
      0:   'Not set',
      1:   'Set by artist',
      2:   'Set by user',
      3:   'Set automatically',
      100: 'Set by simple RMS average',}

   SAMPLE_FREQUENCIES = {
      0: '<= 32 kHz',
      1: '44.1 kHz',
      2: '48 kHz',
      3: '> 48 kHz',}

   STEREO_MODES = {
      0: 'Mono',
      1: 'Stereo',
      2: 'Dual',
      3: 'Joint',
      4: 'Force',
      5: 'Auto',
      6: 'Intensity',
      7: 'Undefined',}

   SURROUND_INFO = {
      0: 'None',
      1: 'DPL encoding',
      2: 'DPL2 encoding',
      3: 'Ambisonic encoding',
      8: 'Reserved',}

   VBR_METHODS = {
      0:  'Unknown',
      1:  'Constant Bitrate',
      2:  'Average Bitrate',
      3:  'Variable Bitrate method1 (old/rh)',
      4:  'Variable Bitrate method2 (mtrh)',
      5:  'Variable Bitrate method3 (mt)',
      6:  'Variable Bitrate method4',
      8:  'Constant Bitrate (2 pass)',
      9:  'Average Bitrate (2 pass)',
      15: 'Reserved',}

   def __init__(self, frame):
      """Read the LAME info tag.

      frame should be the first frame of an mp3.
      """
      self.decode(frame)

   def _crc16(self, data, val = 0):
      """Compute a CRC-16 checksum on a data stream."""
      for c in data:
         val = self._crc16_table[ord(c) ^ (val & 0xff)] ^ (val >> 8)
      return val

   def decode(self, frame):
      """Decode the LAME info tag."""
      try: pos = frame.index("LAME")
      except (ValueError, AttributeError): return

      # check the info tag crc.  if it's not valid, no point parsing much more.
      lamecrc = bin2dec(bytes2bin(frame[190:192]))
      if self._crc16(frame[:190]) != lamecrc:
         #TRACE_MSG('Lame tag CRC check failed')
         # read version string from the first 30 bytes, up to any
         # non-ascii chars, then strip padding chars.
         #
         # XXX (How many bytes is proper to read?  madplay reads 20, but I've
         # got files with longer version strings)
         lamever = []
         for c in frame[pos:pos + 30]:
            if ord(c) not in range(32, 127):
               break
            lamever.append(c)
         self['encoder_version'] = ''.join(lamever).rstrip('\x55')
         TRACE_MSG('Lame Encoder Version: %s' % self['encoder_version'])
         return

      TRACE_MSG('Lame info tag found at position %d' % pos)

      # Encoder short VersionString, 9 bytes
      self['encoder_version'] = lamever = frame[pos:pos + 9].rstrip()
      TRACE_MSG('Lame Encoder Version: %s' % self['encoder_version'])
      pos += 9

      # Info Tag revision + VBR method, 1 byte
      self['tag_revision'] = bin2dec(bytes2bin(frame[pos:pos + 1])[:5])
      vbr_method = bin2dec(bytes2bin(frame[pos:pos + 1])[5:])
      self['vbr_method'] = self.VBR_METHODS.get(vbr_method, 'Unknown')
      TRACE_MSG('Lame info tag version: %s' % self['tag_revision'])
      TRACE_MSG('Lame VBR method: %s' % self['vbr_method'])
      pos += 1

      # Lowpass filter value, 1 byte
      self['lowpass_filter'] = bin2dec(bytes2bin(frame[pos:pos + 1])) * 100
      TRACE_MSG('Lame Lowpass filter value: %s Hz' % self['lowpass_filter'])
      pos += 1

      # Replay Gain, 8 bytes total
      replaygain = {}

      # Peak signal amplitude, 4 bytes
      peak = bin2dec(bytes2bin(frame[pos:pos + 4])) << 5
      if peak > 0:
         peak /= float(1 << 28)
         db = 20 * log10(peak)
         replaygain['peak_amplitude'] = peak
         TRACE_MSG('Lame Peak signal amplitude: %.8f (%+.1f dB)' % (peak, db))
      pos += 4

      # Radio and Audiofile Gain, AKA track and album, 2 bytes each
      for gaintype in ['radio', 'audiofile']:
         name = bin2dec(bytes2bin(frame[pos:pos + 2])[:3])
         orig = bin2dec(bytes2bin(frame[pos:pos + 2])[3:6])
         sign = bin2dec(bytes2bin(frame[pos:pos + 2])[6:7])
         adj  = bin2dec(bytes2bin(frame[pos:pos + 2])[7:]) / 10.0
         if sign:
            adj *= -1
         # XXX Lame 3.95.1 and above use 89dB as a reference instead of 83dB
         # as defined by the Replay Gain spec.  Should this be compensated for?
         #if lamever[:4] == 'LAME' and lamevercmp(lamever[4:], '3.95') > 0:
         #   adj -= 6
         if orig:
            name = self.REPLAYGAIN_NAME.get(name, 'Unknown')
            orig = self.REPLAYGAIN_ORIGINATOR.get(orig, 'Unknown')
            replaygain[gaintype] = {'name': name, 'adjustment': adj,
                                    'originator': orig}
            TRACE_MSG('Lame %s Replay Gain: %s dB (%s)' % (name, adj, orig))
         pos += 2
      if replaygain:
         self['replaygain'] = replaygain

      # Encoding flags + ATH Type, 1 byte
      encflags = bin2dec(bytes2bin(frame[pos:pos + 1])[:4])
      self['encoding_flags'], self['nogap'] = self._parse_encflags(encflags)
      self['ath_type'] = bin2dec(bytes2bin(frame[pos:pos + 1])[4:])
      TRACE_MSG('Lame Encoding flags: %s' % ' '.join(self['encoding_flags']))
      if self['nogap']:
         TRACE_MSG('Lame No gap: %s' % ' and '.join(self['nogap']))
      TRACE_MSG('Lame ATH type: %s' % self['ath_type'])
      pos += 1

      # if ABR {specified bitrate} else {minimal bitrate}, 1 byte
      btype = 'Constant'
      if 'Average' in self['vbr_method']:
         btype = 'Target'
      elif 'Variable' in self['vbr_method']:
         btype = 'Minimum'
      # bitrate may be modified below after preset is read
      self['bitrate'] = (bin2dec(bytes2bin(frame[pos:pos + 1])), btype)
      TRACE_MSG('Lame Bitrate (%s): %s' % (btype, self['bitrate'][0]))
      pos += 1

      # Encoder delays, 3 bytes
      self['encoder_delay'] = bin2dec(bytes2bin(frame[pos:pos + 3])[:12])
      self['encoder_padding'] = bin2dec(bytes2bin(frame[pos:pos + 3])[12:])
      TRACE_MSG('Lame Encoder delay: %s samples' % self['encoder_delay'])
      TRACE_MSG('Lame Encoder padding: %s samples' % self['encoder_padding'])
      pos += 3

      # Misc, 1 byte
      sample_freq = bin2dec(bytes2bin(frame[pos:pos + 1])[:2])
      unwise_settings = bin2dec(bytes2bin(frame[pos:pos + 1])[2:3])
      stereo_mode = bin2dec(bytes2bin(frame[pos:pos + 1])[3:6])
      self['noise_shaping'] = bin2dec(bytes2bin(frame[pos:pos + 1])[6:])
      self['sample_freq'] = self.SAMPLE_FREQUENCIES.get(sample_freq, 'Unknown')
      self['unwise_settings'] = bool(unwise_settings)
      self['stereo_mode'] = self.STEREO_MODES.get(stereo_mode, 'Unknown')
      TRACE_MSG('Lame Source Sample Frequency: %s' % self['sample_freq'])
      TRACE_MSG('Lame Unwise settings used: %s' % self['unwise_settings'])
      TRACE_MSG('Lame Stereo mode: %s' % self['stereo_mode'])
      TRACE_MSG('Lame Noise Shaping: %s' % self['noise_shaping'])
      pos += 1

      # MP3 Gain, 1 byte
      sign = bytes2bin(frame[pos:pos + 1])[0]
      gain = bin2dec(bytes2bin(frame[pos:pos + 1])[1:])
      if sign:
         gain *= -1
      self['mp3_gain'] = gain
      db = gain * 1.5
      TRACE_MSG('Lame MP3 Gain: %s (%+.1f dB)' % (self['mp3_gain'], db))
      pos += 1

      # Preset and surround info, 2 bytes
      surround = bin2dec(bytes2bin(frame[pos:pos + 2])[2:5])
      preset = bin2dec(bytes2bin(frame[pos:pos + 2])[5:])
      if preset in range(8, 321):
         if self['bitrate'] >= 255:
            # the value from preset is better in this case
            self['bitrate'] = (preset, btype)
            TRACE_MSG('Lame Bitrate (%s): %s' % (btype, self['bitrate'][0]))
         if 'Average' in self['vbr_method']:
            preset = 'ABR %s' % preset
         else:
            preset = 'CBR %s' % preset
      else:
         preset = self.PRESETS.get(preset, preset)
      self['surround_info'] = self.SURROUND_INFO.get(surround, surround)
      self['preset'] = preset
      TRACE_MSG('Lame Surround Info: %s' % self['surround_info'])
      TRACE_MSG('Lame Preset: %s' % self['preset'])
      pos += 2

      # MusicLength, 4 bytes
      self['music_length'] = bin2dec(bytes2bin(frame[pos:pos + 4]))
      TRACE_MSG('Lame Music Length: %s bytes' % self['music_length'])
      pos += 4

      # MusicCRC, 2 bytes
      self['music_crc'] = bin2dec(bytes2bin(frame[pos:pos + 2]))
      TRACE_MSG('Lame Music CRC: %04X' % self['music_crc'])
      pos += 2

      # CRC-16 of Info Tag, 2 bytes
      self['infotag_crc'] = lamecrc # we read this earlier
      TRACE_MSG('Lame Info Tag CRC: %04X' % self['infotag_crc'])
      pos += 2

   def _parse_encflags(self, flags):
      """Parse encoder flags.

      Returns a tuple containing lists of encoder flags and nogap data in
      human readable format.
      """

      encoder_flags, nogap = [], []

      if not flags:
         return encoder_flags, nogap

      if flags & self.ENCODER_FLAGS['NSPSYTUNE']:
         encoder_flags.append('--nspsytune')
      if flags & self.ENCODER_FLAGS['NSSAFEJOINT']:
         encoder_flags.append('--nssafejoint')

      NEXT = self.ENCODER_FLAGS['NOGAP_NEXT']
      PREV = self.ENCODER_FLAGS['NOGAP_PREV']
      if flags & (NEXT | PREV):
         encoder_flags.append('--nogap')
         if flags & PREV:
            nogap.append('before')
         if flags & NEXT:
            nogap.append('after')
      return encoder_flags, nogap

def lamevercmp(x, y):
   """Compare LAME version strings.

   alpha and beta versions are considered older.
   versions with sub minor parts or end with 'r' are considered newer.

   Return negative if x<y, zero if x==y, positive if x>y.
   """

   x = x.ljust(5)
   y = y.ljust(5)
   if x[:5] == y[:5]: return 0
   ret = cmp(x[:4], y[:4])
   if ret: return ret
   xmaj, xmin = x.split('.')[:2]
   ymaj, ymin = y.split('.')[:2]
   minparts = ['.']
   # lame 3.96.1 added the use of r in the very short version for post releases
   if (xmaj == '3' and xmin >= '96') or (ymaj == '3' and ymin >= '96'):
      minparts.append('r')
   if x[4] in minparts: return 1
   if y[4] in minparts: return -1
   if x[4] == ' ': return 1
   if y[4] == ' ': return -1
   return cmp(x[4], y[4])
