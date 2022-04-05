use crate::micropython::{ffi, obj::Obj};

extern "C" {
    fn mp_obj_print(obj: ffi::mp_obj_t, kind: ffi::mp_print_kind_t);
}

pub fn _int(i: i64) {
    _obj(Obj::try_from(i).unwrap());
}

pub fn _obj(obj: Obj) {
    unsafe {
        mp_obj_print(obj, ffi::mp_print_kind_t_PRINT_REPR);
    }
}

pub fn _bytes<const N: usize>(bytes: &[u8; N]) {
    _obj(Obj::try_from(&bytes[..]).unwrap());
}

pub fn _int_decorated(i: i64) {
    let space = Obj::try_from(&b"   "[..]).unwrap();
    _obj(space);
    _int(i);
    _obj(space);
}
