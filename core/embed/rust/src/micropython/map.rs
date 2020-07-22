use crate::{
    error::Error,
    micropython::{obj::Obj, qstr::Qstr},
};

// micropython/py/obj.h mp_map_elem_t
#[repr(C)]
pub struct MapElem {
    key: Obj,
    value: Obj,
}

// micropython/py/obj.h mp_map_lookup_kind_t
#[repr(C)]
enum MapLookupKind {
    Lookup = 0,
    LookupAddIfNotFound = 1,
    LookupRemoveIfFound = 2,
    LookupAddIfNotFoundOrRemoveIfFound = 3,
}

extern "C" {
    // micropython/py/obj.h mp_map_t
    pub type Map;

    // micropython/py/map.c
    fn mp_map_lookup(map: *mut Map, index: Obj, lookup_kind: MapLookupKind) -> *mut MapElem;
}

impl Map {
    pub fn get(&self, index: Obj) -> Result<Obj, Error> {
        // SAFETY:
        //  - `mp_map_lookup` returns either NULL or a pointer to a `MapElem` value with
        //    a lifetime valid for the whole lifetime of the passed immutable ref of
        //    `map`.
        //  - with `MapLookupKind::Lookup`, `map` stays unmodified and the cast to mut
        //    ptr is therefore safe.
        //  - `mp_map_lookup` and `MapLookupKind` bindings correspond to the C sources.
        unsafe {
            let map = self as *const Map as *mut Map;
            let elem = mp_map_lookup(map, index, MapLookupKind::Lookup)
                .as_ref()
                .ok_or(Error::Missing)?;
            Ok(elem.value)
        }
    }

    pub fn get_qstr(&self, index: Qstr) -> Result<Obj, Error> {
        self.get(index.to_obj())
    }
}
