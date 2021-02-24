use core::{mem, slice};

pub struct MsgDef {
    pub fields: &'static [FieldDef],
    pub defaults: &'static [u8],
}

impl MsgDef {
    pub fn for_wire_id(wire_id: u16) -> Option<Self> {
        find_msg_offset(wire_id).map(|msg_offset| unsafe {
            // SAFETY: We are taking the offset right out of `find_msg_offset` so we can be
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
        self.flags() & 0b1000_0000 != 0
    }

    pub fn is_repeated(&self) -> bool {
        self.flags() & 0b0100_0000 != 0
    }

    pub fn is_experimental(&self) -> bool {
        self.flags() & 0b0010_0000 != 0
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

pub const WIRE_TYPE_VARINT: u8 = 0;
pub const WIRE_TYPE_LENGTH_DELIMITED: u8 = 2;

impl FieldType {
    pub fn wire_type(&self) -> u8 {
        match self {
            FieldType::UVarInt | FieldType::SVarInt | FieldType::Bool | FieldType::Enum(_) => {
                WIRE_TYPE_VARINT
            }
            FieldType::Bytes | FieldType::String | FieldType::Msg(_) => WIRE_TYPE_LENGTH_DELIMITED,
        }
    }
}

pub struct EnumDef {
    pub values: &'static [u16],
}

static ENUM_DEFS: &[u8] = include_bytes!("../../../../src/trezor/messages/proto_enums.data");
static MSG_DEFS: &[u8] = include_bytes!("../../../../src/trezor/messages/proto_msgs.data");
static WIRE_DEFS: &[u8] = include_bytes!("../../../../src/trezor/messages/proto_wire.data");

fn find_msg_offset(wire_id: u16) -> Option<u16> {
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
    //     fields: [Field],
    //     defaults: [u8],
    // }

    let ptr = MSG_DEFS.as_ptr().add(msg_offset as usize);
    let fields_count = ptr.offset(0).read() as usize;
    let defaults_size = ptr.offset(1).read() as usize;

    let fields_size = fields_count * mem::size_of::<FieldDef>();
    let fields_ptr = ptr.offset(2);
    let defaults_ptr = ptr.offset(2).add(fields_size);

    MsgDef {
        fields: slice::from_raw_parts(fields_ptr.cast(), fields_count),
        defaults: slice::from_raw_parts(defaults_ptr.cast(), defaults_size),
    }
}

unsafe fn get_enum(enum_offset: u16) -> EnumDef {
    // #[repr(C, packed)]
    // struct EnumDef {
    //     count: u8,
    //     vals: [u16],
    // }

    let ptr = ENUM_DEFS.as_ptr().add(enum_offset as usize);
    let count = ptr.offset(0).read() as usize;
    let vals = ptr.offset(1);

    EnumDef {
        values: slice::from_raw_parts(vals.cast(), count),
    }
}
