//! The card side of the emulated NFC driver.

use rtl::error::Error as RtlError;

use super::apdu::Apdu;
use super::{ffi, NfcError};

/// Place a card with `uid` in the field, or remove the card if `uid` is
/// `None`. Removing the card fails the exchange in progress.
pub fn set_connected(uid: Option<&[u8]>) -> Result<(), NfcError> {
    let (ptr, len) = uid.map_or((core::ptr::null(), 0), |uid| (uid.as_ptr(), uid.len()));
    // SAFETY: ffi, the UID is copied before the call returns
    unsafe { ffi::nfc_emu_set_connected(ptr, len) }.ok()?;
    Ok(())
}

/// Take the frame waiting to be sent to the card, and whether it is the
/// reader's PSK share. Fails with `TagDisconnected` if the card is not in the
/// field.
pub fn get_command() -> Result<Option<(Apdu, bool)>, NfcError> {
    let mut cmd: *mut Apdu = core::ptr::null_mut();
    let mut is_psk = false;
    // SAFETY: ffi
    unsafe { ffi::nfc_emu_get_command(&mut cmd, &mut is_psk) }.ok()?;
    // SAFETY: the frame lives in the driver state, which is not modified until
    // `nfc_emu_set_response()`. It is copied out right away.
    let frame = unsafe { cmd.as_ref() }.map(|apdu| {
        let copy = Apdu {
            data: apdu.data,
            data_len: apdu.data_len,
        };
        (copy, is_psk)
    });
    Ok(frame)
}

/// Complete the exchange with the card's response, or fail it with the given
/// error. Fails with `TagDisconnected` if the card is not in the field.
pub fn set_response(response: Result<&[u8], RtlError>) -> Result<(), NfcError> {
    let res = match response {
        // SAFETY: ffi, the response is copied before the call returns
        Ok(data) => unsafe { ffi::nfc_emu_set_response(0, data.as_ptr(), data.len()) },
        // SAFETY: ffi
        Err(e) => unsafe { ffi::nfc_emu_set_response(e as u32, core::ptr::null(), 0) },
    };
    res.ok()?;
    Ok(())
}
