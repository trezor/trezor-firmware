use core::mem;

use crate::align::include_aligned;

macro_rules! proto_def_path {
    ($filename:expr) => {
        concat!(env!("BUILD_DIR"), "/rust/", $filename)
    };
}

static ENUM_DEFS: &[u8] = include_aligned!(u16, proto_def_path!("proto_enums.data"));
static MSG_DEFS: &[u8] = include_aligned!(u16, proto_def_path!("proto_msgs.data"));
static NAME_DEFS: &[u8] = include_aligned!(NameDef, proto_def_path!("proto_names.data"));
static WIRE_DEFS: &[u8] = include_aligned!(WireDef, proto_def_path!("proto_wire.data"));

pub struct MsgDef {
    pub fields: &'static [FieldDef],
    pub defaults: &'static [u8],
    pub is_experimental: bool,
    pub wire_id: Option<u16>,
    pub offset: u16,
}

impl MsgDef {
    pub fn for_name(msg_name: u16) -> Option<Self> {
        find_msg_offset_by_name(msg_name).map(get_msg)
    }

    pub fn for_wire_id(enum_name: u16, wire_id: u16) -> Option<Self> {
        find_msg_offset_by_wire(enum_name, wire_id).map(get_msg)
    }

    pub fn field(&self, tag: u8) -> Option<&FieldDef> {
        self.fields.iter().find(|field| field.tag == tag)
    }
}

#[repr(C, packed)]
pub struct FieldDef {
    pub tag: u8,
    flags_and_type: u8,
    enum_or_msg_offset: u16,
    pub name: u16,
}

impl FieldDef {
    pub fn get_type(&self) -> FieldType {
        match self.ftype() {
            0 => FieldType::UVarInt,
            1 => FieldType::SVarInt,
            2 => FieldType::Bool,
            3 => FieldType::Bytes,
            4 => FieldType::String,
            5 => FieldType::Enum(get_enum(self.enum_or_msg_offset)),
            6 => FieldType::Msg(get_msg(self.enum_or_msg_offset)),
            _ => unreachable!(),
        }
    }

    pub fn is_required(&self) -> bool {
        self.flags() & 0b_1000_0000 != 0
    }

    pub fn is_repeated(&self) -> bool {
        self.flags() & 0b_0100_0000 != 0
    }

    pub fn is_experimental(&self) -> bool {
        self.flags() & 0b_0010_0000 != 0
    }

    fn flags(&self) -> u8 {
        self.flags_and_type & 0xF0
    }

    fn ftype(&self) -> u8 {
        self.flags_and_type & 0x0F
    }
}

pub enum FieldType {
    UVarInt,
    SVarInt,
    Bool,
    Bytes,
    String,
    Enum(EnumDef),
    Msg(MsgDef),
}

pub const PRIMITIVE_TYPE_VARINT: u8 = 0;
pub const PRIMITIVE_TYPE_LENGTH_DELIMITED: u8 = 2;

impl FieldType {
    pub fn primitive_type(&self) -> u8 {
        match self {
            FieldType::UVarInt | FieldType::SVarInt | FieldType::Bool | FieldType::Enum(_) => {
                PRIMITIVE_TYPE_VARINT
            }
            FieldType::Bytes | FieldType::String | FieldType::Msg(_) => {
                PRIMITIVE_TYPE_LENGTH_DELIMITED
            }
        }
    }
}

pub struct EnumDef {
    pub values: &'static [u16],
}

#[repr(C, packed)]
struct NameDef {
    msg_name: u16,
    msg_offset: u16,
}

impl NameDef {
    pub fn defs() -> &'static [NameDef] {
        // SAFETY: NameDef is a packed struct of ints, so all bit patterns are valid.
        let (_pre, name_defs, _post) = unsafe { NAME_DEFS.align_to::<NameDef>() };
        // per `include_aligned!` macro, NAME_DEFS is aligned to NameDef, so `name_defs`
        // array should be cleanly aligned.
        assert!(_pre.is_empty());
        assert!(_post.is_empty());
        name_defs
    }
}

#[repr(C, packed)]
struct WireDef {
    enum_name: u16,
    wire_id: u16,
    msg_offset: u16,
}

impl WireDef {
    pub fn defs() -> &'static [WireDef] {
        // SAFETY: WireDef is a packed struct of ints, so all bit patterns are valid.
        let (_pre, wire_defs, _post) = unsafe { WIRE_DEFS.align_to::<WireDef>() };
        // per `include_aligned!` macro, WIRE_DEFS is aligned to WireDef, so `wire_defs`
        // array should be cleanly aligned.
        assert!(_pre.is_empty());
        assert!(_post.is_empty());
        wire_defs
    }
}

pub fn find_name_by_msg_offset(msg_offset: u16) -> Option<u16> {
    NameDef::defs()
        .iter()
        .find(|def| def.msg_offset == msg_offset)
        .map(|def| def.msg_name)
}

fn find_msg_offset_by_name(msg_name: u16) -> Option<u16> {
    let name_defs = NameDef::defs();
    name_defs
        .binary_search_by_key(&msg_name, |def| def.msg_name)
        .map(|i| name_defs[i].msg_offset)
        .ok()
}

fn find_msg_offset_by_wire(enum_name: u16, wire_id: u16) -> Option<u16> {
    let wire_defs = WireDef::defs();
    wire_defs
        .binary_search_by_key(&(enum_name, wire_id), |def| (def.enum_name, def.wire_id))
        .map(|i| wire_defs[i].msg_offset)
        .ok()
}

pub fn get_msg(msg_offset: u16) -> MsgDef {
    // #[repr(C, packed)]
    // struct MsgDef {
    //     fields_count: u8,
    //     defaults_size: u8,
    //     flags_and_wire_id: u16,
    //     fields: [Field],
    //     defaults: [u8],
    // }
    let msg_def_start = &MSG_DEFS[msg_offset as usize..];
    let fields_count = msg_def_start[0] as usize;
    let defaults_size = msg_def_start[1] as usize;

    let flags_and_wire_id = u16::from_le_bytes([msg_def_start[2], msg_def_start[3]]);
    let is_experimental = flags_and_wire_id & 0x8000 != 0;
    let wire_id = match flags_and_wire_id & 0x7FFF {
        0x7FFF => None,
        some_wire_id => Some(some_wire_id),
    };

    let fields_size_in_bytes = fields_count * mem::size_of::<FieldDef>();
    let fields_start = 4;
    let fields_end = fields_start + fields_size_in_bytes;
    let fields_byteslice = &msg_def_start[fields_start..fields_end];

    // PREREQUISITES:
    // * MSG_DEFS is aligned to u16 (per `include_aligned!` macro)
    // * FieldDef has the same alignment
    assert!(mem::align_of::<FieldDef>() == mem::align_of::<u16>());
    // * both msg_offset and fields_start added together keep the alignment:
    assert!(fields_byteslice.as_ptr().addr() % mem::align_of::<FieldDef>() == 0);

    // SAFETY: FieldDef is a packed struct of ints, so all bit patterns are valid.
    let (_pre, fields, _post) = unsafe { fields_byteslice.align_to::<FieldDef>() };
    // Given the prerequisites, `fields` array must be cleanly aligned.
    assert!(_pre.is_empty());
    assert!(_post.is_empty());

    let defaults_start = fields_end;
    let defaults_end = defaults_start + defaults_size;
    // `defaults` is a byteslice so its alignment is always ok
    let defaults = &msg_def_start[defaults_start..defaults_end];

    MsgDef {
        fields,
        defaults,
        is_experimental,
        wire_id,
        offset: msg_offset,
    }
}

fn get_enum(enum_offset: u16) -> EnumDef {
    // #[repr(C, packed)]
    // struct EnumDef {
    //     count: u16,
    //     vals: [u16],
    // }
    const SIZE: u16 = mem::size_of::<u16>() as u16;

    // SAFETY: enum_defs is an array of u16, so all bit patterns are valid.
    let (_pre, enum_defs, _post) = unsafe { ENUM_DEFS.align_to::<u16>() };
    // ENUM_DEFS is aligned to u16 per `include_aligned!` macro
    assert!(_pre.is_empty());
    assert!(_post.is_empty());

    // enum_offset is a raw byte offset, we check that it is also a valid index of
    // an u16
    assert!(enum_offset % SIZE == 0);
    let offset: usize = (enum_offset / SIZE).into();
    let count: usize = enum_defs[offset].into();
    EnumDef {
        values: &enum_defs[offset + 1..offset + 1 + count],
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::micropython::qstr::Qstr;

    #[test]
    fn wire_type_basic_lookup() {
        // SignTx: 15
        assert!(find_msg_offset_by_wire(Qstr::MP_QSTR_MessageType.to_u16(), 15).is_some());
        // Guaranteed empty.
        assert!(find_msg_offset_by_wire(Qstr::MP_QSTR_CONFIRMED.to_u16(), 15).is_none());
    }
}
