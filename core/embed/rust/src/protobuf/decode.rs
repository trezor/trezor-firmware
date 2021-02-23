use core::convert::{TryFrom, TryInto};
use core::str;

use crate::{
    error::Error,
    micropython::{buffer::Buffer, dict::Dict, gc::Gc, list::List, obj::Obj, qstr::Qstr},
    util,
};

use super::{
    defs::{self, FieldDef, FieldType, MsgDef},
    zigzag,
};

#[no_mangle]
pub extern "C" fn protobuf_decode(buf: Obj, wire_id: Obj) -> Obj {
    util::try_or_none(|| {
        let wire_id = wire_id.try_into()?;
        let msg = MsgDef::for_wire_id(wire_id).ok_or(Error::Missing)?;
        let buf = Buffer::try_from(buf)?;
        let mut stream = InputStream::new(&buf);
        let decoder = Decoder {
            enable_experimental: false,
        };
        let obj = decoder.decode_message(&mut stream, &msg)?;
        Ok(obj)
    })
}

pub struct Decoder {
    pub enable_experimental: bool,
}

impl Decoder {
    pub fn decode_message(&self, stream: &mut InputStream, msg: &MsgDef) -> Result<Obj, Error> {
        // Allocate the backing dict with enough pre-allocated space for all fields.
        let dict = Dict::alloc_with_capacity(msg.fields.len());

        // Decode fields one-by-one from the input stream.
        loop {
            let field_key = match stream.read_uvarint() {
                Ok(key) => key,
                Err(_) => break, // End of stream.
            };
            let field_tag = u8::try_from(field_key >> 3)?;
            let wire_type = u8::try_from(field_key & 7)?;

            match msg.field(field_tag) {
                Some(field) => {
                    let field_value = self.decode_field(stream, field)?;
                    let field_name = Qstr::from(field.name);
                    if field.is_repeated() {
                        // Repeated field, values are stored in a list. First, look up the list
                        // object. If it exists, append to it. If it doesn't, create a new list with
                        // this field's value and assign it.
                        if let Ok(obj) = dict.map().get(field_name) {
                            let list = Gc::<List>::try_from(obj)?;
                            // SAFETY: There are not any other refs into `list`.
                            unsafe {
                                list.append(field_value);
                            }
                        } else {
                            let list = List::alloc(&[field_value]);
                            // SAFETY: There are not any other refs into `dict.map()`.
                            unsafe {
                                dict.map().set(field_name, list);
                            }
                        }
                    } else {
                        // SAFETY: There are not any other refs into `dict.map()`.
                        // Singular field, assign the value directly.
                        unsafe {
                            dict.map().set(field_name, field_value);
                        }
                    }
                }
                None => {
                    // Unknown field, skip it.
                    match wire_type {
                        defs::WIRE_TYPE_VARINT => {
                            stream.read_uvarint()?;
                        }
                        defs::WIRE_TYPE_LENGTH_DELIMITED => {
                            let num = stream.read_uvarint()?;
                            let len = num.try_into()?;
                            stream.read(len)?;
                        }
                        _ => {
                            return Err(Error::InvalidType);
                        }
                    }
                }
            }
        }

        // Fill in the default values by decoding them from the default stream. Only
        // singular fields are allowed to have a default value, this is enforced
        // in the blob compilation.
        let default_stream = &mut InputStream::new(msg.defaults);
        loop {
            // Because we are sure that our field tags fit in one byte, and because this is
            // a trusted stream, we encode the field tag directly as u8, without the wire
            // type.
            let field_tag = match default_stream.read_byte() {
                Ok(tag) => tag,
                Err(_) => break, // End of stream.
            };
            let field = msg.field(field_tag).ok_or(Error::Missing)?;
            let field_name = Qstr::from(field.name);
            if dict.map().contains_key(field_name) {
                // Field already has a value assigned, skip it.
                match field.get_type().wire_type() {
                    defs::WIRE_TYPE_VARINT => {
                        stream.read_uvarint()?;
                    }
                    defs::WIRE_TYPE_LENGTH_DELIMITED => {
                        let num = stream.read_uvarint()?;
                        let len = num.try_into()?;
                        stream.read(len)?;
                    }
                    _ => {
                        return Err(Error::InvalidType);
                    }
                }
            } else {
                // Decode the value and assign it.
                let field_value = self.decode_field(default_stream, field)?;
                // SAFETY: There are not any other refs into `dict.map()`.
                unsafe {
                    dict.map().set(field_name, field_value);
                }
            }
        }

        // Walk the fields again and make sure that all required fields are assigned and
        // all optional missing fields are set to None.
        for field in msg.fields {
            let field_name = Qstr::from(field.name);
            if dict.map().contains_key(field_name) {
                // Field is assigned.
            } else {
                if field.is_required() {
                    // Required field is missing, abort.
                    return Err(Error::Missing);
                } else {
                    // Optional field, set to None.
                    // SAFETY: There are not any other refs into `dict.map()`.
                    unsafe {
                        dict.map().set(field_name, Obj::const_none());
                    }
                }
            }
        }

        Ok(dict.into())
    }

    pub fn decode_field(&self, stream: &mut InputStream, field: &FieldDef) -> Result<Obj, Error> {
        if field.is_experimental() && !self.enable_experimental {
            return Err(Error::InvalidType);
        }
        let num = stream.read_uvarint()?;
        match field.get_type() {
            FieldType::UVarInt => Ok(num.into()),
            FieldType::SVarInt => {
                let signed_int = zigzag::to_signed(num);
                Ok(signed_int.into())
            }
            FieldType::Bool => {
                let boolean = num != 0;
                Ok(boolean.into())
            }
            FieldType::Bytes => {
                let buf_len = num.try_into()?;
                let buf = stream.read(buf_len)?;
                Ok(buf.into())
            }
            FieldType::String => {
                let buf_len = num.try_into()?;
                let buf = stream.read(buf_len)?;
                let unicode = str::from_utf8(buf).map_err(|_| Error::InvalidType)?;
                Ok(unicode.into())
            }
            FieldType::Enum(enum_type) => {
                let enum_val = num.try_into()?;
                if enum_type.values.contains(&enum_val) {
                    Ok(enum_val.into())
                } else {
                    Err(Error::InvalidType)
                }
            }
            FieldType::Msg(msg_type) => {
                let msg_len = num.try_into()?;
                let sub_stream = &mut stream.read_stream(msg_len)?;
                self.decode_message(sub_stream, &msg_type)
            }
        }
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

    pub fn read_stream(&mut self, len: usize) -> Result<Self, Error> {
        let buf = self
            .buf
            .get(self.pos..self.pos + len)
            .ok_or(Error::Missing)?;
        self.pos += len;
        Ok(Self::new(buf))
    }

    pub fn read(&mut self, len: usize) -> Result<&[u8], Error> {
        let buf = self
            .buf
            .get(self.pos..self.pos + len)
            .ok_or(Error::Missing)?;
        self.pos += len;
        Ok(buf)
    }

    pub fn read_byte(&mut self) -> Result<u8, Error> {
        let val = self.buf.get(self.pos).copied().ok_or(Error::Missing)?;
        self.pos += 1;
        Ok(val)
    }

    pub fn read_uvarint(&mut self) -> Result<u64, Error> {
        let mut uint = 0;
        let mut shift = 0;
        loop {
            let byte = self.read_byte()?;
            uint += (byte as u64 & 0x7F) << shift;
            shift += 7;
            if byte & 0x80 == 0 {
                break;
            }
        }
        Ok(uint)
    }
}
