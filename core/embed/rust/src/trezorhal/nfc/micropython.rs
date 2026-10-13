use super::*;
use crate::micropython::buffer::get_buffer;
use crate::micropython::gc::Gc;
use crate::micropython::macros::*;
use crate::micropython::module::Module;
use crate::micropython::obj::{Obj, ObjBase};
use crate::micropython::qstr::Qstr;
use crate::micropython::typ::{FullType, Type};
use crate::micropython::{util, Error};

#[repr(C)]
struct TagConnection<'a> {
    base: ObjBase,
    state: TapContext<'a>,
}

impl<'a> TagConnection<'a> {
    pub fn new(static_private_key: &[u8], static_public_key: &[u8]) -> Result<Gc<Self>, Error> {
        let mut state = TapContext::get()?;
        state.set_keys(static_private_key, static_public_key)?;
        state.set_pin("")?;
        unsafe {
            Gc::new_with_custom_finaliser(Self {
                base: Self::obj_type().as_base(),
                state,
            })
        }
    }

    fn obj_type() -> &'static Type {
        static TYPE: FullType = obj_type! {
            name: Qstr::MP_QSTR_TagConnection,
            locals: &obj_dict!(obj_map! {
                Qstr::MP_QSTR_uid => obj_fn_1!(nfc_conn_uid).as_obj(),
                Qstr::MP_QSTR_setup => obj_fn_2!(nfc_conn_setup).as_obj(),
                Qstr::MP_QSTR_send_command => obj_fn_3!(nfc_conn_send_command).as_obj(),
                Qstr::MP_QSTR_recv_response => obj_fn_1!(nfc_conn_recv_response).as_obj(),
                Qstr::MP_QSTR___del__ => obj_fn_1!(nfc_conn_delete).as_obj(),
            }),
        };
        &TYPE
    }
}

impl<'a> TryFrom<Obj> for Gc<TagConnection<'a>> {
    type Error = Error;

    fn try_from(value: Obj) -> Result<Self, Self::Error> {
        if TagConnection::obj_type().is_type_of(value) {
            // SAFETY: We assume that if `value` is an object pointer with the correct type,
            // it is always GC-allocated.
            let this = unsafe { Gc::from_raw(value.as_ptr().cast()) };
            Ok(this)
        } else {
            Err(Error::TypeError)
        }
    }
}

impl<'a> From<Gc<TagConnection<'a>>> for Obj {
    fn from(val: Gc<TagConnection<'a>>) -> Self {
        // SAFETY:
        //  - We are GC-allocated.
        //  - We are `repr(C)`.
        //  - We have a `base` as the first field with the correct type.
        unsafe { Obj::from_ptr(Gc::into_raw(val).cast()) }
    }
}

extern "C" fn nfc_conn_uid(this: Obj) -> Obj {
    let block = || {
        let this: Gc<TagConnection> = this.try_into()?;
        this.state.info.uid().try_into()
    };
    unsafe { util::try_or_raise(block) }
}

// FIXME why is this not called
extern "C" fn nfc_conn_delete(this: Obj) -> Obj {
    let block = || {
        let this: Gc<TagConnection> = this.try_into()?;
        ulog::warning!(
            "Deleting NFC connection {}",
            hex_bytes(this.state.info.uid())
        );
        Ok(Obj::const_none())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn nfc_conn_setup(this: Obj, verify_fn: Obj) -> Obj {
    let block = || {
        let mut this: Gc<TagConnection> = this.try_into()?;
        // FIXME: SAFETY or mutex
        let this = unsafe { Gc::as_mut(&mut this) };
        let inner_fn = |static_public_key: &[u8; DHLEN], cert: &[u8]| {
            let static_public_key = static_public_key.as_ref().try_into()?;
            let cert = cert.try_into()?;
            let cert_ok = verify_fn.call_with_n_args(&[static_public_key, cert])?;
            bool::try_from(cert_ok)
        };
        let verify_fn = |static_public_key: &[u8; DHLEN], cert: &[u8]| {
            inner_fn(static_public_key, cert).unwrap_or_else(|_e| {
                // TODO log or propagate error
                ulog::error!("Certificate callback failed");
                false
            })
        };
        let done = this.state.setup(&verify_fn)?;
        Ok(done.into())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn nfc_conn_send_command(this: Obj, ins: Obj, data: Obj) -> Obj {
    let block = || {
        let mut this: Gc<TagConnection> = this.try_into()?;
        // FIXME: SAFETY or mutex
        let this = unsafe { Gc::as_mut(&mut this) };

        let ins = u16::try_from(ins)?;
        let ins =
            Instruction::try_from(ins).map_err(|_| Error::ValueError(c"Unknown instruction"))?;
        let data = if data == Obj::const_none() {
            &[]
        } else {
            unsafe { get_buffer(data)? }
        };
        this.state.command(ins, data)?;
        Ok(Obj::const_none())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn nfc_conn_recv_response(this: Obj) -> Obj {
    let block = || {
        let mut this: Gc<TagConnection> = this.try_into()?;
        // FIXME: SAFETY or mutex
        let this = unsafe { Gc::as_mut(&mut this) };

        match this.state.response()? {
            None => Ok(Obj::const_none()),
            Some(data) => data.try_into(),
        }
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn py_start_discovery() -> Obj {
    let block = || {
        start_discovery()?;
        Ok(Obj::const_none())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn py_stop_discovery() -> Obj {
    let block = || {
        stop_discovery()?;
        Ok(Obj::const_none())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn py_connect(static_private_key: Obj, static_public_key: Obj) -> Obj {
    let block = || {
        let static_private_key = unsafe { get_buffer(static_private_key)? };
        let static_public_key = unsafe { get_buffer(static_public_key)? };
        let conn = TagConnection::new(static_private_key, static_public_key)?;
        Ok(conn.into())
    };
    unsafe { util::try_or_raise(block) }
}

#[no_mangle]
#[rustfmt::skip]
pub static mp_module_trezornfc: Module = obj_module! {
    Qstr::MP_QSTR___name__ => Qstr::MP_QSTR_trezornfc.to_obj(),

    /// def start_discovery() -> None:
    ///     """Activate electromagnetic field and start searching for an NFC tag. Caller should poll
    ///     for the `NFC_EVENT_CONNECTED` event and then call `connect()`."""
    Qstr::MP_QSTR_start_discovery => obj_fn_0!(py_start_discovery).as_obj(),

    /// def stop_discovery() -> None:
    ///     """Disables electromagnetic field and disconnects any active NFC tag."""
    Qstr::MP_QSTR_stop_discovery => obj_fn_0!(py_stop_discovery).as_obj(),

    /// def connect(static_private_key: bytes, static_public_key: bytes) -> TagConnection:
    ///     """Return connection handle after `NFC_EVENT_CONNECTED` occurs. The next step is to call
    ///     its `setup()` method."""
    Qstr::MP_QSTR_connect => obj_fn_2!(py_connect).as_obj(),

    /// class TagConnection:
    ///     """Represents active communications session with powered-on NFC tag."""
    ///
    ///     def uid(self) -> bytes:
    ///         """Returns tag ID."""
    ///
    ///     def setup(self, verify_fn: Callable[[bytes, bytes], bool]) -> bool:
    ///         """Select applet, open secure channel (optional) and authenticate with PIN (optional).
    ///         Returns True if complete and ready for issuing commands. Otherwise the caller needs
    ///         to poll for `NFC_EVENT_TRANSCEIVE_DONE` and call the function again, repeating until
    ///         it returns True or raises an exception. Session is invalid after receiving
    ///         `NFC_EVENT_DISCONNECTED`.
    ///
    ///         Callback `verify_fn` is used to check remote static public key and certificate."""
    ///
    ///     def send_command(self, ins: int, data: AnyBytes | None) -> None:
    ///         """Schedule asynchronous sending of ISO-DEP command. Caller needs to poll for the
    ///         `NFC_EVENT_TRANSCEIVE_DONE` event, then call `recv_response` to obtain the response
    ///         or error."""
    ///
    ///     def recv_response(self) -> bytes | None:
    ///         """Return tag's response to previously called `send_command`."""
    ///
    /// mock:global

    /// SET_PIN: int
    Qstr::MP_QSTR_SET_PIN => Obj::small_int(Instruction::SetPin.code()),

    /// WIPE: int
    Qstr::MP_QSTR_WIPE => Obj::small_int(Instruction::Wipe.code()),

    /// READ_PIN_COUNTER: int
    Qstr::MP_QSTR_READ_PIN_COUNTER => Obj::small_int(Instruction::ReadPinCounter.code()),

    /// READ_SUCCESS_LOG: int
    Qstr::MP_QSTR_READ_SUCCESS_LOG => Obj::small_int(Instruction::ReadSuccessLog.code()),

    /// READ_FAILURE_LOGS: int
    Qstr::MP_QSTR_READ_FAILURE_LOGS => Obj::small_int(Instruction::ReadFailureLogs.code()),

    /// READ_SEED_METADATA: int
    Qstr::MP_QSTR_READ_SEED_METADATA => Obj::small_int(Instruction::ReadSeedMetadata.code()),

    /// WRITE_SEED_METADATA: int
    Qstr::MP_QSTR_WRITE_SEED_METADATA => Obj::small_int(Instruction::WriteSeedMetadata.code()),

    /// READ_SEED: int
    Qstr::MP_QSTR_READ_SEED => Obj::small_int(Instruction::ReadSeed.code()),

    /// WRITE_SEED: int
    Qstr::MP_QSTR_WRITE_SEED => Obj::small_int(Instruction::WriteSeed.code()),
    // TODO: use SimpleTypeObj, see e.g. NOTIFICATION_LEVEL_OBJ
};
