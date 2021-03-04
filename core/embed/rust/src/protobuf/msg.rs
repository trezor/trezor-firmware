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
};

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
            locals: &obj_dict!(obj_map! {
                // TODO: Pass null.
            }),
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
    let mut this: Gc<MsgObj> = match self_in.try_into() {
        Ok(obj) => obj,
        Err(_) => return,
    };
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
