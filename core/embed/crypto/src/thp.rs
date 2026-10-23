//! Device identity derivation, independent of wallet vault owners.

use super::secret::{SecretContext, SecretContextLock, ZeroableMemory};
use super::{Error, ffi};

// SAFETY: HDNode is a flat C struct and an all-zero node is valid storage.
unsafe impl ZeroableMemory for ffi::HDNode {}

/// Borrow the legacy THP static private key only for a native operation.
/// The device secret already crosses the Python boundary; the derived node
/// and private key do not. Drop wipes the node on success and failure.
pub fn with_static_key<R>(
    device_secret: &[u8],
    operation: impl FnOnce(&[u8; 32]) -> R,
) -> Result<R, Error> {
    let mut context = SecretContext::<ffi::HDNode>::default();
    derive_and_use(&mut context, device_secret, operation)
}

fn derive_and_use<R>(
    context: &mut SecretContext<ffi::HDNode>,
    device_secret: &[u8],
    operation: impl FnOnce(&[u8; 32]) -> R,
) -> Result<R, Error> {
    let mut locked = SecretContextLock::new(context);
    if device_secret.len() != 16 {
        return Err(Error::InvalidParams);
    }
    let node = locked.hazard_mut();
    // SAFETY: all pointers refer to live buffers of the advertised lengths.
    // COPY HAZARD: the node is derived in place and is never copied out.
    let ok = unsafe {
        ffi::hdnode_from_seed(
            device_secret.as_ptr(),
            device_secret.len(),
            c"curve25519".as_ptr(),
            node,
        ) != 0
            && ffi::hdnode_private_ckd(node, 0x8054_4850) != 0
    };
    if !ok {
        return Err(Error::InvalidContext);
    }
    Ok(operation(&node.private_key))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn legacy_identity_vectors() {
        // Recorded from the unmodified Stage A HDNode implementation.
        let vectors = [
            (
                "00000000000000000000000000000000",
                "9c762377b24ffb1a022b20d2f78b2ff5ee212e9011f1e3f6df75f6c65d559023",
            ),
            (
                "000102030405060708090a0b0c0d0e0f",
                "bdf1b57c1e4c46d8f269a5c50f9f7e1bd90f8ed4ad6909be1117f80127b2daf3",
            ),
            (
                "ffffffffffffffffffffffffffffffff",
                "7efb2325d9c027cb58dea80cd98a05ca4f89134290dc57cb172f688d4078bc97",
            ),
        ];
        for (seed, expected) in vectors {
            let seed = hex::decode(seed).unwrap();
            assert!(with_static_key(&seed, |key| assert_eq!(hex::encode(key), expected)).is_ok());
        }
    }

    #[test]
    fn invalid_device_secret_lengths() {
        for length in [0, 1, 15, 17, 32, 64] {
            assert!(
                with_static_key(&[0; 64][..length], |_| panic!("invalid secret accepted")).is_err()
            );
        }
    }

    #[test]
    fn erases_context_on_success_and_error() {
        let mut context = SecretContext::<ffi::HDNode>::default();
        for (invalid, fail_operation) in [(false, false), (false, true), (true, true)] {
            // Include an existing value to check the invalid-input exit too.
            context.hazard_mut().private_key.fill(0x5a);
            let secret = [0; 16];
            let secret = if invalid { &secret[..15] } else { &secret[..] };
            let result = derive_and_use(&mut context, secret, |_| {
                if fail_operation { Err(()) } else { Ok(()) }
            });
            assert_eq!(result.is_err(), invalid);
            // SAFETY: the locked context was zeroized in place and has not moved.
            let erased = unsafe {
                core::slice::from_raw_parts(
                    (context.hazard_mut() as *const ffi::HDNode).cast::<u8>(),
                    core::mem::size_of::<ffi::HDNode>(),
                )
            };
            assert!(erased.iter().all(|byte| *byte == 0));
        }
    }
}
