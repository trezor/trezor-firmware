use super::*;
use crate::micropython::macros::*;
use crate::micropython::module::Module;
use crate::micropython::qstr::Qstr;
use crate::micropython::{util, Obj};

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

extern "C" fn py_run(num: Obj) -> Obj {
    let block = || {
        let num = u32::try_from(num)?;
        let reply = match num {
            0 => tap(apdu::Instruction::ReadSeedMetadata, &[])?,
            1 => tap(
                apdu::Instruction::WriteSeedMetadata,
                (0u8..=255u8).collect::<Vec<_, 256>>().as_slice(),
            )?,
            2 => tap(apdu::Instruction::ReadSeed, &[])?,
            3 => tap(
                apdu::Instruction::WriteSeed,
                (0u8..=255u8).rev().collect::<Vec<_, 256>>().as_slice(),
            )?,
            4 => tap(apdu::Instruction::Wipe, &[])?,
            5 => tap(apdu::Instruction::SetPin, encode_pin("1234")?.as_slice())?,
            6 => tap(apdu::Instruction::ReadPinCounter, &[])?,
            7 => tap(apdu::Instruction::ReadSuccessLog, &[])?,
            8 => tap(apdu::Instruction::ReadFailureLogs, &[])?,
            _ => {
                ulog::error!("Unknown NFC operation");
                Vec::new()
            }
        };
        let mut msg = String::<256>::new();
        match reply.len() {
            0 => ufmt::uwrite!(msg, "OK (no data)"),
            ..=81 => ufmt::uwrite!(msg, "{}", hex_bytes(&reply)),
            _ => ufmt::uwrite!(msg, "{}", hex_bytes(&reply[..81])),
        }
        .unwrap();
        (reply.len(), msg.as_str()).try_into()
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

    Qstr::MP_QSTR_run => obj_fn_1!(py_run).as_obj(),
};
