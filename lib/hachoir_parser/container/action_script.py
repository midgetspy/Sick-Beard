"""
SWF (Macromedia/Adobe Flash) file parser.

Documentation:

 - Alexis' SWF Reference:
   http://www.m2osw.com/swf_alexref.html

Author: Sebastien Ponce
Creation date: 26 April 2008
"""

from hachoir_core.field import (FieldSet, ParserError,
    Bit, Bits, UInt8, UInt32, Int16, UInt16, Float32, CString,
    RawBytes)
#from hachoir_core.field import Field
from hachoir_core.field.float import FloatExponent
from struct import unpack

class FlashFloat64(FieldSet):
    def createFields(self):
        yield Bits(self, "mantisa_high", 20)
        yield FloatExponent(self, "exponent", 11)
        yield Bit(self, "negative")
        yield Bits(self, "mantisa_low", 32)

    def createValue(self):
        # Manual computation:
        # mantisa = mantisa_high * 2^32 + mantisa_low
        # float = 2^exponent + (1 + mantisa / 2^52)
        # (and float is negative if negative=True)
        bytes = self.parent.stream.readBytes(
            self.absolute_address, self.size//8)
        # Mix bytes: xxxxyyyy <=> yyyyxxxx
        bytes = bytes[4:8] + bytes[0:4]
        return unpack('<d', bytes)[0]

TYPE_INFO = {
    0x00: (CString, "Cstring[]"),
    0x01: (Float32, "Float[]"),
    0x02: (None, "Null[]"),
    0x03: (None, "Undefined[]"),
    0x04: (UInt8, "Register[]"),
    0x05: (UInt8, "Boolean[]"),
    0x06: (FlashFloat64, "Double[]"),
    0x07: (UInt32, "Integer[]"),
    0x08: (UInt8, "Dictionnary_Lookup_Index[]"),
    0x09: (UInt16, "Large_Dictionnary_Lookup_Index[]"),
}

def parseBranch(parent, size):
    yield Int16(parent, "offset")

def parseDeclareFunction(parent, size):
    yield CString(parent, "name")
    argCount = UInt16(parent, "arg_count")
    yield argCount
    for i in range(argCount.value):
        yield CString(parent, "arg[]")
    yield UInt16(parent, "function_length")

def parseDeclareFunctionV7(parent, size):
    yield CString(parent, "name")
    argCount = UInt16(parent, "arg_count")
    yield argCount
    yield UInt8(parent, "reg_count")
    yield Bits(parent, "reserved", 7)
    yield Bit(parent, "preload_global")
    yield Bit(parent, "preload_parent")
    yield Bit(parent, "preload_root")
    yield Bit(parent, "suppress_super")
    yield Bit(parent, "preload_super")
    yield Bit(parent, "suppress_arguments")
    yield Bit(parent, "preload_arguments")
    yield Bit(parent, "suppress_this")
    yield Bit(parent, "preload_this")
    for i in range(argCount.value):
        yield UInt8(parent, "register[]")
        yield CString(parent, "arg[]")
    yield UInt16(parent, "function_length")

def parseTry(parent, size):
    yield Bits(parent, "reserved", 5)
    catchInReg = Bit(parent, "catch_in_register")
    yield catchInReg
    yield Bit(parent, "finally")
    yield Bit(parent, "catch")
    yield UInt8(parent, "try_size")
    yield UInt8(parent, "catch_size")
    yield UInt8(parent, "finally_size")
    if catchInReg.value:
        yield CString(parent, "name")
    else:
        yield UInt8(parent, "register")

def parsePushData(parent, size):
    while not parent.eof:
        codeobj = UInt8(parent, "data_type[]")
        yield codeobj
        code = codeobj.value
        if code not in TYPE_INFO:
            raise ParserError("Unknown type in Push_Data : " + hex(code))
        parser, name = TYPE_INFO[code]
        if parser:
            yield parser(parent, name)
#        else:
#            yield Field(parent, name, 0)

def parseSetTarget(parent, size):
    yield CString(parent, "target")

def parseWith(parent, size):
    yield UInt16(parent, "size")

def parseGetURL(parent, size):
    yield CString(parent, "url")
    yield CString(parent, "target")

def parseGetURL2(parent, size):
    yield UInt8(parent, "method")

def parseGotoExpression(parent, size):
    yield UInt8(parent, "play")

def parseGotoFrame(parent, size):
    yield UInt16(parent, "frame_no")

def parseGotoLabel(parent, size):
    yield CString(parent, "label")

def parseWaitForFrame(parent, size):
    yield UInt16(parent, "frame")
    yield UInt8(parent, "skip")

def parseWaitForFrameDyn(parent, size):
    yield UInt8(parent, "skip")

def parseDeclareDictionnary(parent, size):
    count = UInt16(parent, "count")
    yield count
    for i in range(count.value):
        yield CString(parent, "dictionnary[]")

def parseStoreRegister(parent, size):
    yield UInt8(parent, "register")

def parseStrictMode(parent, size):
    yield UInt8(parent, "strict")

class Instruction(FieldSet):
    ACTION_INFO = {
        0x00: ("end[]", "End", None),
        0x99: ("Branch_Always[]", "Branch Always", parseBranch),
        0x9D: ("Branch_If_True[]", "Branch If True", parseBranch),
        0x3D: ("Call_Function[]", "Call Function", None),
        0x52: ("Call_Method[]", "Call Method", None),
        0x9B: ("Declare_Function[]", "Declare Function", parseDeclareFunction),
        0x8E: ("Declare_Function_V7[]", "Declare Function (V7)", parseDeclareFunctionV7),
        0x3E: ("Return[]", "Return", None),
        0x2A: ("Throw[]", "Throw", None),
        0x8F: ("Try[]", "Try", parseTry),
        # Stack Control
        0x4C: ("Duplicate[]", "Duplicate", None),
        0x96: ("Push_Data[]", "Push Data", parsePushData),
        0x4D: ("Swap[]", "Swap", None),
        # Action Script Context
        0x8B: ("Set_Target[]", "Set Target", parseSetTarget),
        0x20: ("Set_Target_dynamic[]", "Set Target (dynamic)", None),
        0x94: ("With[]", "With", parseWith),
        # Movie Control
        0x9E: ("Call_Frame[]", "Call Frame", None),
        0x83: ("Get_URL[]", "Get URL", parseGetURL),
        0x9A: ("Get_URL2[]", "Get URL2", parseGetURL2),
        0x9F: ("Goto_Expression[]", "Goto Expression", parseGotoExpression),
        0x81: ("Goto_Frame[]", "Goto Frame", parseGotoFrame),
        0x8C: ("Goto_Label[]", "Goto Label", parseGotoLabel),
        0x04: ("Next_Frame[]", "Next Frame", None),
        0x06: ("Play[]", "Play", None),
        0x05: ("Previous_Frame[]", "Previous Frame", None),
        0x07: ("Stop[]", "Stop", None),
        0x08: ("Toggle_Quality[]", "Toggle Quality", None),
        0x8A: ("Wait_For_Frame[]", "Wait For Frame", parseWaitForFrame),
        0x8D: ("Wait_For_Frame_dynamic[]", "Wait For Frame (dynamic)", parseWaitForFrameDyn),
        # Sound
        0x09: ("Stop_Sound[]", "Stop Sound", None),
        # Arithmetic
        0x0A: ("Add[]", "Add", None),
        0x47: ("Add_typed[]", "Add (typed)", None),
        0x51: ("Decrement[]", "Decrement", None),
        0x0D: ("Divide[]", "Divide", None),
        0x50: ("Increment[]", "Increment", None),
        0x18: ("Integral_Part[]", "Integral Part", None),
        0x3F: ("Modulo[]", "Modulo", None),
        0x0C: ("Multiply[]", "Multiply", None),
        0x4A: ("Number[]", "Number", None),
        0x0B: ("Subtract[]", "Subtract", None),
        # Comparisons
        0x0E: ("Equal[]", "Equal", None),
        0x49: ("Equal_typed[]", "Equal (typed)", None),
        0x66: ("Strict_Equal[]", "Strict Equal", None),
        0x67: ("Greater_Than_typed[]", "Greater Than (typed)", None),
        0x0F: ("Less_Than[]", "Less Than", None),
        0x48: ("Less_Than_typed[]", "Less Than (typed)", None),
        0x13: ("String_Equal[]", "String Equal", None),
        0x68: ("String_Greater_Than[]", "String Greater Than", None),
        0x29: ("String_Less_Than[]", "String Less Than", None),
        # Logical and Bit Wise
        0x60: ("And[]", "And", None),
        0x10: ("Logical_And[]", "Logical And", None),
        0x12: ("Logical_Not[]", "Logical Not", None),
        0x11: ("Logical_Or[]", "Logical Or", None),
        0x61: ("Or[]", "Or", None),
        0x63: ("Shift_Left[]", "Shift Left", None),
        0x64: ("Shift_Right[]", "Shift Right", None),
        0x65: ("Shift_Right_Unsigned[]", "Shift Right Unsigned", None),
        0x62: ("Xor[]", "Xor", None),
        # Strings & Characters (See the String Object also)
        0x33: ("Chr[]", "Chr", None),
        0x37: ("Chr_multi-bytes[]", "Chr (multi-bytes)", None),
        0x21: ("Concatenate_Strings[]", "Concatenate Strings", None),
        0x32: ("Ord[]", "Ord", None),
        0x36: ("Ord_multi-bytes[]", "Ord (multi-bytes)", None),
        0x4B: ("String[]", "String", None),
        0x14: ("String_Length[]", "String Length", None),
        0x31: ("String_Length_multi-bytes[]", "String Length (multi-bytes)", None),
        0x15: ("SubString[]", "SubString", None),
        0x35: ("SubString_multi-bytes[]", "SubString (multi-bytes)", None),
        # Properties
        0x22: ("Get_Property[]", "Get Property", None),
        0x23: ("Set_Property[]", "Set Property", None),
        # Objects
        0x2B: ("Cast_Object[]", "Cast Object", None),
        0x42: ("Declare_Array[]", "Declare Array", None),
        0x88: ("Declare_Dictionary[]", "Declare Dictionary", parseDeclareDictionnary),
        0x43: ("Declare_Object[]", "Declare Object", None),
        0x3A: ("Delete[]", "Delete", None),
        0x3B: ("Delete_All[]", "Delete All", None),
        0x24: ("Duplicate_Sprite[]", "Duplicate Sprite", None),
        0x46: ("Enumerate[]", "Enumerate", None),
        0x55: ("Enumerate_Object[]", "Enumerate Object", None),
        0x69: ("Extends[]", "Extends", None),
        0x4E: ("Get_Member[]", "Get Member", None),
        0x45: ("Get_Target[]", "Get Target", None),
        0x2C: ("Implements[]", "Implements", None),
        0x54: ("Instance_Of[]", "Instance Of", None),
        0x40: ("New[]", "New", None),
        0x53: ("New_Method[]", "New Method", None),
        0x25: ("Remove_Sprite[]", "Remove Sprite", None),
        0x4F: ("Set_Member[]", "Set Member", None),
        0x44: ("Type_Of[]", "Type Of", None),
        # Variables
        0x41: ("Declare_Local_Variable[]", "Declare Local Variable", None),
        0x1C: ("Get_Variable[]", "Get Variable", None),
        0x3C: ("Set_Local_Variable[]", "Set Local Variable", None),
        0x1D: ("Set_Variable[]", "Set Variable", None),
        # Miscellaneous
        0x2D: ("FSCommand2[]", "FSCommand2", None),
        0x34: ("Get_Timer[]", "Get Timer", None),
        0x30: ("Random[]", "Random", None),
        0x27: ("Start_Drag[]", "Start Drag", None),
        0x28: ("Stop_Drag[]", "Stop Drag", None),
        0x87: ("Store_Register[]", "Store Register", parseStoreRegister),
        0x89: ("Strict_Mode[]", "Strict Mode", parseStrictMode),
        0x26: ("Trace[]", "Trace", None),
    }

    def __init__(self, *args):
        FieldSet.__init__(self, *args)
        code = self["action_id"].value
        if code & 128:
            self._size = (3 + self["action_length"].value) * 8
        else:
            self._size = 8
        if code in self.ACTION_INFO:
            self._name, self._description, self.parser = self.ACTION_INFO[code]
        else:
            self.parser = None

    def createFields(self):
        yield Bits(self, "action_id", 8)
        if not (self["action_id"].value & 128):
            return
        yield UInt16(self, "action_length")
        size = self["action_length"].value
        if not size:
            return
        if self.parser:
            for field in self.parser(self, size):
                yield field
        else:
            yield RawBytes(self, "action_data", size)

    def createDescription(self):
        return self._description

    def __str__(self):
        r = str(self._description)
        for f in self:
            if f.name not in ("action_id", "action_length", "count") and not f.name.startswith("data_type") :
                r = r + "\n   " + str((self.address+f.address)/8) + " " + str(f.name) + "=" + str(f.value)
        return r

class ActionScript(FieldSet):
    def createFields(self):
        while not self.eof:
            yield Instruction(self, "instr[]")

    def __str__(self):
        r = ""
        for f in self:
            r = r + str(f.address/8) + " " + str(f) + "\n"
        return r

def parseActionScript(parent, size):
    yield ActionScript(parent, "action", size=size*8)

