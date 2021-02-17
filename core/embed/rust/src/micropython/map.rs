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
            key: key.to_obj(),
            value,
        }
    }
}

impl Map {
    pub fn get(&self, index: Obj) -> Result<Obj, Error> {
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

    pub fn get_qstr(&self, index: Qstr) -> Result<Obj, Error> {
        self.get(index.to_obj())
    }
}

pub type MapElem = ffi::mp_map_elem_t;
