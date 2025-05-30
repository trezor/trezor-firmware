// Copyright (c) 2025 Trezor Company s.r.o.
//
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in
// all copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
// SOFTWARE.

use heapless::{Entry, FnvIndexMap};

use crate::{
    error::Error,
    micropython::{map::Map, qstr::Qstr},
};

use super::{buffer::StrBuffer, list::List, module::Module, obj::Obj, util};

struct Key {
    file: StrBuffer,
    line: u16,
}

impl TryFrom<&Key> for Obj {
    type Error = Error;

    fn try_from(val: &Key) -> Result<Self, Self::Error> {
        let file: Obj = val.file.as_ref().try_into()?;
        let line: Obj = val.line.into();
        (file, line).try_into()
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
        self.file.as_ref() == other.file.as_ref() && self.line == other.line
    }
}

impl core::cmp::Eq for Key {}

static mut COVERAGE_DATA: FnvIndexMap<Key, u64, { 1024 * 1024 }> = FnvIndexMap::new();

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
        // SAFETY: we are in single-threaded environment
        unsafe {
            match COVERAGE_DATA.entry(key) {
                Entry::Occupied(e) => {
                    *e.into_mut() += 1;
                }
                Entry::Vacant(e) => {
                    e.insert(1)
                        .map_err(|_| Error::RuntimeError(c"COVERAGE_DATA is too small"))?;
                }
            }
        };
        Ok(Obj::const_none())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn py_get() -> Obj {
    let block = || {
        // SAFETY: we are in single-threaded environment
        let list = unsafe { List::from_iter(COVERAGE_DATA.iter().map(Item))? };
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
