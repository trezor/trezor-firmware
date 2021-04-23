use core::convert::{TryFrom, TryInto};

use crate::{
    error::Error,
    micropython::{
        dict::Dict,
        ffi,
        gc::Gc,
        map::Map,
        obj::{Obj, ObjBase},
        qstr::Qstr,
        typ::Type,
    },
    util,
};

use super::{decode::Decoder, defs::MsgDef};

#[repr(C)]
pub struct MsgObj {
    base: ObjBase,
    map: Map,
    msg_wire_id: Option<u16>,
    msg_offset: u16,
}

impl MsgObj {
    pub fn alloc_with_capacity(capacity: usize, msg: &MsgDef) -> Gc<Self> {
        Gc::new(Self {
            base: Self::obj_type().to_base(),
            map: Map::with_capacity(capacity),
            msg_wire_id: msg.wire_id,
            msg_offset: msg.offset,
        })
    }

    pub fn map(&self) -> &Map {
        &self.map
    }

    pub fn map_mut(&mut self) -> &mut Map {
        &mut self.map
    }

    fn obj_type() -> &'static Type {
        static TYPE: Type = obj_type! {
            name: Qstr::MP_QSTR_Msg,
            attr_fn: msg_obj_attr,
        };
        &TYPE
    }
}

impl Into<Obj> for Gc<MsgObj> {
    fn into(self) -> Obj {
        // SAFETY:
        //  - We are GC-allocated.
        //  - We are `repr(C)`.
        //  - We have a `base` as the first field with the correct type.
        unsafe { Obj::from_ptr(Self::into_raw(self).cast()) }
    }
}

impl TryFrom<Obj> for Gc<MsgObj> {
    type Error = Error;

    fn try_from(value: Obj) -> Result<Self, Self::Error> {
        if MsgObj::obj_type().is_type_of(value) {
            // SAFETY: We assume that if `value` is an object pointer with the correct type,
            // it is always GC-allocated.
            let this = unsafe { Gc::from_raw(value.as_ptr().cast()) };
            Ok(this)
        } else {
            Err(Error::InvalidType)
        }
    }
}

unsafe extern "C" fn msg_obj_attr(self_in: Obj, attr: ffi::qstr, dest: *mut Obj) {
    let mut this: Gc<MsgObj> = self_in.try_into().unwrap();

    let attr = Qstr::from_u16(attr as _);

    unsafe {
        if dest.read() == Obj::const_null() {
            // Load attribute.
            if let Ok(obj) = this.map.get(attr) {
                // Message field was found, return its value.
                dest.write(obj);
            } else {
                match attr {
                    Qstr::MP_QSTR_MESSAGE_WIRE_TYPE => {
                        // Return the wire ID of this message def, or None if not set.
                        let obj = this
                            .msg_wire_id
                            .map_or_else(Obj::const_none, |wire_id| wire_id.into());
                        dest.write(obj);
                    }
                    Qstr::MP_QSTR___dict__ => {
                        // Conversion to dict. Allocate a new dict object with a copy of our map
                        // and return it. This is a bit different from how uPy does it now, because
                        // we're returning a mutable dict.
                        let dict = Gc::new(Dict::with_map(this.map.clone()));
                        dest.write(dict.into());
                    }
                    _ => {}
                }
            }
        } else {
            let value = dest.offset(1).read();
            if value == Obj::const_null() {
                // Delete atribute.
                this.as_mut().map.delete(attr);
            } else {
                // Store attribute.
                this.as_mut().map.set(attr, value);
            }
            // TODO: Fail if attr does not exist.
            dest.write(Obj::const_null());
        }
    }
}

#[repr(C)]
pub struct MsgDefObj {
    base: ObjBase,
    def: MsgDef,
}

impl MsgDefObj {
    pub fn alloc(def: MsgDef) -> Gc<Self> {
        Gc::new(Self {
            base: Self::obj_type().to_base(),
            def,
        })
    }

    pub fn msg(&self) -> &MsgDef {
        &self.def
    }

    fn obj_type() -> &'static Type {
        static TYPE: Type = obj_type! {
            name: Qstr::MP_QSTR_MsgDef,
            locals: &obj_dict!(obj_map! {
                Qstr::MP_QSTR_wire => obj_fn_1!(msg_def_obj_wire).to_obj(),
                Qstr::MP_QSTR_is_type_of => obj_fn_2!(msg_def_obj_is_type_of).to_obj(),
            }),
            call_fn: msg_def_obj_call,
        };
        &TYPE
    }
}

impl Into<Obj> for Gc<MsgDefObj> {
    fn into(self) -> Obj {
        // SAFETY:
        //  - We are GC-allocated.
        //  - We are `repr(C)`.
        //  - We have a `base` as the first field with the correct type.
        unsafe { Obj::from_ptr(Self::into_raw(self).cast()) }
    }
}

impl TryFrom<Obj> for Gc<MsgDefObj> {
    type Error = Error;

    fn try_from(value: Obj) -> Result<Self, Self::Error> {
        if MsgDefObj::obj_type().is_type_of(value) {
            // SAFETY: We assume that if `value` is an object pointer with the correct type,
            // it is always GC-allocated.
            let this = unsafe { Gc::from_raw(value.as_ptr().cast()) };
            Ok(this)
        } else {
            Err(Error::InvalidType)
        }
    }
}

unsafe extern "C" fn msg_def_obj_call(
    self_in: Obj,
    n_args: usize,
    n_kw: usize,
    args: *const Obj,
) -> Obj {
    util::try_with_args_and_kwargs_inline(n_args, n_kw, args, |_args, kwargs| {
        let this = Gc::<MsgDefObj>::try_from(self_in)?;
        let decoder = Decoder {
            enable_experimental: true,
        };
        let obj = decoder.message_from_values(kwargs, this.msg())?;
        Ok(obj)
    })
}

unsafe extern "C" fn msg_def_obj_wire(self_in: Obj) -> Obj {
    util::try_or_raise(|| {
        let this = Gc::<MsgDefObj>::try_from(self_in)?;
        Ok(this
            .def
            .wire_id
            .map_or_else(Obj::const_none, |wire_id| wire_id.into()))
    })
}

unsafe extern "C" fn msg_def_obj_is_type_of(self_in: Obj, obj: Obj) -> Obj {
    util::try_or_raise(|| {
        let this = Gc::<MsgDefObj>::try_from(self_in)?;
        let msg = Gc::<MsgObj>::try_from(obj);
        match msg {
            Ok(msg) if msg.msg_offset == this.def.offset => Ok(Obj::const_true()),
            _ => Ok(Obj::const_false()),
        }
    })
}
