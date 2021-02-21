use core::convert::{TryFrom, TryInto};

use crate::{
    error::Error,
    micropython::{buffer::Buffer, dict::Dict, gc::Gc, list::List, obj::Obj, qstr::Qstr},
    util,
};

use super::defs::{Field, FieldType, Msg};

#[no_mangle]
pub extern "C" fn protobuf_decode(buf: Obj, wire_id: Obj) -> Obj {
    util::try_or_none(|| {
        let msg = Msg::for_wire_id(wire_id.try_into()?).ok_or(Error::Missing)?;
        let buf = Buffer::try_from(buf)?;
        let mut stream = InputStream::new(&buf);
        let decoder = Decoder {
            enable_experimental: false,
        };
        let obj = decoder
            .decode_message(&mut stream, &msg)
            .ok_or(Error::InvalidType)?;
        Ok(obj)
    })
}

pub struct Decoder {
    pub enable_experimental: bool,
}

impl Decoder {
    pub fn decode_message(&self, stream: &mut InputStream, msg: &Msg) -> Option<Obj> {
        // Allocate the backing dict with enough pre-allocated space for all fields.
        let dict = Dict::alloc_with_capacity(msg.fields().len());

        // Decode fields one-by-one from the input stream.
        loop {
            let field_key = match stream.read_uvarint() {
                Some(key) => key,
                None => break,
            };
            let field_tag = (field_key >> 3) as u8; // TODO: check the cast
            let wire_type = (field_key & 7) as u8;

            match msg.field(field_tag) {
                Some(field) => {
                    let field_value = self.decode_field(stream, field)?;
                    let field_name = Qstr::from(field.name);
                    if field.is_repeated() {
                        // Repeated field, values are stored in a list.
                        unsafe {
                            // Look up the list object. If it exists, append to it. If it doesn't,
                            // create a new list with this field's value and assign it.
                            if let Some(obj) = dict.map().get(field_name).ok() {
                                let list = Gc::<List>::try_from(obj).ok()?;
                                list.append(field_value);
                            } else {
                                let list = List::alloc(&[field_value]);
                                dict.map().set(field_name, list);
                            }
                        }
                    } else {
                        // Singular field, assign the value directly.
                        unsafe {
                            dict.map().set(field_name, field_value);
                        }
                    }
                }
                None => {
                    // Unknown field, skip it.
                    // TODO: skip
                }
            }
        }

        // Fill in the default values. Only signular fields are allowed to have a
        // default value, this is enforced in the def compilation.
        for default in msg.defaults() {
            let field = msg.fields().iter().find(|field| field.tag == default.tag)?;
            let field_name = Qstr::from(field.name);
            if dict.map().contains_key(field_name) {
                // Field already has a value, do nothing.
            } else {
                // Decode the value and assign it.
                let field_stream = &mut InputStream::new(default.value);
                let field_value = self.decode_field(field_stream, field)?;
                unsafe {
                    dict.map().set(field_name, field_value);
                }
            }
        }

        Some(dict.into())
    }

    pub fn decode_field(&self, stream: &mut InputStream, field: &Field) -> Option<Obj> {
        if field.is_experimental() && !self.enable_experimental {
            return None;
        }
        let num = stream.read_uvarint()?;
        match field.get_type() {
            FieldType::UVarInt => Some(num.try_into().ok()?),
            FieldType::SVarInt => {
                let signed_int = to_signed(num);
                Some(signed_int.into())
            }
            FieldType::Bool => {
                let boolean = num != 0;
                Some(boolean.into())
            }
            FieldType::Bytes => {
                let buf_len = num.try_into().ok()?;
                let buf = stream.read(buf_len)?;
                Some(buf.into())
            }
            FieldType::String => {
                let buf_len = num.try_into().ok()?;
                let buf = stream.read(buf_len)?;
                // TODO: decode to str
                Some(buf.into())
            }
            FieldType::Enum(enum_type) => {
                let enum_val = num.try_into().ok()?;
                if enum_type.values.contains(&enum_val) {
                    Some(enum_val.try_into().ok()?)
                } else {
                    None
                }
            }
            FieldType::Msg(msg_type) => {
                let msg_len = num.try_into().ok()?;
                let sub_stream = &mut stream.slice(msg_len)?;
                self.decode_message(sub_stream, &msg_type)
            }
        }
    }
}

fn to_signed(uint: u64) -> i64 {
    let sign = uint & 1;
    let val = uint >> 1;
    if sign != 0 {
        !val as i64
    } else {
        val as i64
    }
}

pub struct InputStream<'a> {
    buf: &'a [u8],
    pos: usize,
}

impl<'a> InputStream<'a> {
    pub fn new(buf: &'a [u8]) -> Self {
        Self { buf, pos: 0 }
    }

    pub fn slice(&mut self, len: usize) -> Option<Self> {
        let buf = self.buf.get(self.pos..self.pos + len)?;
        self.pos += len;
        Some(Self::new(buf))
    }

    pub fn read(&mut self, len: usize) -> Option<&[u8]> {
        let buf = self.buf.get(self.pos..self.pos + len)?;
        self.pos += len;
        Some(buf)
    }

    pub fn read_byte(&mut self) -> Option<u8> {
        let val = self.buf.get(self.pos).copied()?;
        self.pos += 1;
        Some(val)
    }

    pub fn read_uvarint(&mut self) -> Option<u64> {
        let mut res = 0;
        let mut byte = 0x80;
        let mut shift = 0;
        while byte & 0x80 != 0 {
            byte = self.read_byte()?;
            res += (byte as u64 & 0x7F) << shift;
            shift += 7;
        }
        Some(res)
    }
}
