use super::blob;
use crate::error::Error;
use crate::io::InputStream;
use crate::micropython::buffer::get_buffer;
use crate::micropython::gc::Gc;
use crate::micropython::macros::{obj_fn_var, obj_module};
use crate::micropython::map::Map;
use crate::micropython::module::Module;
use crate::micropython::obj::Obj;
use crate::micropython::qstr::Qstr;
use crate::micropython::util;
use crate::protobuf::decode::Decoder;
use crate::protobuf::obj::MsgDefObj;

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
            .map_err(|_| Error::ExternalDataError(c"Invalid definition"))
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
