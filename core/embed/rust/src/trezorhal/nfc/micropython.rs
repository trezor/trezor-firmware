use super::*;
use crate::micropython::buffer::{get_buffer, Bytes, StrBuffer};
use crate::micropython::gc::Gc;
use crate::micropython::macros::*;
use crate::micropython::map::Map;
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
    pub fn new() -> Result<Gc<Self>, Error> {
        unsafe {
            Gc::new_with_custom_finaliser(Self {
                base: Self::obj_type().as_base(),
                state: TapContext::get()?,
            })
        }
    }

    fn obj_type() -> &'static Type {
        static TYPE: FullType = obj_type! {
            name: Qstr::MP_QSTR_TagConnection,
            locals: &obj_dict!(obj_map! {
                Qstr::MP_QSTR_uid => obj_fn_1!(nfc_conn_uid).as_obj(),
                Qstr::MP_QSTR_setup => obj_fn_var!(5, 5, nfc_conn_setup).as_obj(),
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
extern "C" fn nfc_conn_delete(obj: Obj) -> Obj {
    let block = || {
        let this: Gc<TagConnection> = obj.try_into()?;
        ulog::warn!(
            "Deleting NFC connection {} {:?}",
            hex_bytes(this.state.info.uid()),
            obj.as_ptr(),
        );
        Ok(Obj::const_none())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn nfc_conn_setup(n_args: usize, args: *const Obj) -> Obj {
    let block = |args: &[Obj], _kwargs: &Map| {
        let &[this, static_private_key, static_public_key, pin, verify_fn] =
            args.try_into().map_err(|_| Error::TypeError)?;

        let mut this: Gc<TagConnection> = this.try_into()?;
        // FIXME: SAFETY or mutex
        let this = unsafe { Gc::as_mut(&mut this) };

        let static_private_key: Option<Bytes> = static_private_key.try_into_option()?;
        let static_public_key: Option<Bytes> = static_public_key.try_into_option()?;
        let local_static_keys = match (&static_private_key, &static_public_key) {
            (Some(private), Some(public)) => Some(NoiseKeyPair {
                private: private.as_ref().try_into().map_err(|_| Error::TypeError)?,
                public: public.as_ref().try_into().map_err(|_| Error::TypeError)?,
            }),
            _ => None,
        };

        let pin: Option<StrBuffer> = pin.try_into_option()?;
        let pin: Option<&str> = pin.as_ref().map(|a| a.as_ref());

        let mut cert_error = None;
        let inner_fn = |static_public_key: &[u8; DHLEN], cert: &[u8]| {
            let static_public_key = static_public_key.as_ref().try_into()?;
            let cert = cert.try_into()?;
            let cert_ok = verify_fn.call_with_n_args(&[static_public_key, cert])?;
            bool::try_from(cert_ok)
        };
        let mut verify_fn = |static_public_key: &[u8; DHLEN], cert: &[u8]| {
            inner_fn(static_public_key, cert).unwrap_or_else(|e| {
                cert_error = Some(e);
                false
            })
        };
        match (
            this.state.setup(local_static_keys, pin, &mut verify_fn),
            cert_error,
        ) {
            (Ok(done), _) => Ok(done.into()),
            (Err(NfcError::InvalidCertificate), Some(e)) => Err(e),
            (Err(e), _) => Err(e.into()),
        }
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, &Map::EMPTY, block) }
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
        } else if matches!(ins, Instruction::SetPin) {
            &encode_pin(StrBuffer::try_from(data)?.as_ref())?
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

extern "C" fn py_connect() -> Obj {
    let block = || {
        let conn = TagConnection::new()?;
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
    ///     for the `NFC_CONNECTED` event and then call `connect()`."""
    Qstr::MP_QSTR_start_discovery => obj_fn_0!(py_start_discovery).as_obj(),

    /// def stop_discovery() -> None:
    ///     """Disables electromagnetic field and disconnects any active NFC tag."""
    Qstr::MP_QSTR_stop_discovery => obj_fn_0!(py_stop_discovery).as_obj(),

    /// def connect() -> TagConnection:
    ///     """Return connection handle after `NFC_CONNECTED` occurs. The next step is to call its
    ///     `setup()` method."""
    Qstr::MP_QSTR_connect => obj_fn_0!(py_connect).as_obj(),

    /// class TagConnection:
    ///     """Represents active communications session with powered-on NFC tag."""
    ///
    ///     def uid(self) -> bytes:
    ///         """Returns tag ID."""
    ///
    ///     def setup(self, static_private_key: bytes | None, static_public_key: bytes | None, pin: str | None, verify_fn: Callable[[bytes, bytes], bool]) -> bool:
    ///         """Select applet, open secure channel (optional) and authenticate with PIN (optional).
    ///         Returns True if complete and ready for issuing commands. Otherwise the caller needs
    ///         to poll for `NFC_TRANSCEIVE_DONE` and call the function again, repeating until it
    ///         returns True or raises an exception. Session is invalid after receiving `NFC_DISCONNECTED`.
    ///
    ///         Callback `verify_fn` is used to check remote static public key and certificate."""
    ///
    ///     def send_command(self, ins: int, data: AnyBytes | None) -> None:
    ///         """Schedule asynchronous sending of ISO-DEP command. Caller needs to poll for the
    ///         `NFC_TRANSCEIVE_DONE` event, then call `recv_response` to obtain the response or error."""
    ///
    ///     def recv_response(self) -> bytes | None:
    ///         """Return tag's response to previously called `send_command`."""
    ///
    /// mock:global

    /// class NfcError(RuntimeError):
    ///     pass
    Qstr::MP_QSTR_NfcError => super::error::micropython::EXCEPTION_TYPE.as_type().as_obj(),

    /// class NfcCommandFailed(NfcError):
    ///     """`arg[0]` is 16-bit status code, `arg[1]` is its text representation or None"""
    Qstr::MP_QSTR_NfcCommandFailed => super::error::micropython::EXCEPTION_COMMAND_FAILED_TYPE.as_type().as_obj(),

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

    /// GET_OS_VERSION: int
    Qstr::MP_QSTR_GET_OS_VERSION => Obj::small_int(Instruction::GetOsVersion.code()),

    /// GET_UID: int
    Qstr::MP_QSTR_GET_UID => Obj::small_int(Instruction::GetUid.code()),

    /// MEASURE_CPU_FREQUENCY: int
    Qstr::MP_QSTR_MEASURE_CPU_FREQUENCY => Obj::small_int(Instruction::MeasureCpuFrequency.code()),

    /// HARDEN_MEMORY: int
    Qstr::MP_QSTR_HARDEN_MEMORY => Obj::small_int(Instruction::HardenMemory.code()),

    /// INTEGRITY_CHECK: int
    Qstr::MP_QSTR_INTEGRITY_CHECK => Obj::small_int(Instruction::IntegrityCheck.code()),

    /// PIN_UNLOCKED: int
    Qstr::MP_QSTR_PIN_UNLOCKED => Obj::small_int(Instruction::PinUnlocked.code()),
    // TODO: use SimpleTypeObj, see e.g. NOTIFICATION_LEVEL_OBJ
};
