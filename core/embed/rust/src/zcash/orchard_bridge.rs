use core::convert::{TryFrom, TryInto};
use core::ops::{Deref, DerefMut};

use cstr_core::CStr;
use f4jumble;
use orchard::keys::{FullViewingKey, IncomingViewingKey, SpendingKey};

use crate::error::Error;
use crate::micropython::{
    buffer::{Buffer, BufferMut},
    obj::Obj,
};
use crate::util;

/// Returns Orchard Full Viewing Key.
fn get_orchard_fvk(sk: Obj) -> Result<FullViewingKey, Error> {
    let sk: Buffer = sk.try_into()?;
    let mut sk_bytes = [0u8; 32];
    sk_bytes.copy_from_slice(sk.deref());

    // SpendingKey is not valid with a negligible probability.
    let sk = SpendingKey::from_bytes(sk_bytes);
    // conversion from CtOption to Option
    let sk: Option<SpendingKey> = sk.into();
    let err_msg =
        unsafe { CStr::from_bytes_with_nul_unchecked("Invalid Spending Key\0".as_bytes()) };
    let sk = sk.ok_or(Error::ValueError(err_msg))?;

    let fvk: FullViewingKey = (&sk).into();
    Ok(fvk)
}

#[no_mangle]
pub extern "C" fn zcash_get_orchard_fvk(sk: Obj) -> Obj {
    let block = || {
        let fvk = get_orchard_fvk(sk)?;
        let fvk_bytes = fvk.to_bytes();
        let fvk_obj = Obj::try_from(&fvk_bytes[..])?;
        Ok(fvk_obj)
    };
    unsafe { util::try_or_raise(block) }
}

#[no_mangle]
pub extern "C" fn zcash_get_orchard_ivk(sk: Obj) -> Obj {
    let block = || {
        let fvk = get_orchard_fvk(sk)?;
        let ivk: IncomingViewingKey = (&fvk).into();
        let ivk_bytes = ivk.to_bytes();
        let ivk_obj = Obj::try_from(&ivk_bytes[..])?;
        Ok(ivk_obj)
    };
    unsafe { util::try_or_raise(block) }
}

#[no_mangle]
pub extern "C" fn zcash_get_orchard_address(sk: Obj, diversifier_index: Obj) -> Obj {
    let block = || {
        let fvk = get_orchard_fvk(sk)?;
        let diversifier_index: u64 = diversifier_index.try_into()?;
        let addr = fvk.address_at(diversifier_index);
        let addr_bytes = addr.to_raw_address_bytes();
        let addr_obj = Obj::try_from(&addr_bytes[..])?;
        Ok(addr_obj)
    };
    unsafe { util::try_or_raise(block) }
}

// Length of f4jumbled message must be in range 48..=4194368
impl From<f4jumble::Error> for Error {
    fn from(_e: f4jumble::Error) -> Error {
        Error::OutOfRange
    }
}

#[no_mangle]
pub extern "C" fn zcash_f4jumble(message: Obj) -> Obj {
    let block = || {
        let mut message: BufferMut = message.try_into()?;
        let _ = f4jumble::f4jumble_mut(message.deref_mut())?;
        Ok(Obj::const_none())
    };
    unsafe { util::try_or_raise(block) }
}

#[no_mangle]
pub extern "C" fn zcash_f4jumble_inv(message: Obj) -> Obj {
    let block = || {
        let mut message: BufferMut = message.try_into()?;
        let _ = f4jumble::f4jumble_inv_mut(message.deref_mut())?;
        Ok(Obj::const_none())
    };
    unsafe { util::try_or_raise(block) }
}
