use core::convert::{TryFrom, TryInto};
use core::str;

use crate::{
    error::Error,
    micropython::{buffer::Buffer, dict::Dict, gc::Gc, list::List, map::Map, obj::Obj, qstr::Qstr},
    util::{self},
};

use super::{
    defs::{self, FieldDef, FieldType, MsgDef},
    zigzag,
};

#[no_mangle]
pub extern "C" fn protobuf_new(n_args: usize, args: *const Obj, kwargs: *const Map) -> Obj {
    util::try_with_args_and_kwargs(n_args, args, kwargs, |args, kwargs| {
        let msg_name = args.get(0).copied().ok_or(Error::Missing)?;
        let msg_name = Qstr::try_from(msg_name)?;
        let msg = MsgDef::for_name(msg_name.to_u16()).ok_or(Error::Missing)?;
        let decoder = Decoder {
            enable_experimental: false,
        };
        let obj = decoder.message_from_values(kwargs, &msg)?;
        Ok(obj)
    })
}

#[no_mangle]
pub extern "C" fn protobuf_decode(buf: Obj, wire_id: Obj) -> Obj {
    util::try_or_none(|| {
        let wire_id = wire_id.try_into()?;
        let msg = MsgDef::for_wire_id(wire_id).ok_or(Error::Missing)?;
        let buf = Buffer::try_from(buf)?;
        let stream = &mut InputStream::new(&buf);
        let decoder = Decoder {
            enable_experimental: false,
        };
        let obj = decoder.message_from_stream(stream, &msg)?;
        Ok(obj)
    })
}

pub struct Decoder {
    pub enable_experimental: bool,
}

impl Decoder {
    /// Create a new message instance and decode `stream` into it, handling the
    /// default and required fields correctly.
    pub fn message_from_stream(
        &self,
        stream: &mut InputStream,
        msg: &MsgDef,
    ) -> Result<Obj, Error> {
        let mut dict = self.empty_message(msg);
        // SAFETY: We assume that `dict` is not alised here.
        let map = unsafe { dict.as_mut() }.map_mut();
        self.decode_fields_into(stream, msg, map)?;
        self.decode_defaults_into(msg, map)?;
        self.assign_required_into(msg, map)?;
        Ok(dict.into())
    }

    /// Create a new message instance and fill it from `values`, handling the
    /// default and required fields correctly.
    pub fn message_from_values(&self, values: &Map, msg: &MsgDef) -> Result<Obj, Error> {
        let mut dict = self.empty_message(msg);
        // SAFETY: We assume that `dict` is not alised here.
        let map = unsafe { dict.as_mut() }.map_mut();
        for elem in values.elems() {
            map.set(elem.key, elem.value);
        }
        self.decode_defaults_into(msg, map)?;
        self.assign_required_into(msg, map)?;
        Ok(dict.into())
    }

    /// Allocate the backing dict with enough pre-allocated space for all
    /// fields.
    pub fn empty_message(&self, msg: &MsgDef) -> Gc<Dict> {
        Dict::alloc_with_capacity(msg.fields.len())
    }

    /// Decode message fields one-by-one from the input stream, assigning them
    /// into `map`.
    pub fn decode_fields_into(
        &self,
        stream: &mut InputStream,
        msg: &MsgDef,
        map: &mut Map,
    ) -> Result<(), Error> {
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
                        if let Ok(obj) = map.get(field_name) {
                            let mut list = Gc::<List>::try_from(obj)?;
                            // SAFETY: We assume that `list` is not aliased here.
                            unsafe { list.as_mut() }.append(field_value);
                        } else {
                            let list = List::alloc(&[field_value]);
                            map.set(field_name, list);
                        }
                    } else {
                        // Singular field, assign the value directly.
                        map.set(field_name, field_value);
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
        Ok(())
    }

    /// Fill in the default values by decoding them from the default stream.
    /// Only singular fields are allowed to have a default value, this is
    /// enforced in the blob compilation.
    pub fn decode_defaults_into(&self, msg: &MsgDef, map: &mut Map) -> Result<(), Error> {
        let stream = &mut InputStream::new(msg.defaults);
        loop {
            // Because we are sure that our field tags fit in one byte, and because this is
            // a trusted stream, we encode the field tag directly as u8, without the wire
            // type.
            let field_tag = match stream.read_byte() {
                Ok(tag) => tag,
                Err(_) => break, // End of stream.
            };
            let field = msg.field(field_tag).ok_or(Error::Missing)?;
            let field_name = Qstr::from(field.name);
            if map.contains_key(field_name) {
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
                let field_value = self.decode_field(stream, field)?;
                map.set(field_name, field_value);
            }
        }
        Ok(())
    }

    /// Walk the fields definitions and make sure that all required fields are
    /// assigned and all optional missing fields are set to `None`.
    pub fn assign_required_into(&self, msg: &MsgDef, map: &mut Map) -> Result<(), Error> {
        for field in msg.fields {
            let field_name = Qstr::from(field.name);
            if map.contains_key(field_name) {
                // Field is assigned.
            } else {
                if field.is_required() {
                    // Required field is missing, abort.
                    return Err(Error::Missing);
                } else {
                    // Optional field, set to None.
                    map.set(field_name, Obj::const_none());
                }
            }
        }
        Ok(())
    }

    /// Decode one field value from the input stream.
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
                self.message_from_stream(sub_stream, &msg_type)
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
