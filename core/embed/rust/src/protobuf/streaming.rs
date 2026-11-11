//! Schema access and bounded output for the asynchronous service codec. The
//! native decoder remains unchanged: the Python reader allocates only final
//! field values, then uses the same message constructor for required fields and
//! defaults.
use super::defs::FieldType;
use super::encode::{Encoder, OutputStream};
use super::obj::{MsgDefObj, MsgObj};
use crate::micropython::gc::Gc;
use crate::micropython::list::List;
use crate::micropython::qstr::Qstr;
use crate::micropython::{buffer, util, Error, Obj};

pub extern "C" fn field_info(def: Obj, tag: Obj) -> Obj {
    let block = || {
        let def = Gc::<MsgDefObj>::try_from(def)?;
        if def.msg().is_experimental {
            return Err(Error::ValueError(c"experimental service message"));
        }
        let tag = u8::try_from(tag)?;
        let Some(field) = def.msg().field(tag) else {
            return Ok(Obj::const_none());
        };
        if field.is_experimental() {
            return Err(Error::ValueError(c"experimental service field"));
        }
        let (kind, nested): (u8, Obj) = match field.get_type() {
            FieldType::UVarInt32 => (0, Obj::const_none()),
            FieldType::SVarInt32 => (1, Obj::const_none()),
            FieldType::UVarInt64 => (2, Obj::const_none()),
            FieldType::SVarInt64 => (3, Obj::const_none()),
            FieldType::Bool => (4, Obj::const_none()),
            FieldType::Bytes => (5, Obj::const_none()),
            FieldType::String => (6, Obj::const_none()),
            FieldType::Enum(def) => {
                let mut values = List::alloc(&[])?;
                for value in def.values {
                    unsafe { Gc::as_mut(&mut values) }.append((*value).into())?;
                }
                (7, values.into())
            }
            FieldType::Msg(msg) => (8, MsgDefObj::alloc(msg)?.into()),
        };
        (
            Qstr::from(field.name()).to_obj(),
            kind,
            field.is_repeated(),
            nested,
        )
            .try_into()
    };
    unsafe { util::try_or_raise(block) }
}

struct Window<'a> {
    output: &'a mut [u8],
    start: usize,
    position: usize,
    written: usize,
}

impl OutputStream for Window<'_> {
    fn write(&mut self, data: &[u8]) -> Result<(), Error> {
        let first = self.start.saturating_sub(self.position).min(data.len());
        let count = (data.len() - first).min(self.output.len() - self.written);
        self.output[self.written..self.written + count]
            .copy_from_slice(&data[first..first + count]);
        self.position += data.len();
        self.written += count;
        Ok(())
    }
    fn write_byte(&mut self, byte: u8) -> Result<(), Error> {
        self.write(&[byte])
    }
}

pub extern "C" fn encode_range(output: Obj, message: Obj, offset: Obj) -> Obj {
    let block = || {
        let message = Gc::<MsgObj>::try_from(message)?;
        let start = usize::try_from(offset)?;
        // No Python code runs during encoding. The service's report buffer is not
        // stored in a message: decoded bytes fields have their own backing stores.
        let output = unsafe { buffer::get_buffer_mut(output) }?;
        let mut stream = Window {
            output,
            start,
            position: 0,
            written: 0,
        };
        Encoder.encode_message(&mut stream, &message.def(), &message)?;
        stream.written.try_into()
    };
    unsafe { util::try_or_raise(block) }
}
