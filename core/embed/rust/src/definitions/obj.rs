use crypto::{cosi, ed25519};

use super::constants;
use crate::micropython::buffer::get_buffer;
use crate::micropython::macros::{obj_fn_3, obj_module};
use crate::micropython::module::Module;
use crate::micropython::qstr::Qstr;
use crate::micropython::{util, Error, Obj};

fn verify_with_keys(
    digest: &[u8],
    sig: &cosi::Signature,
    public_keys: &[ed25519::PublicKey; 3],
) -> Result<(), Error> {
    cosi::verify(constants::THRESHOLD, digest, public_keys, sig)
        .map_err(|_| Error::ValueError(c"Signature verification failed"))
}

extern "C" fn verify(digest: Obj, sig: Obj, sigmask: Obj) -> Obj {
    let block = || {
        // SAFETY: reference is discarded at the end of the block
        let digest = unsafe { get_buffer(digest)? };
        let signature = unsafe { get_buffer(sig)? };

        let sig = cosi::Signature::new(
            u8::try_from(sigmask)?,
            signature.try_into().map_err(|_| Error::TypeError)?,
        );
        #[allow(unused_mut)]
        let mut result = verify_with_keys(digest, &sig, &constants::PUBLIC_KEYS_PRODUCTION);
        #[cfg(feature = "dev_keys")]
        if result.is_err() {
            // allow development keys
            result = verify_with_keys(digest, &sig, &constants::PUBLIC_KEYS_DEVEL);
        }
        result.map(|()| Obj::const_none())
    };

    unsafe { util::try_or_raise(block) }
}

#[no_mangle]
#[rustfmt::skip]
pub static mp_module_trezordefinitions: Module = obj_module! {
    /// def verify(digest: AnyBytes, sig: AnyBytes, sigmask: int) -> None:
    ///     """Verify the definitions signature."""
    Qstr::MP_QSTR_verify => obj_fn_3!(verify).as_obj(),
};
