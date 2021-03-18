use core::convert::{TryFrom, TryInto};

use crate::{
    error::Error,
    micropython::{
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

pub const MSG_WIRE_ID_ATTR: Qstr = Qstr::MP_QSTR_MESSAGE_WIRE_TYPE;

#[repr(C)]
pub struct MsgObj {
    base: ObjBase,
    map: Map,
}

impl MsgObj {
    pub fn alloc_with_capacity(capacity: usize) -> Gc<Self> {
        Gc::new(Self {
            base: Self::obj_type().to_base(),
            map: Map::new_with_capacity(capacity),
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

    if dest.read() == Obj::const_null() {
        // Load attribute.
        if let Ok(obj) = this.map.get(attr) {
            dest.write(obj);
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
            attr_fn: msg_def_obj_attr,
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

unsafe extern "C" fn msg_def_obj_attr(self_in: Obj, attr: ffi::qstr, dest: *mut Obj) {
    let this: Gc<MsgDefObj> = self_in.try_into().unwrap();

    let attr = Qstr::from_u16(attr as _);

    if dest.read() == Obj::const_null() {
        let value = match attr {
            // Get this message's wire ID, or None if not present.
            MSG_WIRE_ID_ATTR => match this.def.wire_id {
                Some(wire_id) => wire_id.into(),
                None => Obj::const_none(),
            },
            // Fail for unknown attributes.
            _ => Obj::const_null(),
        };
        dest.write(value);
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
            enable_experimental: false,
        };
        let obj = decoder.message_from_values(kwargs, this.msg())?;
        Ok(obj)
    })
}
