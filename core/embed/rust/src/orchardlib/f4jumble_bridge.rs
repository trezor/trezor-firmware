//! This module is a python FFI bridge for f4jumble crate.

use core::ops::DerefMut;
use f4jumble;

use crate::error::Error;
use crate::micropython::{buffer::BufferMut, obj::Obj, util};

// Length of F4jumbled message must be in range 48..=4194368.
impl From<f4jumble::Error> for Error {
    fn from(_e: f4jumble::Error) -> Error {
        Error::OutOfRange
    }
}

/// Apply the F4jumble permutation to a message.
#[no_mangle]
pub extern "C" fn orchardlib_f4jumble(message: Obj) -> Obj {
    let block = || {
        let mut message: BufferMut = message.try_into()?;
        f4jumble::f4jumble_mut(message.deref_mut())?;
        Ok(Obj::const_none())
    };
    unsafe { util::try_or_raise(block) }
}

/// Apply the F4jumble inverse permutation to a message.
#[no_mangle]
pub extern "C" fn orchardlib_f4jumble_inv(message: Obj) -> Obj {
    let block = || {
        let mut message: BufferMut = message.try_into()?;
        f4jumble::f4jumble_inv_mut(message.deref_mut())?;
        Ok(Obj::const_none())
    };
    unsafe { util::try_or_raise(block) }
}
