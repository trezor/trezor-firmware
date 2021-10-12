use crate::micropython::obj::Obj;

#[no_mangle]
pub extern "C" fn zcash_diag(_diag_type: Obj, data: Obj) -> Obj {
    data
}
