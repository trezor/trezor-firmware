use core::{mem, slice};

pub struct MsgDef {
    pub fields: &'static [FieldDef],
    pub defaults: &'static [u8],
    pub is_experimental: bool,
    pub wire_id: Option<u16>,
    pub offset: u16,
}

impl MsgDef {
    pub fn for_name(msg_name: u16) -> Option<Self> {
        find_msg_offset_by_name(msg_name).map(|msg_offset| unsafe {
            // SAFETY: We are taking the offset right out of the definitions so we can be
            // sure it's to be trusted.
            get_msg(msg_offset)
        })
    }

    pub fn for_wire_id(wire_id: u16) -> Option<Self> {
        find_msg_offset_by_wire(wire_id).map(|msg_offset| unsafe {
            // SAFETY: We are taking the offset right out of the definitions so we can be
            // sure it's to be trusted.
            get_msg(msg_offset)
        })
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
            5 => FieldType::Enum(unsafe { get_enum(self.enum_or_msg_offset) }),
            6 => FieldType::Msg(unsafe { get_msg(self.enum_or_msg_offset) }),
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

static ENUM_DEFS: &[u8] = include_bytes!(concat!(env!("OUT_DIR"), "/../../../../proto_enums.data"));
static MSG_DEFS: &[u8] = include_bytes!(concat!(env!("OUT_DIR"), "/../../../..//proto_msgs.data"));
static NAME_DEFS: &[u8] = include_bytes!(concat!(env!("OUT_DIR"), "/../../../..//proto_names.data"));
static WIRE_DEFS: &[u8] = include_bytes!(concat!(env!("OUT_DIR"), "/../../../..//proto_wire.data"));

fn find_msg_offset_by_name(msg_name: u16) -> Option<u16> {
    #[repr(C, packed)]
    struct NameDef {
        msg_name: u16,
        msg_offset: u16,
    }

    let name_defs: &[NameDef] = unsafe {
        slice::from_raw_parts(
            NAME_DEFS.as_ptr().cast(),
            NAME_DEFS.len() / mem::size_of::<NameDef>(),
        )
    };
    name_defs
        .binary_search_by_key(&msg_name, |def| def.msg_name)
        .map(|i| name_defs[i].msg_offset)
        .ok()
}

fn find_msg_offset_by_wire(wire_id: u16) -> Option<u16> {
    #[repr(C, packed)]
    struct WireDef {
        wire_id: u16,
        msg_offset: u16,
    }

    let wire_defs: &[WireDef] = unsafe {
        slice::from_raw_parts(
            WIRE_DEFS.as_ptr().cast(),
            WIRE_DEFS.len() / mem::size_of::<WireDef>(),
        )
    };
    wire_defs
        .binary_search_by_key(&wire_id, |def| def.wire_id)
        .map(|i| wire_defs[i].msg_offset)
        .ok()
}

unsafe fn get_msg(msg_offset: u16) -> MsgDef {
    // #[repr(C, packed)]
    // struct MsgDef {
    //     fields_count: u8,
    //     defaults_size: u8,
    //     flags_and_wire_id: u16,
    //     fields: [Field],
    //     defaults: [u8],
    // }

    // SAFETY: `msg_offset` has to point to a beginning of a valid message
    // definition inside `MSG_DEFS`.
    unsafe {
        let ptr = MSG_DEFS.as_ptr().add(msg_offset as usize);
        let fields_count = ptr.offset(0).read() as usize;
        let defaults_size = ptr.offset(1).read() as usize;

        let flags_and_wire_id_lo = ptr.offset(2).read();
        let flags_and_wire_id_hi = ptr.offset(3).read();
        let flags_and_wire_id = u16::from_le_bytes([flags_and_wire_id_lo, flags_and_wire_id_hi]);

        let is_experimental = flags_and_wire_id & 0x8000 != 0;
        let wire_id = match flags_and_wire_id & 0x7FFF {
            0x7FFF => None,
            some_wire_id => Some(some_wire_id),
        };

        let fields_size = fields_count * mem::size_of::<FieldDef>();
        let fields_ptr = ptr.offset(4);
        let defaults_ptr = ptr.offset(4).add(fields_size);

        MsgDef {
            fields: slice::from_raw_parts(fields_ptr.cast(), fields_count),
            defaults: slice::from_raw_parts(defaults_ptr.cast(), defaults_size),
            is_experimental,
            wire_id,
            offset: msg_offset,
        }
    }
}

unsafe fn get_enum(enum_offset: u16) -> EnumDef {
    // #[repr(C, packed)]
    // struct EnumDef {
    //     count: u8,
    //     vals: [u16],
    // }

    // SAFETY: `enum_offset` has to point to a beginning of a valid enum
    // definition inside `ENUM_DEFS`.
    unsafe {
        let ptr = ENUM_DEFS.as_ptr().add(enum_offset as usize);
        let count = ptr.offset(0).read() as usize;
        let vals = ptr.offset(1);

        EnumDef {
            values: slice::from_raw_parts(vals.cast(), count),
        }
    }
}
