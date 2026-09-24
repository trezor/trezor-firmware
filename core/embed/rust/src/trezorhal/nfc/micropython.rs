use super::*;
use crate::micropython::macros::*;
use crate::micropython::module::Module;
use crate::micropython::qstr::Qstr;
use crate::micropython::{util, Error, Obj};

impl From<NfcError> for Error {
    fn from(error: NfcError) -> Self {
        match error {
            // TODO ts_t -> OsError
            NfcError::DriverError(_) => Error::RuntimeError(c"NFC driver error"), // TODO
            NfcError::InvalidData => Error::RuntimeError(c"Malformed NFC data"),
            NfcError::TimedOut => Error::RuntimeError(c"NFC operation timed out"),
            NfcError::UnsupportedTag => Error::RuntimeError(c"Unsupported card type"),
            NfcError::CommandFailed(_status_word) => Error::RuntimeError(c"Command failed"),
            NfcError::CommandFailedUnknown(_status_code) => {
                Error::RuntimeError(c"Command failed 2")
            }
            NfcError::HandshakeFailed => Error::RuntimeError(c"Handshake failed"),
        }
    }
}

extern "C" fn py_start() -> Obj {
    let block = || {
        start_discovery()?;
        Ok(Obj::const_none())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn py_stop() -> Obj {
    let block = || {
        stop_discovery()?;
        Ok(Obj::const_none())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn py_run() -> Obj {
    let block = || {
        //tap(apdu::Instruction::Wipe, &[], true, None)?;
        //tap(apdu::Instruction::WriteSeed, &[0x1; 256], true, Some(""))?;
        tap(apdu::Instruction::ReadSeed, &[], true, Some(""))?;
        //tap(apdu::Instruction::ReadSeedMetadata, &[], false, None)?;
        Ok(Obj::const_none())
    };
    unsafe { util::try_or_raise(block) }
}

// probably needs some kind of context object holding noise state, pin, queue of
// outgoing APDUs and what to do with their results

#[no_mangle]
#[rustfmt::skip]
pub static mp_module_trezornfc: Module = obj_module! {
    Qstr::MP_QSTR___name__ => Qstr::MP_QSTR_trezornfc.to_obj(),

    /// def start():
    ///     """
    ///     TODO.
    ///     """
    Qstr::MP_QSTR_start => obj_fn_0!(py_start).as_obj(),

    /// def stop():
    ///     """
    ///     TODO.
    ///     """
    Qstr::MP_QSTR_stop => obj_fn_0!(py_stop).as_obj(),

    Qstr::MP_QSTR_run => obj_fn_0!(py_run).as_obj(),
};
