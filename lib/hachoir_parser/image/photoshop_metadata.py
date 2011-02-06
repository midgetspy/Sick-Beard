from lib.hachoir_core.field import (FieldSet, ParserError,
    UInt8, UInt16, UInt32,
    String, CString, PascalString8,
    NullBytes, RawBytes)
from lib.hachoir_core.text_handler import textHandler, hexadecimal
from lib.hachoir_core.tools import alignValue, createDict
from lib.hachoir_parser.image.iptc import IPTC
from lib.hachoir_parser.common.win32 import PascalStringWin32

class Version(FieldSet):
    def createFields(self):
        yield UInt32(self, "version")
        yield UInt8(self, "has_realm")
        yield PascalStringWin32(self, "writer_name", charset="UTF-16-BE")
        yield PascalStringWin32(self, "reader_name", charset="UTF-16-BE")
        yield UInt32(self, "file_version")
        size = (self.size - self.current_size) // 8
        if size:
            yield NullBytes(self, "padding", size)

class Photoshop8BIM(FieldSet):
    TAG_INFO = {
        0x03ed: ("res_info", None, "Resolution information"),
        0x03f3: ("print_flag", None, "Print flags: labels, crop marks, colour bars, etc."),
        0x03f5: ("col_half_info", None, "Colour half-toning information"),
        0x03f8: ("color_trans_func", None, "Colour transfer function"),
        0x0404: ("iptc", IPTC, "IPTC/NAA"),
        0x0406: ("jpeg_qual", None, "JPEG quality"),
        0x0408: ("grid_guide", None, "Grid guides informations"),
        0x040a: ("copyright_flag", None, "Copyright flag"),
        0x040c: ("thumb_res2", None, "Thumbnail resource (2)"),
        0x040d: ("glob_angle", None, "Global lighting angle for effects"),
        0x0411: ("icc_tagged", None, "ICC untagged (1 means intentionally untagged)"),
        0x0414: ("base_layer_id", None, "Base value for new layers ID's"),
        0x0419: ("glob_altitude", None, "Global altitude"),
        0x041a: ("slices", None, "Slices"),
        0x041e: ("url_list", None, "Unicode URL's"),
        0x0421: ("version", Version, "Version information"),
        0x2710: ("print_flag2", None, "Print flags (2)"),
    }
    TAG_NAME = createDict(TAG_INFO, 0)
    CONTENT_HANDLER = createDict(TAG_INFO, 1)
    TAG_DESC = createDict(TAG_INFO, 2)

    def __init__(self, *args, **kw):
        FieldSet.__init__(self, *args, **kw)
        try:
            self._name, self.handler, self._description = self.TAG_INFO[self["tag"].value]
        except KeyError:
            self.handler = None
        size = self["size"]
        self._size = size.address + size.size + alignValue(size.value, 2) * 8

    def createFields(self):
        yield String(self, "signature", 4, "8BIM signature", charset="ASCII")
        if self["signature"].value != "8BIM":
            raise ParserError("Stream doesn't look like 8BIM item (wrong signature)!")
        yield textHandler(UInt16(self, "tag"), hexadecimal)
        if self.stream.readBytes(self.absolute_address + self.current_size, 4) != "\0\0\0\0":
            yield PascalString8(self, "name")
            size = 2 + (self["name"].size // 8) % 2
            yield NullBytes(self, "name_padding", size)
        else:
            yield String(self, "name", 4, strip="\0")
        yield UInt16(self, "size")
        size = alignValue(self["size"].value, 2)
        if not size:
            return
        if self.handler:
            yield self.handler(self, "content", size=size*8)
        else:
            yield RawBytes(self, "content", size)

class PhotoshopMetadata(FieldSet):
    def createFields(self):
        yield CString(self, "signature", "Photoshop version")
        if self["signature"].value == "Photoshop 3.0":
            while not self.eof:
                yield Photoshop8BIM(self, "item[]")
        else:
            size = (self._size - self.current_size) / 8
            yield RawBytes(self, "rawdata", size)

