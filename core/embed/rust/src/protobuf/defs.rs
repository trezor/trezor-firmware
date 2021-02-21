use core::{mem, slice};

pub struct Msg {
    pub fields: &'static [Field],
    pub defaults: &'static [u8],
}

impl Msg {
    pub fn for_wire_id(wire_id: u16) -> Option<Self> {
        find_msg_index(wire_id).map(|msg_index| unsafe {
            // SAFETY: We are taking the index right out of `find_msg_index` so we can be
            // sure it's trusted.
            find_msg(msg_index)
        })
    }

    pub fn field(&self, tag: u8) -> Option<&Field> {
        self.fields.iter().find(|field| field.tag == tag)
    }
}

#[repr(C, packed)]
pub struct Field {
    pub tag: u8,
    flags_and_type: u8,
    enum_or_msg_index: u16,
    pub name: u16,
}

impl Field {
    pub fn get_type(&self) -> FieldType {
        match self.ftype() {
            0 => FieldType::UVarInt,
            1 => FieldType::SVarInt,
            2 => FieldType::Bool,
            3 => FieldType::Bytes,
            4 => FieldType::String,
            5 => FieldType::Enum(unsafe { find_enum(self.enum_or_msg_index) }),
            6 => FieldType::Msg(unsafe { find_msg(self.enum_or_msg_index) }),
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
    Enum(Enum),
    Msg(Msg),
}

pub struct Enum {
    pub values: &'static [u16],
}

static ENUM_DEFS: &[u8] = include_bytes!("../../../../src/trezor/messages/proto_enums.data");
static MSG_DEFS: &[u8] = include_bytes!("../../../../src/trezor/messages/proto_msgs.data");
static WIRE_DEFS: &[u8] = include_bytes!("../../../../src/trezor/messages/proto_wire.data");

fn find_msg_index(wire_id: u16) -> Option<u16> {
    #[repr(C, packed)]
    struct WireDef {
        wire_id: u16,
        msg_index: u16,
    }

    let wire_defs: &[WireDef] = unsafe {
        slice::from_raw_parts(
            WIRE_DEFS.as_ptr().cast(),
            WIRE_DEFS.len() / mem::size_of::<WireDef>(),
        )
    };
    for def in wire_defs {
        if def.wire_id == wire_id {
            return Some(def.msg_index);
        }
    }
    None
}

unsafe fn find_msg(msg_index: u16) -> Msg {
    // #[repr(C, packed)]
    // struct MsgDef {
    //     fields_count: u8,
    //     defaults_size: u8,
    //     fields: [Field],
    //     defaults: [u8],
    // }

    let mut ptr = MSG_DEFS.as_ptr();
    let mut i = 0;
    loop {
        let fields_count = ptr.offset(0).read() as usize;
        let defaults_size = ptr.offset(1).read() as usize;

        let fields_size = fields_count * mem::size_of::<Field>();
        let fields_ptr = ptr.offset(2);
        let defaults_ptr = ptr.offset(2).add(fields_size);

        if i == msg_index {
            break Msg {
                fields: slice::from_raw_parts(fields_ptr.cast(), fields_count),
                defaults: slice::from_raw_parts(defaults_ptr.cast(), defaults_size),
            };
        } else {
            ptr = defaults_ptr.add(defaults_size);
            i += 1;
        }
    }
}

unsafe fn find_enum(enum_index: u16) -> Enum {
    // #[repr(C, packed)]
    // struct EnumDef {
    //     count: u8,
    //     vals: [u16],
    // }

    let mut ptr = ENUM_DEFS.as_ptr();
    let mut i = 0;
    loop {
        let count = ptr.offset(0).read() as usize;
        let vals = ptr.offset(1);
        if i == enum_index {
            break Enum {
                values: slice::from_raw_parts(vals.cast(), count),
            };
        } else {
            ptr = vals.add(count * 2);
            i += 1;
        }
    }
}
