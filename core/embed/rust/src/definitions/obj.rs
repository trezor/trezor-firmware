use crypto::{cosi, ed25519};

use super::error::Error as DefinitionsError;
use super::{blob, constants};
use crate::io::InputStream;
use crate::micropython::buffer::get_buffer;
use crate::micropython::exception::Exception;
use crate::micropython::gc::Gc;
use crate::micropython::macros::{obj_fn_var, obj_module};
use crate::micropython::map::Map;
use crate::micropython::module::Module;
use crate::micropython::qstr::Qstr;
use crate::micropython::util::EXTERNAL_DATA_ERROR;
use crate::micropython::{util, Error, Obj};
use crate::protobuf::decode::Decoder;
use crate::protobuf::obj::MsgDefObj;

impl From<DefinitionsError> for Error {
    fn from(error: DefinitionsError) -> Self {
        let exc = Exception::new_with_arg(&EXTERNAL_DATA_ERROR, error.to_string());
        Error::Exception(exc)
    }
}

fn verify_with_keys(
    threshold: u8,
    digest: &[u8],
    sig: &cosi::Signature,
    public_keys: &[ed25519::PublicKey; 3],
) -> Result<(), DefinitionsError> {
    cosi::verify(threshold, digest, public_keys, sig)
        .map_err(|_| DefinitionsError::InvalidSignature)
}

fn threshold_for_version(version: u8) -> Result<u8, DefinitionsError> {
    constants::DefsVersion::try_from_byte(version).map(|version| version.threshold())
}

extern "C" fn decode(n_args: usize, args: *const Obj) -> Obj {
    let block = |args: &[Obj], _kwargs: &Map| {
        if args.len() != 3 {
            return Err(Error::TypeError);
        }
        // SAFETY: We assume that for the lifetime of `definition`, no MicroPython
        // code can run that would mutate the buffer, nor pass it to another Rust
        // function.
        let definition = unsafe { get_buffer(args[0])? };
        let expected_type = u8::try_from(args[1])?;
        let msg_def = Gc::<MsgDefObj>::try_from(args[2])?;

        // parse the definition blob and verify its CoSi signature
        let payload = blob::parse_and_verify(definition, expected_type)?;

        // decode the payload into the expected message type
        let mut stream = InputStream::new(payload);
        let decoder = Decoder {
            enable_experimental: false,
        };
        decoder
            .message_from_stream(&mut stream, msg_def.msg())
            .map_err(|_| DefinitionsError::InvalidPayload.into())
    };

    unsafe { util::try_with_args_and_kwargs(n_args, args, &Map::EMPTY, block) }
}

#[no_mangle]
#[rustfmt::skip]
pub static mp_module_trezordefinitions: Module = obj_module! {
    /// from trezorproto import MessageType
    ///
    /// mock:global
    /// T = TypeVar("T", bound=MessageType)
    ///
    /// def decode(
    ///     definition: AnyBytes,
    ///     expected_type: int,
    ///     msg_type: type[T],
    /// ) -> T:
    ///     """Parse a signed definition blob, verify its signature and decode it
    ///     into the specified message type."""
    Qstr::MP_QSTR_decode => obj_fn_var!(3, 3, decode).as_obj(),
};
