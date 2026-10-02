use heapless::Vec;

use super::{Error, ed25519, ffi};

const MAX_PUBKEYS: usize = 3;

/// Collective Ed25519 signature with a bitmask of participating public keys.
pub struct Signature {
    sigmask: u8,
    signature: ed25519::Signature,
}

impl Signature {
    /// `sigmask` is a bitmask over `public_keys` (bit 0 = first key).
    pub fn new(sigmask: u8, signature: ed25519::Signature) -> Self {
        Self { sigmask, signature }
    }
}

/// Verify a CoSi signature of `message`.
///
/// Combines the public keys selected by `signature.sigmask` and checks that at
/// least `threshold` of them participated.
pub fn verify(
    threshold: u8,
    message: &[u8],
    public_keys: &[ed25519::PublicKey],
    signature: &Signature,
) -> Result<(), Error> {
    if threshold < 1 {
        return Err(Error::InvalidParams);
    }
    let selected_keys = select_keys(signature.sigmask, public_keys)?;
    if selected_keys.len() < threshold as usize {
        return Err(Error::InvalidParams);
    }
    let combined_key = combine_publickeys(&selected_keys)?;
    ed25519::verify(message, &combined_key, &signature.signature)
}

fn select_keys(
    mut sigmask: u8,
    keys: &[ed25519::PublicKey],
) -> Result<Vec<ed25519::PublicKey, MAX_PUBKEYS>, Error> {
    let mut selected_keys = Vec::new();
    for key in keys {
        if sigmask & 1 != 0 {
            let result = selected_keys.push(*key);
            if result.is_err() {
                // selected_keys is sized to MAX_PUBKEYS.
                // if the push overflows, means there's too many pubkeys selected.
                return Err(Error::InvalidSigmask);
            }
        }
        sigmask >>= 1;
    }
    if sigmask != 0 {
        Err(Error::InvalidParams)
    } else {
        Ok(selected_keys)
    }
}

/// Combines `keys` into the public key a CoSi signature over them verifies
/// against (see [`verify`]).
pub fn combine_publickeys(keys: &[ed25519::PublicKey]) -> Result<ed25519::PublicKey, Error> {
    let mut combined_key = ed25519::PublicKey::default();
    // SAFETY: ffi
    let res = unsafe {
        ffi::ed25519_cosi_combine_publickeys(&mut combined_key as *mut _, keys.as_ptr(), keys.len())
    };
    if res == 0 {
        Ok(combined_key)
    } else {
        Err(Error::InvalidEncoding)
    }
}

#[cfg(test)]
mod test {
    use super::*;

    // RFC 8032 test vectors 1 and 2
    const KEY_A: &str = "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a";
    const KEY_B: &str = "3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c";

    fn key(hex_str: &str) -> ed25519::PublicKey {
        hex::decode(hex_str).unwrap().try_into().unwrap()
    }

    #[test]
    fn test_combine_single_key() {
        let a = key(KEY_A);
        assert_eq!(combine_publickeys(&[a]).unwrap(), a);
    }

    #[test]
    fn test_combine_is_order_independent() {
        let (a, b) = (key(KEY_A), key(KEY_B));
        let ab = combine_publickeys(&[a, b]).unwrap();
        assert_eq!(combine_publickeys(&[b, a]).unwrap(), ab);
        assert_ne!(ab, a);
        assert_ne!(ab, b);
    }

    #[test]
    fn test_combine_invalid_key() {
        // y = 2 is not on the curve
        let mut bad = [0u8; 32];
        bad[0] = 2;
        let res = combine_publickeys(&[key(KEY_A), bad]);
        assert!(matches!(res, Err(Error::InvalidEncoding)));
    }
}
