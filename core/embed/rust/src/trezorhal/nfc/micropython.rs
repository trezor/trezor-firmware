use core::cell::RefCell;

use crypto::noise_xxpsk3::NoiseXXpsk3Ctx;

use super::*;
use crate::micropython::buffer::{get_buffer, Bytes, StrBuffer};
use crate::micropython::exception::{builtin, Exception, ExceptionType};
use crate::micropython::gc::{Gc, GcBox};
use crate::micropython::macros::*;
use crate::micropython::map::Map;
use crate::micropython::module::Module;
use crate::micropython::obj::{Obj, ObjBase};
use crate::micropython::qstr::Qstr;
use crate::micropython::typ::{FullType, Type};
use crate::micropython::{util, Error};

const DELETED: Error = Error::RuntimeError(c"NFC connection deleted");
const BUSY: Error = Error::RuntimeError(c"NFC context is locked");
static EXCEPTION_TYPE: ExceptionType =
    ExceptionType::new(builtin::RuntimeError, Qstr::MP_QSTR_NfcError);
static EXCEPTION_COMMAND_FAILED_TYPE: ExceptionType =
    ExceptionType::new(&EXCEPTION_TYPE, Qstr::MP_QSTR_NfcCommandFailed);

impl From<NfcError> for Error {
    fn from(error: NfcError) -> Self {
        let code_description = |code: u16| -> Obj {
            match StatusWord::try_from(code) {
                Ok(sw) => {
                    let msg = uformat!(len: 32, "{:?}", sw);
                    msg.as_str().try_into().unwrap_or(Obj::const_none())
                }
                Err(_) => Obj::const_none(),
            }
        };
        let exc = |msg| Error::Exception(Exception::new_with_arg(&EXCEPTION_TYPE, msg));
        match error {
            NfcError::UnexpectedInput => exc(c"Unexpected input"),
            NfcError::InvalidData => exc(c"Malformed NFC data"),
            NfcError::UnsupportedTag => exc(c"Unsupported tag type"),
            NfcError::CryptoError => exc(c"Secure channel failed"),
            NfcError::InvalidCertificate => exc(c"Certificate validation failed"),
            NfcError::TagDisconnected => Error::EOFError,
            NfcError::CommandFailed(code) => Error::Exception(Exception::new(
                &EXCEPTION_COMMAND_FAILED_TYPE,
                &[code.into(), code_description(code)],
            )),
            NfcError::DriverError(e) => Error::OSError(e),
        }
    }
}

type TapContextGcNoise = TapContext<GcBox<NoiseXXpsk3Ctx>>;

#[repr(C)]
struct TagConnection {
    base: ObjBase,
    // `None` after `__del__`.
    state: RefCell<Option<TapContextGcNoise>>,
}

impl TagConnection {
    pub fn new() -> Result<Gc<Self>, Error> {
        let noise_ctx = GcBox::new(NoiseXXpsk3Ctx::default())?;
        // SAFETY: has valid base as its first element.
        let base = Self::obj_type().as_base();
        let state = RefCell::new(Some(TapContext::get(noise_ctx)?));
        unsafe { Gc::new_with_custom_finaliser(Self { base, state }) }
    }

    /// Run `f` with exclusive access to the session. Fails with `BUSY` when
    /// called re-entrantly, e.g. from the `verify_fn` callback during
    /// `setup()`.
    fn with_mut<R>(
        &self,
        f: impl FnOnce(&mut Option<TapContextGcNoise>) -> Result<R, Error>,
    ) -> Result<R, Error> {
        let mut state = self.state.try_borrow_mut().map_err(|_| BUSY)?;
        f(&mut state)
    }

    /// Like `with_mut`, but fails with `DELETED` after `__del__`.
    fn with_state<R>(
        &self,
        f: impl FnOnce(&mut TapContextGcNoise) -> Result<R, Error>,
    ) -> Result<R, Error> {
        self.with_mut(|state| f(state.as_mut().ok_or(DELETED)?))
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

impl TryFrom<Obj> for Gc<TagConnection> {
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

impl From<Gc<TagConnection>> for Obj {
    fn from(val: Gc<TagConnection>) -> Self {
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
        this.with_state(|state| state.info.uid().try_into())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn nfc_conn_delete(obj: Obj) -> Obj {
    let block = || {
        let this: Gc<TagConnection> = obj.try_into()?;
        this.with_mut(|state| {
            if let Some(s) = &*state {
                ulog::debug!(
                    "Deleting NFC connection {} {:?}",
                    hex_bytes(s.info.uid()),
                    obj.as_ptr(),
                );
            }
            // Drop the session in place, wiping its secrets.
            state.take();
            Ok(())
        })?;
        Ok(Obj::const_none())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn nfc_conn_setup(n_args: usize, args: *const Obj) -> Obj {
    let block = |args: &[Obj], _kwargs: &Map| {
        let &[this, static_private_key, static_public_key, pin, verify_fn] =
            args.try_into().map_err(|_| Error::TypeError)?;
        let this: Gc<TagConnection> = this.try_into()?;

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
                assert!(cert_error.is_none());
                cert_error = Some(e);
                false
            })
        };
        let result =
            this.with_state(|state| Ok(state.setup(local_static_keys, pin, &mut verify_fn)))?;
        match (result, cert_error) {
            (Ok(done), _) => Ok(done.into()),
            (Err(NfcError::InvalidCertificate), Some(e)) => Err(e),
            (Err(e), _) => Err(e.into()),
        }
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, &Map::EMPTY, block) }
}

extern "C" fn nfc_conn_send_command(this: Obj, ins: Obj, data: Obj) -> Obj {
    let block = || {
        let this: Gc<TagConnection> = this.try_into()?;
        let ins = u16::try_from(ins)?;
        let ins =
            Instruction::try_from(ins).map_err(|_| Error::ValueError(c"Unknown instruction"))?;
        let data = if data == Obj::const_none() {
            &[]
        } else if matches!(ins, Instruction::SetPin) {
            &encode_pin(StrBuffer::try_from(data)?.as_ref())?
        } else {
            // SAFETY: reference is discarded before the function returns, with no calls to
            // micropython inbetween
            unsafe { get_buffer(data)? }
        };
        let c_apdu = CApdu::compose(ins, data)?;
        this.with_state(|state| Ok(state.command(&c_apdu)?))?;
        Ok(Obj::const_none())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn nfc_conn_recv_response(this: Obj) -> Obj {
    let block = || {
        let this: Gc<TagConnection> = this.try_into()?;
        this.with_state(|state| match state.response()? {
            None => Ok(Obj::const_none()),
            Some(data) => data.try_into(),
        })
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

extern "C" fn py_is_connected() -> Obj {
    is_connected().into()
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

    /// def is_connected() -> bool:
    ///     """Whether a tag is connected. Check it before waiting for `NFC_CONNECTED`, the
    ///     event may have been delivered to another task (e.g. the previous layout)."""
    Qstr::MP_QSTR_is_connected => obj_fn_0!(py_is_connected).as_obj(),

    /// class TagConnection:
    ///     """Represents active communication session with powered-on NFC tag."""
    ///
    ///     def uid(self) -> bytes:
    ///         """Returns tag ID."""
    ///
    ///     def setup(self, static_private_key: bytes | None, static_public_key: bytes | None, pin: str | None, verify_fn: Callable[[bytes, bytes], bool]) -> bool:
    ///         """Select applet, open secure channel (optional) and authenticate with PIN (optional).
    ///         Returns True if complete and ready for issuing commands. Otherwise the caller needs
    ///         to poll for `NFC_TRANSCEIVE_DONE` and call the function again (with the same
    ///         arguments), repeating until it returns True or raises an exception. Session is invalid
    ///         after receiving `NFC_DISCONNECTED`.
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
    ///     def __del__(self) -> None:
    ///         """Ends the session and wipes its secrets. The connection cannot be
    ///         used afterwards."""
    ///
    /// mock:global

    /// class NfcError(RuntimeError):
    ///     pass
    Qstr::MP_QSTR_NfcError => EXCEPTION_TYPE.as_type().as_obj(),

    /// class NfcCommandFailed(NfcError):
    ///     """`arg[0]` is 16-bit status code, `arg[1]` is its text representation or None"""
    Qstr::MP_QSTR_NfcCommandFailed => EXCEPTION_COMMAND_FAILED_TYPE.as_type().as_obj(),

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
};

#[cfg(feature = "emulator")]
mod emulator {
    use num_traits::FromPrimitive;
    use rtl::error::Error as RtlError;

    use super::super::emulator::{get_command, set_connected, set_response};
    use super::*;

    pub extern "C" fn py_set_connected(uid: Obj) -> Obj {
        let block = || {
            let uid: Option<Bytes> = uid.try_into_option()?;
            set_connected(uid.as_deref())?;
            Ok(Obj::const_none())
        };
        unsafe { util::try_or_raise(block) }
    }

    pub extern "C" fn py_get_command() -> Obj {
        let block = || match get_command()? {
            None => Ok(Obj::const_none()),
            Some((apdu, is_psk)) => (apdu.as_slice(), is_psk).try_into(),
        };
        unsafe { util::try_or_raise(block) }
    }

    pub extern "C" fn py_set_response(response: Obj) -> Obj {
        let block = || {
            if let Ok(code) = i32::try_from(response) {
                let error =
                    RtlError::from_i32(code).ok_or(Error::ValueError(c"Unknown error code"))?;
                set_response(Err(error))?;
            } else {
                set_response(Ok(&Bytes::try_from(response)?))?;
            }
            Ok(Obj::const_none())
        };
        unsafe { util::try_or_raise(block) }
    }
}

#[cfg(feature = "emulator")]
#[no_mangle]
#[rustfmt::skip]
pub static mp_module_trezornfcemu: Module = obj_module! {
    Qstr::MP_QSTR___name__ => Qstr::MP_QSTR_trezornfcemu.to_obj(),

    /// mock:global

    /// def set_connected(uid: AnyBytes | None) -> None:
    ///     """Place a card with the given UID in the field, or remove it if `uid`
    ///     is None. Removing the card fails the exchange in progress. Stopping
    ///     discovery removes the card too."""
    Qstr::MP_QSTR_set_connected => obj_fn_1!(emulator::py_set_connected).as_obj(),

    /// def get_command() -> tuple[bytes, bool] | None:
    ///     """Take the frame waiting to be sent to the card, together with a flag
    ///     that is True for the PSK share and False for a command APDU. Returns
    ///     None if no exchange has been started. Raises EOFError if the card is
    ///     not in the field."""
    Qstr::MP_QSTR_get_command => obj_fn_0!(emulator::py_get_command).as_obj(),

    /// def set_response(response: AnyBytes | int) -> None:
    ///     """Complete the exchange with the card's response, or fail it with the
    ///     given error code. Raises EOFError if the card is not in the field."""
    Qstr::MP_QSTR_set_response => obj_fn_1!(emulator::py_set_response).as_obj(),
};
