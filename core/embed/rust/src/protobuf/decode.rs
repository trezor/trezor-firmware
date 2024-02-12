use core::{
    convert::{TryFrom, TryInto},
    str,
};

use crate::{
    error::Error,
    micropython::{buffer, gc::Gc, list::List, map::Map, obj::Obj, qstr::Qstr, util},
};

use super::{
    defs::{self, FieldDef, FieldType, MsgDef},
    error,
    obj::{MsgDefObj, MsgObj},
    zigzag,
};

pub extern "C" fn protobuf_decode(buf: Obj, msg_def: Obj, enable_experimental: Obj) -> Obj {
    let block = || {
        let def = Gc::<MsgDefObj>::try_from(msg_def)?;
        let enable_experimental = bool::try_from(enable_experimental)?;

        if !enable_experimental && def.msg().is_experimental {
            // Refuse to decode message defs marked as experimental if not
            // explicitly allowed. Messages can also mark certain fields as
            // experimental (not the whole message). This is enforced during the
            // decoding.
            return Err(error::experimental_not_enabled());
        }

        // SAFETY:
        // We assume that for the lifetime of `buf`, no MicroPython code can run that
        // would mutate the buffer, nor pass it to another Rust function.
        let buf = unsafe { buffer::get_buffer(buf) }?;
        let stream = &mut InputStream::new(buf);
        let decoder = Decoder {
            enable_experimental,
        };

        let obj = decoder.message_from_stream(stream, def.msg())?;
        Ok(obj)
    };
    unsafe { util::try_or_raise(block) }
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
        let mut obj = self.empty_message(msg)?;
        // SAFETY: We assume that `obj` is not aliased here.
        let map = unsafe { Gc::as_mut(&mut obj) }.map_mut();
        self.decode_fields_into(stream, msg, map)?;
        self.decode_defaults_into(msg, map)?;
        self.assign_required_into(msg, map)?;
        Ok(obj.into())
    }

    /// Create a new message instance and fill it from `values`, handling the
    /// default and required fields correctly.
    pub fn message_from_values(&self, values: &Map, msg: &MsgDef) -> Result<Obj, Error> {
        let mut obj = self.empty_message(msg)?;
        // SAFETY: We assume that `obj` is not aliased here.
        let map = unsafe { Gc::as_mut(&mut obj) }.map_mut();
        for elem in values.elems() {
            map.set(elem.key, elem.value)?;
        }
        self.decode_defaults_into(msg, map)?;
        self.assign_required_into(msg, map)?;
        Ok(obj.into())
    }

    /// Allocate the backing message object with enough pre-allocated space for
    /// all fields.
    pub fn empty_message(&self, msg: &MsgDef) -> Result<Gc<MsgObj>, Error> {
        MsgObj::alloc_with_capacity(msg.fields.len(), msg)
    }

    /// Decode message fields one-by-one from the input stream, assigning them
    /// into `map`.
    fn decode_fields_into(
        &self,
        stream: &mut InputStream,
        msg: &MsgDef,
        map: &mut Map,
    ) -> Result<(), Error> {
        // Loop, trying to read the field key that contains the tag and primitive value
        // type. If we fail to read the key, we are at the end of the stream.
        while let Ok(field_key) = stream.read_uvarint_u32() {
            let field_tag = u8::try_from(field_key >> 3)?;
            let prim_type = u8::try_from(field_key & 7)?;

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
                            // SAFETY: We assume that `list` is not aliased here. This holds for
                            // uses in `message_from_stream` and `message_from_values`, because we
                            // start with an empty `Map` and fill with unique lists.
                            unsafe { Gc::as_mut(&mut list) }.append(field_value)?;
                        } else {
                            let list = List::alloc(&[field_value])?;
                            map.set(field_name, list)?;
                        }
                    } else {
                        // Singular field, assign the value directly.
                        map.set(field_name, field_value)?;
                    }
                }
                None => {
                    // Unknown field, skip it.
                    match prim_type {
                        defs::PRIMITIVE_TYPE_VARINT => {
                            stream.read_uvarint_u64()?;
                        }
                        defs::PRIMITIVE_TYPE_LENGTH_DELIMITED => {
                            let num = stream.read_uvarint_u32()?;
                            let len = num.try_into()?;
                            stream.read(len)?;
                        }
                        _ => {
                            return Err(error::unknown_field_type());
                        }
                    }
                }
            }
        }
        Ok(())
    }

    /// Fill in the default values by decoding them from the defaults stream.
    /// Only singular fields are allowed to have a default value, this is
    /// enforced in the blob compilation.
    fn decode_defaults_into(&self, msg: &MsgDef, map: &mut Map) -> Result<(), Error> {
        let stream = &mut InputStream::new(msg.defaults);

        // The format of the defaults stream is a sequence of records:
        //  - one-byte field tag (without the primitive type).
        //  - Protobuf-encoded default value.
        // We need to look to the field descriptor to know how to interpret the value
        // after the field tag.
        while let Ok(field_tag) = stream.read_byte() {
            let field = msg
                .field(field_tag)
                .ok_or_else(|| Error::KeyError(field_tag.into()))?;
            let field_name = Qstr::from(field.name);
            if map.contains_key(field_name) {
                // Field already has a value assigned, skip it.
                match field.get_type().primitive_type() {
                    defs::PRIMITIVE_TYPE_VARINT => {
                        stream.read_uvarint_u64()?;
                    }
                    defs::PRIMITIVE_TYPE_LENGTH_DELIMITED => {
                        let num = stream.read_uvarint_u32()?;
                        let len = num.try_into()?;
                        stream.read(len)?;
                    }
                    _ => {
                        return Err(error::unknown_field_type());
                    }
                }
            } else {
                // Decode the value and assign it.
                let field_value = self.decode_field(stream, field)?;
                map.set(field_name, field_value)?;
            }
        }
        Ok(())
    }

    /// Walk the fields definitions and make sure that all required fields are
    /// assigned and all optional missing fields are set to `None`.
    fn assign_required_into(&self, msg: &MsgDef, map: &mut Map) -> Result<(), Error> {
        for field in msg.fields {
            let field_name = Qstr::from(field.name);
            if map.contains_key(field_name) {
                // Field is assigned, skip.
                continue;
            }
            if field.is_required() {
                // Required field is missing, abort.
                return Err(error::missing_required_field(field_name));
            }
            if field.is_repeated() {
                // Optional repeated field, set to a new empty list.
                map.set(field_name, List::alloc(&[])?)?;
            } else {
                // Optional singular field, set to None.
                map.set(field_name, Obj::const_none())?;
            }
        }
        Ok(())
    }

    /// Decode one field value from the input stream.
    fn decode_field(&self, stream: &mut InputStream, field: &FieldDef) -> Result<Obj, Error> {
        if field.is_experimental() && !self.enable_experimental {
            return Err(error::experimental_not_enabled());
        }

        match field.get_type() {
            FieldType::UVarInt32 => {
                let num = stream.read_uvarint_u32()?;
                Ok(num.try_into()?)
            }
            FieldType::UVarInt64 => {
                let num = stream.read_uvarint_u64()?;
                Ok(num.try_into()?)
            }
            FieldType::SVarInt => {
                let num = stream.read_uvarint_u64()?;
                let signed_int = zigzag::to_signed(num);
                Ok(signed_int.try_into()?)
            }
            FieldType::Bool => {
                let boolean = stream.read_uvarint_u32()? != 0;
                Ok(boolean.into())
            }
            FieldType::Bytes => {
                let num = stream.read_uvarint_u64()?;
                let buf_len = num.try_into()?;
                let buf = stream.read(buf_len)?;
                buf.try_into()
            }
            FieldType::String => {
                let num = stream.read_uvarint_u64()?;
                let buf_len = num.try_into()?;
                let buf = stream.read(buf_len)?;
                let unicode =
                    str::from_utf8(buf).map_err(|_| error::invalid_value(field.name.into()))?;
                unicode.try_into()
            }
            FieldType::Enum(enum_type) => {
                let num = stream.read_uvarint_u32()?;
                let enum_val = num.try_into()?;
                if enum_type.values.contains(&enum_val) {
                    Ok(enum_val.into())
                } else {
                    Err(error::invalid_value(field.name.into()))
                }
            }
            FieldType::Msg(msg_type) => {
                let num = stream.read_uvarint_u64()?;
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
            .ok_or_else(error::end_of_buffer)?;
        self.pos += len;
        Ok(Self::new(buf))
    }

    pub fn read(&mut self, len: usize) -> Result<&[u8], Error> {
        let buf = self
            .buf
            .get(self.pos..self.pos + len)
            .ok_or_else(error::end_of_buffer)?;
        self.pos += len;
        Ok(buf)
    }

    pub fn read_byte(&mut self) -> Result<u8, Error> {
        let val = self
            .buf
            .get(self.pos)
            .copied()
            .ok_or_else(error::end_of_buffer)?;
        self.pos += 1;
        Ok(val)
    }

    pub fn read_uvarint_u32(&mut self) -> Result<u32, Error> {
        let mut uint: u32 = 0;
        let mut shift = 0;
        for byte_count in 1..=5 {
            let byte: u32 = self.read_byte()? as u32;
            let payload = byte & 0x7F;
            if byte_count == 5 && payload > 0xF {
                // NB: the 5th byte is only accepted it it contains no more than 4 payload bits (4 x 7 + 4 = 32 bits)!
                break;
            }
            uint += payload << shift;
            shift += 7;
            if byte & 0x80 == 0 {
                return Ok(uint);
            }
        }

        Err(Error::OutOfRange)
    }

    pub fn read_uvarint_u64(&mut self) -> Result<u64, Error> {
        let mut uint: u64 = 0;
        let mut shift = 0;
        for byte_count in 1..=10 {
            let byte: u64 = self.read_byte()? as u64;
            let payload = byte & 0x7F;
            if byte_count == 10 && payload > 1 {
                // NB: the 10th byte is only accepted it it contains no more than 1 payload bit (9 x 7 + 1 = 64 bits)!
                break;
            }
            uint += payload << shift;
            shift += 7;
            if byte & 0x80 == 0 {
                return Ok(uint);
            }
        }

        Err(Error::OutOfRange)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn read_uvarint_32() {
        // 1 byte...
        let mut stream = InputStream::new(&[0b00000001]);
        assert!(matches!(stream.read_uvarint_u32(), Ok(1)));

        // 2 bytes...
        let mut stream = InputStream::new(&[0b10010110, 0b00000001]);
        assert!(matches!(stream.read_uvarint_u32(), Ok(150)));

        // a 0 taking up 5 whole bytes...
        let mut stream = InputStream::new(&[0b10000000, 0b10000000, 0b10000000, 0b10000000, 0b00000000]);
        assert!(matches!(stream.read_uvarint_u32(), Ok(0)));

        // 5 bytes, with only 4 bits used in the last byte... still OK!
        let mut stream = InputStream::new(&[0b10000000, 0b10000000, 0b10000000, 0b10000000, 0b00001111]);
        assert!(matches!(stream.read_uvarint_u32(), Ok(0xF0000000)));

        // 5 bytes with more than 4 bits used in the last byte => overflow
        let mut stream = InputStream::new(&[0b10000000, 0b10000000, 0b10000000, 0b10000000, 0b00010000]);
        assert!(stream.read_uvarint_u32().is_err());

        // 5+ bytes => overflow
        let mut stream = InputStream::new(&[0b10000000, 0b10000000, 0b10000000, 0b10000000, 0b10000000, 0b00000001]);
        assert!(stream.read_uvarint_u32().is_err());

        // although the same number as above fits well on 64 bit
        let mut stream = InputStream::new(&[0b10000000, 0b10000000, 0b10000000, 0b10000000, 0b10000000, 0b00000001]);
        assert!(matches!(stream.read_uvarint_u64(), Ok(0x800000000)));
    }

    #[test]
    fn read_uvarint_64() {
        // 1 byte...
        let mut stream = InputStream::new(&[0b00000001]);
        assert!(matches!(stream.read_uvarint_u64(), Ok(1)));

        // 2 bytes...
        let mut stream = InputStream::new(&[0b10010110, 0b00000001]);
        assert!(matches!(stream.read_uvarint_u64(), Ok(150)));

        // 5 bytes, with more than 4 bits used in the last byte => works fine for u64!
        let mut stream = InputStream::new(&[0b10000000, 0b10000000, 0b10000000, 0b10000000, 0b00010000]);
        assert!(matches!(stream.read_uvarint_u64(), Ok(0x100000000)));

        // 10 bytes with just a single bit in the last one
        let mut stream = InputStream::new(&[0b10000000, 0b10000000, 0b10000000, 0b10000000, 0b10000000, 0b10000000, 0b10000000, 0b10000000, 0b10000000, 0b00000001]);
        assert!(matches!(stream.read_uvarint_u64(), Ok(0x8000000000000000)));

        // 10 bytes and the number is still not complete => too much ... even if so far all we got is zeroes!
        let mut stream = InputStream::new(&[0b10000000, 0b10000000, 0b10000000, 0b10000000, 0b10000000, 0b10000000, 0b10000000, 0b10000000, 0b10000000, 0b10000000]);
        assert!(stream.read_uvarint_u64().is_err());

        // 10 bytes with more than a bit used in the last one => too much for u64!
        let mut stream = InputStream::new(&[0b10000000, 0b10000000, 0b10000000, 0b10000000, 0b10000000, 0b10000000, 0b10000000, 0b10000000, 0b10000000, 0b00000010]);
        assert!(stream.read_uvarint_u64().is_err());
    }
}
