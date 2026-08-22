use crypto::{cosi, ed25519};

use super::constants;
use crate::error::{value_error, Error};
use crate::micropython::buffer::get_buffer;
use crate::micropython::macros::{obj_fn_var, obj_module};
use crate::micropython::map::Map;
use crate::micropython::module::Module;
use crate::micropython::obj::Obj;
use crate::micropython::qstr::Qstr;
use crate::micropython::util;

fn verify_with_keys(
    threshold: u8,
    digest: &[u8],
    sig: &cosi::Signature,
    public_keys: &[ed25519::PublicKey; 3],
) -> Result<(), Error> {
    Ok(cosi::verify(threshold, digest, public_keys, sig)?)
}

fn threshold_for_version(version: u8) -> Result<u8, Error> {
    match version {
        constants::VERSION_1 => Ok(constants::THRESHOLD_V1),
        _ => Err(value_error!(c"Unsupported definition format version")),
    }
}

extern "C" fn verify(n_args: usize, args: *const Obj) -> Obj {
    let block = |args: &[Obj], _kwargs: &Map| {
        if args.len() != 4 {
            return Err(Error::TypeError);
        }
        // SAFETY: reference is discarded at the end of the block
        let digest = unsafe { get_buffer(args[0])? };
        let signature = unsafe { get_buffer(args[1])? };
        let sigmask = u8::try_from(args[2])?;
        let format_version = u8::try_from(args[3])?;
        let threshold = threshold_for_version(format_version)?;

        let sig =
            cosi::Signature::new(sigmask, signature.try_into().map_err(|_| Error::TypeError)?);
        #[allow(unused_mut)]
        let mut result =
            verify_with_keys(threshold, digest, &sig, &constants::PUBLIC_KEYS_PRODUCTION);
        #[cfg(feature = "dev_keys")]
        if result.is_err() {
            // allow development keys
            result = verify_with_keys(threshold, digest, &sig, &constants::PUBLIC_KEYS_DEVEL);
        }
        result.map(|()| Obj::const_none())
    };

    unsafe { util::try_with_args_and_kwargs(n_args, args, &Map::EMPTY, block) }
}

#[no_mangle]
#[rustfmt::skip]
pub static mp_module_trezordefinitions: Module = obj_module! {
    /// def verify(digest: AnyBytes, sig: AnyBytes, sigmask: int, version: int) -> None:
    ///     """Verify the definitions signature."""
    Qstr::MP_QSTR_verify => obj_fn_var!(4, 4, verify).as_obj(),
};
