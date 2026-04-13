use core::{
    convert::{TryFrom, TryInto},
    str,
};

use micropython::{
    buffer, error::Error, gc::Gc, list::List, map::Map, obj::Obj, py_object::GcObject, util,
};

use crate::io::InputStream;

use super::{
    defs::{self, FieldDef, FieldType, MsgDef},
    error,
    obj::MsgObj,
    zigzag,
};

pub extern "C" fn protobuf_decode(buf: Obj, msg_def: Obj, enable_experimental: Obj) -> Obj {
    let block = || {
        let def = GcObject::<MsgDef>::try_from(msg_def)?;
        let def = def.borrow();
        let enable_experimental = bool::try_from(enable_experimental)?;

        if !enable_experimental && def.is_experimental {
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

        let obj = decoder.message_from_stream(stream, &def)?;
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
    pub(crate) fn message_from_stream(
        &self,
        stream: &mut InputStream,
        msg: &MsgDef,
    ) -> Result<Obj, Error> {
        let obj = self.empty_message(msg)?;
        // SAFETY: We assume that `obj` is not aliased here.
        {
            let mut obj_mut = obj.borrow_mut();
            let map = obj_mut.map_mut();
            self.decode_fields_into(stream, msg, map)?;
            self.decode_defaults_into(msg, map)?;
            self.assign_required_into(msg, map)?;
        }
        Ok(obj.into())
    }

    /// Create a new message instance and fill it from `values`, handling the
    /// default and required fields correctly.
    pub(crate) fn message_from_values(&self, values: &Map, msg: &MsgDef) -> Result<Obj, Error> {
        let obj = self.empty_message(msg)?;
        // SAFETY: We assume that `obj` is not aliased here.
        {
            let mut obj_mut = obj.borrow_mut();
            let map = obj_mut.map_mut();
            for elem in values.elems() {
                map.set(elem.key, elem.value)?;
            }
            self.decode_defaults_into(msg, map)?;
            self.assign_required_into(msg, map)?;
        }
        Ok(obj.into())
    }

    /// Allocate the backing message object with enough pre-allocated space for
    /// all fields.
    pub(crate) fn empty_message(&self, msg: &MsgDef) -> Result<GcObject<MsgObj>, Error> {
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
        while let Ok(field_key) = stream.read_uvarint() {
            let field_tag = u8::try_from(field_key >> 3)?;
            let prim_type = u8::try_from(field_key & 7)?;

            match msg.field(field_tag) {
                Some(field) if field.get_type().primitive_type() != prim_type => {
                    return Err(error::invalid_value(field.name()));
                }
                Some(field) => {
                    let field_value = self.decode_field(stream, field)?;
                    if field.is_repeated() {
                        // Repeated field, values are stored in a list. First, look up the list
                        // object. If it exists, append to it. If it doesn't, create a new list with
                        // this field's value and assign it.
                        if let Ok(obj) = map.get(field.name()) {
                            let mut list = Gc::<List>::try_from(obj)?;
                            // SAFETY: We assume that `list` is not aliased here. This holds for
                            // uses in `message_from_stream` and `message_from_values`, because we
                            // start with an empty `Map` and fill with unique lists.
                            unsafe { Gc::as_mut(&mut list) }.append(field_value)?;
                        } else {
                            let list = List::alloc(&[field_value])?;
                            map.set(field.name(), list)?;
                        }
                    } else {
                        // Singular field, assign the value directly.
                        map.set(field.name(), field_value)?;
                    }
                }
                None => {
                    // Unknown field, skip it.
                    match prim_type {
                        defs::PRIMITIVE_TYPE_VARINT => {
                            stream.read_uvarint()?;
                        }
                        defs::PRIMITIVE_TYPE_LENGTH_DELIMITED => {
                            let num = stream.read_uvarint()?;
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
    pub(crate) fn decode_defaults_into(&self, msg: &MsgDef, map: &mut Map) -> Result<(), Error> {
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
            if map.contains_key(field.name()) {
                // Field already has a value assigned, skip it.
                match field.get_type().primitive_type() {
                    defs::PRIMITIVE_TYPE_VARINT => {
                        stream.read_uvarint()?;
                    }
                    defs::PRIMITIVE_TYPE_LENGTH_DELIMITED => {
                        let num = stream.read_uvarint()?;
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
                map.set(field.name(), field_value)?;
            }
        }
        Ok(())
    }

    /// Walk the fields definitions and make sure that all required fields are
    /// assigned and all optional missing fields are set to `None`.
    pub(crate) fn assign_required_into(&self, msg: &MsgDef, map: &mut Map) -> Result<(), Error> {
        for field in msg.fields {
            if map.contains_key(field.name()) {
                // Field is assigned, skip.
                continue;
            }
            if field.is_required() {
                // Required field is missing, abort.
                return Err(error::missing_required_field(field.name()));
            }
            if field.is_repeated() {
                // Optional repeated field, set to a new empty list.
                map.set(field.name(), List::alloc(&[])?)?;
            } else {
                // Optional singular field, set to None.
                map.set(field.name(), Obj::const_none())?;
            }
        }
        Ok(())
    }

    /// Decode one field value from the input stream.
    pub(crate) fn decode_field(
        &self,
        stream: &mut InputStream,
        field: &FieldDef,
    ) -> Result<Obj, Error> {
        if field.is_experimental() && !self.enable_experimental {
            return Err(error::experimental_not_enabled());
        }
        let num = stream.read_uvarint()?;
        match field.get_type() {
            FieldType::UVarInt | FieldType::UVarInt64 => Ok(num.try_into()?),
            FieldType::SVarInt | FieldType::SVarInt64 => {
                let signed_int = zigzag::to_signed(num);
                Ok(signed_int.try_into()?)
            }
            FieldType::Bool => {
                let boolean = num != 0;
                Ok(boolean.into())
            }
            FieldType::Bytes => {
                let buf_len = num.try_into()?;
                let buf = stream.read(buf_len)?;
                buf.try_into()
            }
            FieldType::String => {
                let buf_len = num.try_into()?;
                let buf = stream.read(buf_len)?;
                let unicode =
                    str::from_utf8(buf).map_err(|_| error::invalid_value(field.name()))?;
                unicode.try_into()
            }
            FieldType::Enum(enum_type) => {
                let enum_val = num.try_into()?;
                enum_type
                    .into_obj(enum_val)
                    .map_err(|_| error::invalid_value(field.name()))
            }
            FieldType::Msg(msg_type) => {
                let msg_len = num.try_into()?;
                let sub_stream = &mut stream.read_stream(msg_len)?;
                self.message_from_stream(sub_stream, &msg_type)
            }
        }
    }
}

impl defs::EnumDef {
    pub fn into_obj(&self, value: u16) -> Result<Obj, ()> {
        if self.values.contains(&value) {
            Ok(value.into())
        } else {
            Err(())
        }
    }
}
