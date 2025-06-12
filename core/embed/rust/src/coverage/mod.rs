/// Off-heap data structure for collecting code coverage data.
use heapless::{Entry, FnvIndexMap};
use spin::RwLock;

use crate::{
    error::Error,
    micropython::{
        list::List,
        macros::{obj_fn_0, obj_fn_2, obj_module},
        module::Module,
        obj::Obj,
        qstr::Qstr,
        util,
    },
};

struct Key {
    file: Qstr,
    line: u16,
}

impl TryFrom<&Key> for Obj {
    type Error = Error;

    fn try_from(val: &Key) -> Result<Self, Self::Error> {
        (Obj::from(val.file), Obj::from(val.line)).try_into()
    }
}

impl core::hash::Hash for Key {
    fn hash<H: core::hash::Hasher>(&self, state: &mut H) {
        self.file.hash(state);
        self.line.hash(state);
    }
}

impl core::cmp::PartialEq for Key {
    fn eq(&self, other: &Key) -> bool {
        self.file == other.file && self.line == other.line
    }
}

impl core::cmp::Eq for Key {}

static COVERAGE_DATA: RwLock<FnvIndexMap<Key, u64, { 1024 * 1024 }>> =
    RwLock::new(FnvIndexMap::new());

struct Item<'a>((&'a Key, &'a u64));

impl<'a> TryFrom<Item<'a>> for Obj {
    type Error = Error;

    fn try_from(item: Item<'a>) -> Result<Self, Self::Error> {
        let (key, &value) = item.0;
        let key: Obj = key.try_into()?;
        let value: Obj = value.try_into()?;
        (key, value).try_into()
    }
}

extern "C" fn py_add(file: Obj, line: Obj) -> Obj {
    let block = || {
        let key = Key {
            file: file.try_into()?,
            line: line.try_into()?,
        };
        match COVERAGE_DATA.write().entry(key) {
            Entry::Occupied(e) => {
                *e.into_mut() += 1;
            }
            Entry::Vacant(e) => {
                e.insert(1)
                    .map_err(|_| Error::RuntimeError(c"COVERAGE_DATA is too small"))?;
            }
        };
        Ok(Obj::const_none())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn py_get() -> Obj {
    let block = || {
        let list = {
            let data = COVERAGE_DATA.read();
            List::from_iter(data.iter().map(Item))?
        };
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
