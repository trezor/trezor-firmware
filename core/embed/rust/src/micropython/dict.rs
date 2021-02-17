use super::{ffi, map::Map};

pub type Dict = ffi::mp_obj_dict_t;

impl Dict {
    pub fn new(map: Map) -> Self {
        unsafe {
            Self {
                base: ffi::mp_obj_base_t {
                    type_: &ffi::mp_type_dict,
                },
                map,
            }
        }
    }
}
