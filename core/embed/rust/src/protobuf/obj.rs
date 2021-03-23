use core::convert::TryFrom;

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

use super::decode::Decoder;
use super::defs::{find_name_by_msg_offset, get_msg, MsgDef};

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

    pub fn def(&self) -> MsgDef {
        unsafe { get_msg(self.msg_offset) }
    }

    fn obj_type() -> &'static Type {
        static TYPE: Type = obj_type! {
            name: Qstr::MP_QSTR_Msg,
            attr_fn: msg_obj_attr,
        };
        &TYPE
    }
}

impl MsgObj {
    fn getattr(&self, attr: Qstr) -> Result<Obj, Error> {
        if let Ok(obj) = self.map.get(attr) {
            // Message field was found, return its value.
            return Ok(obj);
        }

        // Built-in attribute
        match attr {
            Qstr::MP_QSTR_MESSAGE_WIRE_TYPE => {
                // Return the wire ID of this message def, or None if not set.
                Ok(self.msg_wire_id.map_or(Obj::const_none(), |wire_id| wire_id.into()))
            }
            Qstr::MP_QSTR_MESSAGE_NAME => {
                // Return the qstr name of this message def
                Ok(Qstr::from_u16(find_name_by_msg_offset(self.msg_offset)?).into())
            }
            Qstr::MP_QSTR___dict__ => {
                // Conversion to dict. Allocate a new dict object with a copy of our map
                // and return it. This is a bit different from how uPy does it now, because
                // we're returning a mutable dict.
                Ok(Gc::new(Dict::with_map(self.map.clone())).into())
            }
            _ => { Err(Error::Missing) }
        }
    }

    fn setattr(&mut self, attr: Qstr, value: Obj) -> Result<(), Error> {
        if value == Obj::const_null() {
            // this would be a delattr
            return Err(Error::InvalidOperation);
        }

        if self.map.contains_key(attr) {
            self.map.set(attr, value);
            Ok(())
        } else {
            Err(Error::Missing)
        }
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
    util::try_or_raise(|| {
        let mut this = Gc::<MsgObj>::try_from(self_in)?;
        let attr = Qstr::from_u16(attr as _);

        unsafe {
            if dest.read() == Obj::const_null() {
                // Load attribute
                dest.write(this.getattr(attr)?);
            } else {
                let value = dest.offset(1).read();
                // Store attribute
                Gc::as_mut(&mut this).setattr(attr, value)?;
                dest.write(Obj::const_null());
            }
            Ok(())
        }
    })
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
    util::try_or_raise(|| {
        let this=  Gc::<MsgDefObj>::try_from(self_in)?;
        let attr = Qstr::from_u16(attr as _);

        if unsafe { dest.read() } != Obj::const_null() {
            return Err(Error::InvalidOperation);
        }

        match attr {
            Qstr::MP_QSTR_MESSAGE_NAME => {
                // Return the qstr name of this message def
                let name = Qstr::from_u16(find_name_by_msg_offset(this.def.offset)?);
                unsafe { dest.write(name.into()); };
            }
            Qstr::MP_QSTR_MESSAGE_WIRE_TYPE => {
                // Return the wire type of this message def
                let wire_id_obj = this
                    .def
                    .wire_id
                    .map_or_else(Obj::const_none, |wire_id| wire_id.into());
                unsafe { dest.write(wire_id_obj); };
            }
            Qstr::MP_QSTR_is_type_of => {
                // Return the is_type_of bound method
                // dest[0] = function_obj
                // dest[1] = self
                unsafe {
                    dest.write(MSG_DEF_OBJ_IS_TYPE_OF_OBJ.to_obj());
                    dest.offset(1).write(self_in);
                }
            }
            _ => { return Err(Error::Missing); }
        }
        Ok(())
    });
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

static MSG_DEF_OBJ_IS_TYPE_OF_OBJ: ffi::mp_obj_fun_builtin_fixed_t = obj_fn_2!(msg_def_obj_is_type_of);
