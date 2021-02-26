use core::slice;

use crate::{
    error::Error,
    micropython::{obj::Obj, qstr::Qstr},
};

use super::ffi;

pub type Map = ffi::mp_map_t;

impl Map {
    pub fn fixed<const N: usize>(table: &'static [MapElem; N]) -> Self {
        // micropython/py/ob.h MP_DEFINE_CONST_DICT
        // .all_keys_are_qstrs = 1,
        // .is_fixed = 1,
        // .is_ordered = 1,
        // .used = MP_ARRAY_SIZE(table_name),
        // .alloc = MP_ARRAY_SIZE(table_name),
        let bits = 0b111 | N << 3;
        let bitfield = ffi::__BindgenBitfieldUnit::new(bits.to_ne_bytes());
        Self {
            _bitfield_align_1: [],
            _bitfield_1: bitfield,
            alloc: N,
            table: table.as_ptr() as *mut MapElem,
        }
    }

    pub fn at(key: Qstr, value: Obj) -> MapElem {
        MapElem {
            key: key.into(),
            value,
        }
    }
}

impl Map {
    pub fn len(&self) -> usize {
        self.used()
    }

    pub fn elems(&self) -> &[MapElem] {
        // SAFETY: `self.table` should always point to an array of `MapElem` of
        // `self.len()` items valid at least for the lifetime of `self`.
        unsafe { slice::from_raw_parts(self.table, self.len()) }
    }

    pub fn contains_key(&self, index: impl Into<Obj>) -> bool {
        self.get_obj(index.into()).is_ok()
    }

    pub fn get(&self, index: impl Into<Obj>) -> Result<Obj, Error> {
        self.get_obj(index.into())
    }

    pub fn get_obj(&self, index: Obj) -> Result<Obj, Error> {
        // SAFETY:
        //  - `mp_map_lookup` returns either NULL or a pointer to a `mp_map_elem_t`
        //    value with a lifetime valid for the whole lifetime of the passed immutable
        //    ref of `map`.
        //  - with `_mp_map_lookup_kind_t_MP_MAP_LOOKUP`, `map` stays unmodified and the
        //    cast to mut ptr is therefore safe.
        unsafe {
            let map = self as *const Map as *mut Map;
            let elem = ffi::mp_map_lookup(map, index, ffi::_mp_map_lookup_kind_t_MP_MAP_LOOKUP)
                .as_ref()
                .ok_or(Error::Missing)?;
            Ok(elem.value)
        }
    }

    pub unsafe fn set(&self, index: impl Into<Obj>, value: impl Into<Obj>) {
        self.set_obj(index.into(), value.into())
    }

    pub unsafe fn set_obj(&self, index: Obj, value: Obj) {
        let map = self as *const Map as *mut Map;
        let elem = ffi::mp_map_lookup(
            map,
            index,
            ffi::_mp_map_lookup_kind_t_MP_MAP_LOOKUP_ADD_IF_NOT_FOUND,
        )
        .as_mut()
        .unwrap();
        elem.value = value;
    }
}

pub type MapElem = ffi::mp_map_elem_t;
