use heapless::FnvIndexSet;

use crate::{
    error::Error,
    micropython::{map::Map, qstr::Qstr},
};

use super::{buffer::StrBuffer, list::List, module::Module, obj::Obj, util};

struct Entry {
    file: StrBuffer,
    line: u16,
}

impl TryFrom<&Entry> for Obj {
    type Error = Error;

    fn try_from(val: &Entry) -> Result<Self, Self::Error> {
        let file: Obj = val.file.as_ref().try_into()?;
        let line: Obj = val.line.into();
        let tuple = (file, line);
        tuple.try_into()
    }
}

impl core::hash::Hash for Entry {
    fn hash<H: core::hash::Hasher>(&self, state: &mut H) {
        self.file.hash(state);
        self.line.hash(state);
    }
}

impl core::cmp::PartialEq for Entry {
    fn eq(&self, other: &Entry) -> bool {
        self.file.as_ref() == other.file.as_ref() && self.line == other.line
    }
}

impl core::cmp::Eq for Entry {}

static mut COVERAGE_DATA: FnvIndexSet<Entry, { 1024 * 1024 }> = FnvIndexSet::new();

extern "C" fn py_add(file: Obj, line: Obj) -> Obj {
    let block = || {
        let entry = Entry {
            file: file.try_into()?,
            line: line.try_into()?,
        };
        // SAFETY: we are in single-threaded environment
        let res = unsafe { COVERAGE_DATA.insert(entry) };
        res.map_err(|_| Error::RuntimeError(c"COVERAGE_DATA is too small"))?;
        Ok(Obj::const_none())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn py_get() -> Obj {
    let block = || {
        // SAFETY: we are in single-threaded environment
        let list = unsafe { List::from_iter(COVERAGE_DATA.iter())? };
        Ok(list.leak().into())
    };
    unsafe { util::try_or_raise(block) }
}

#[no_mangle]
#[rustfmt::skip]
pub static mp_module_coveragedata: Module = obj_module! {
    Qstr::MP_QSTR___name__ => Qstr::MP_QSTR_coveragedata.to_obj(),

    /// mock:global

    /// def add(file: str, line: int) -> None:
    ///     """
    ///     Mark file line as covered.
    ///     """
    Qstr::MP_QSTR_add => obj_fn_2!(py_add).as_obj(),

    /// def get() -> list[tuple[str, int]]:
    ///     """
    ///     Return a list of all covered file lines.
    ///     """
    Qstr::MP_QSTR_get => obj_fn_0!(py_get).as_obj(),
};
