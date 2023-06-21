use core::convert::{TryFrom, TryInto};

use crate::{
    error::Error,
    micropython::{buffer, gc::Gc, iter::IterBuf, list::List, obj::Obj, qstr::Qstr, util},
};

use super::{
    defs::{FieldDef, FieldType, MsgDef},
    error,
    obj::MsgObj,
    zigzag,
};

#[no_mangle]
pub extern "C" fn protobuf_len(obj: Obj) -> Obj {
    let block = || {
        let obj = Gc::<MsgObj>::try_from(obj)?;
        let stream = &mut CounterStream { len: 0 };
        Encoder.encode_message(stream, &obj.def(), &obj)?;
        stream.len.try_into()
    };
    unsafe { util::try_or_raise(block) }
}

#[no_mangle]
pub extern "C" fn protobuf_encode(buf: Obj, obj: Obj) -> Obj {
    let block = || {
        let obj = Gc::<MsgObj>::try_from(obj)?;

        // SAFETY:
        // We assume that:
        //  - there are no other refs into `buf` at this point. This specifically means
        //    that no fields of `obj` should reference `buf` memory.
        //  - for the lifetime of `buf`, no Python code will mutate the contents.
        let buf = unsafe { buffer::get_buffer_mut(buf)? };
        let stream = &mut BufferStream::new(buf);

        Encoder.encode_message(stream, &obj.def(), &obj)?;

        stream.len().try_into()
    };
    unsafe { util::try_or_raise(block) }
}

pub struct Encoder;

impl Encoder {
    pub fn encode_message(
        &self,
        stream: &mut impl OutputStream,
        msg: &MsgDef,
        obj: &MsgObj,
    ) -> Result<(), Error> {
        for field in msg.fields {
            let field_name = Qstr::from(field.name);

            // Lookup the field by name. If not set or None, skip.
            let field_value = match obj.map().get(field_name) {
                Ok(value) => value,
                Err(_) => continue,
            };
            if field_value == Obj::const_none() {
                continue;
            }

            let field_key = {
                let prim_type = field.get_type().primitive_type();
                let prim_type = prim_type as u64;
                let field_tag = field.tag as u64;
                field_tag << 3 | prim_type
            };

            if field.is_repeated() {
                for iter_value in IterBuf::new().try_iterate(field_value)? {
                    stream.write_uvarint(field_key)?;
                    self.encode_field(stream, field, iter_value)?;
                }
            } else {
                stream.write_uvarint(field_key)?;
                self.encode_field(stream, field, field_value)?;
            }
        }

        Ok(())
    }

    pub fn encode_field(
        &self,
        stream: &mut impl OutputStream,
        field: &FieldDef,
        value: Obj,
    ) -> Result<(), Error> {
        match field.get_type() {
            FieldType::UVarInt | FieldType::Enum(_) => {
                let uint = u64::try_from(value)?;
                stream.write_uvarint(uint)?;
            }
            FieldType::SVarInt => {
                let sint = i64::try_from(value)?;
                let uint = zigzag::to_unsigned(sint);
                stream.write_uvarint(uint)?;
            }
            FieldType::Bool => {
                let boolean = bool::try_from(value)?;
                let uint = if boolean { 1 } else { 0 };
                stream.write_uvarint(uint)?;
            }
            FieldType::Bytes | FieldType::String => {
                if Gc::<List>::try_from(value).is_ok() {
                    // As an optimization, we support defining bytes and string
                    // fields also as a list-of-values. Serialize them as if
                    // concatenated.

                    let mut iter_buf = IterBuf::new();

                    // Serialize the total length of the buffer.
                    let mut len = 0;
                    for value in iter_buf.try_iterate(value)? {
                        // SAFETY: buffer is dropped immediately.
                        let buffer = unsafe { buffer::get_buffer(value) }?;
                        len += buffer.len();
                    }
                    stream.write_uvarint(len as u64)?;

                    // Serialize the buffers one-by-one.
                    for value in iter_buf.try_iterate(value)? {
                        // SAFETY: buffer is dropped immediately.
                        let buffer = unsafe { buffer::get_buffer(value) }?;
                        stream.write(buffer)?;
                    }
                } else {
                    // Single length-delimited field.
                    // SAFETY: buffer is dropped immediately.
                    let buffer = unsafe { buffer::get_buffer(value) }?;
                    stream.write_uvarint(buffer.len() as u64)?;
                    stream.write(buffer)?;
                }
            }
            FieldType::Msg(msg_type) => {
                let value = &Gc::<MsgObj>::try_from(value)?;
                // Calculate the message size by encoding it through `CountingWriter`.
                let counter = &mut CounterStream { len: 0 };
                self.encode_message(counter, &msg_type, value)?;

                // Encode the message as length-delimited bytes.
                stream.write_uvarint(counter.len as u64)?;
                self.encode_message(stream, &msg_type, value)?;
            }
        }

        Ok(())
    }
}

pub trait OutputStream {
    fn write(&mut self, buf: &[u8]) -> Result<(), Error>;
    fn write_byte(&mut self, val: u8) -> Result<(), Error>;

    fn write_uvarint(&mut self, mut num: u64) -> Result<(), Error> {
        loop {
            let shifted = num >> 7;
            let byte = (num & 0x7F) as u8;
            if shifted != 0 {
                num = shifted;
                self.write_byte(byte | 0x80)?;
            } else {
                break self.write_byte(byte);
            }
        }
    }
}

pub struct CounterStream {
    pub len: usize,
}

impl OutputStream for CounterStream {
    fn write(&mut self, buf: &[u8]) -> Result<(), Error> {
        self.len += buf.len();
        Ok(())
    }

    fn write_byte(&mut self, _val: u8) -> Result<(), Error> {
        self.len += 1;
        Ok(())
    }
}

pub struct BufferStream<'a> {
    buf: &'a mut [u8],
    pos: usize,
}

impl<'a> BufferStream<'a> {
    pub fn new(buf: &'a mut [u8]) -> Self {
        Self { buf, pos: 0 }
    }

    pub fn len(&self) -> usize {
        self.pos
    }
}

impl<'a> OutputStream for BufferStream<'a> {
    fn write(&mut self, val: &[u8]) -> Result<(), Error> {
        let pos = &mut self.pos;
        let len = val.len();
        self.buf
            .get_mut(*pos..*pos + len)
            .map(|buf| {
                *pos += len;
                buf.copy_from_slice(val);
            })
            .ok_or_else(error::end_of_buffer)
    }

    fn write_byte(&mut self, val: u8) -> Result<(), Error> {
        let pos = &mut self.pos;
        self.buf
            .get_mut(*pos)
            .map(|buf| {
                *pos += 1;
                *buf = val;
            })
            .ok_or_else(error::end_of_buffer)
    }
}
