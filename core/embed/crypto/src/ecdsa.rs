use super::{Error, ffi};

pub const ECDSA_DIGEST_SIZE: usize = ffi::ECDSA_SCALAR_SIZE as usize;
pub const ECDSA_SIGNATURE_SIZE: usize = ffi::ECDSA_RAW_SIGNATURE_SIZE as usize;
pub const ECDSA_PUBLIC_KEY_SIZE: usize = ffi::ECDSA_PUBLIC_KEY_SIZE as usize;
pub const ECDSA_PUBLIC_KEY_COMPRESSED_SIZE: usize = ffi::ECDSA_PUBLIC_KEY_COMPRESSED_SIZE as usize;

pub type EcdsaDigest = [u8; ECDSA_DIGEST_SIZE];
pub type EcdsaSignature = [u8; ECDSA_SIGNATURE_SIZE];
pub type EcdsaPublicKey = [u8; ECDSA_PUBLIC_KEY_SIZE];

/// Supported Weierstrass curves for ECDSA.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Curve {
    Secp256k1,
    Nist256p1,
}

#[derive(Debug, Copy, Clone, PartialEq, Eq)]
#[repr(transparent)]
pub struct RecId(u8);

impl RecId {
    pub const fn new(value: u8) -> Self {
        let Ok(new) = Self::try_new(value) else {
            panic!("invalid recovery id");
        };
        new
    }

    pub const fn try_new(value: u8) -> Result<Self, Error> {
        if value > 3 {
            Err(Error::InvalidParams)
        } else {
            Ok(Self(value))
        }
    }
}

macro_rules! try_from_int {
    ($type:ty) => {
        impl TryFrom<$type> for RecId {
            type Error = Error;

            fn try_from(value: $type) -> Result<Self, Self::Error> {
                #[allow(irrefutable_let_patterns)]
                let Ok(value) = u8::try_from(value) else {
                    return Err(Error::InvalidParams);
                };
                Self::try_new(value)
            }
        }
    };
}

try_from_int!(u8);
try_from_int!(u16);
try_from_int!(u32);
try_from_int!(u64);
try_from_int!(u128);
try_from_int!(i8);
try_from_int!(i16);
try_from_int!(i32);
try_from_int!(i64);
try_from_int!(i128);

impl From<RecId> for cty::c_int {
    fn from(value: RecId) -> Self {
        value.0 as cty::c_int
    }
}

impl Curve {
    fn to_ffi_curve(self) -> *const ffi::ecdsa_curve {
        match self {
            // SAFETY: `secp256k1` / `nist256p1` are immutable C statics provided by
            // trezor-crypto and live for the whole program.
            Curve::Secp256k1 => unsafe { &ffi::secp256k1 },
            Curve::Nist256p1 => unsafe { &ffi::nist256p1 },
        }
    }
}

/// Check that `pubkey` is a compressed (`0x02`/`0x03`) or uncompressed (`0x04`)
/// SEC1 encoding of the expected length.
fn verify_pubkey_slice(pubkey: &[u8]) -> Result<(), Error> {
    if pubkey.is_empty() {
        return Err(Error::InvalidEncoding);
    }
    match pubkey[0] {
        0x02 | 0x03 if pubkey.len() == ECDSA_PUBLIC_KEY_COMPRESSED_SIZE => Ok(()),
        0x04 if pubkey.len() == ECDSA_PUBLIC_KEY_SIZE => Ok(()),
        _ => Err(Error::InvalidEncoding),
    }
}

/// Verify an ECDSA signature of `digest` against `public_key` on `curve`.
///
/// `public_key` may be compressed or uncompressed SEC1 encoding.
pub fn verify_digest(
    curve: Curve,
    public_key: &[u8],
    signature: &EcdsaSignature,
    digest: &EcdsaDigest,
) -> Result<(), Error> {
    verify_pubkey_slice(public_key)?;
    let ffi_curve = curve.to_ffi_curve();
    // SAFETY:
    // * ffi_curve is one of the supported builtin curves
    // * public_key is either a compressed or uncompressed public key of correct
    //   size
    // * signature has correct length
    // * digest has correct length
    let result = unsafe {
        ffi::ecdsa_verify_digest(
            ffi_curve,
            public_key.as_ptr(),
            signature.as_ptr(),
            digest.as_ptr(),
        )
    };
    if result == 0 {
        Ok(())
    } else {
        Err(Error::SignatureVerificationFailed)
    }
}

/// Recover the uncompressed public key from an ECDSA signature of `digest`.
///
/// `recid` is the recovery id (`0..=3`) identifying which of the candidate
/// points was used.
pub fn verify_recover(
    curve: Curve,
    signature: &EcdsaSignature,
    recid: RecId,
    digest: &EcdsaDigest,
) -> Result<EcdsaPublicKey, Error> {
    let ffi_curve = curve.to_ffi_curve();
    let mut public_key = [0u8; ECDSA_PUBLIC_KEY_SIZE];
    // SAFETY:
    // * ffi_curve is one of the supported builtin curves
    // * signature has correct length
    // * digest has correct length
    // * public_key is a pointer to a valid sized buffer
    let result = unsafe {
        ffi::ecdsa_recover_pub_from_sig(
            ffi_curve,
            public_key.as_mut_ptr(),
            signature.as_ptr(),
            digest.as_ptr(),
            recid.into(),
        )
    };
    if result == 0 {
        Ok(public_key)
    } else {
        Err(Error::SignatureVerificationFailed)
    }
}

#[cfg(test)]
mod test {
    use super::*;
    use crate::sha256::Sha256;

    fn hex_arr<const N: usize>(s: &str) -> [u8; N] {
        hex::decode(s).unwrap().try_into().unwrap()
    }

    fn digest_of(msg: &[u8]) -> EcdsaDigest {
        Sha256::digest(msg)
    }

    fn compress(uncompressed: &EcdsaPublicKey) -> [u8; ECDSA_PUBLIC_KEY_COMPRESSED_SIZE] {
        let mut compressed = [0u8; ECDSA_PUBLIC_KEY_COMPRESSED_SIZE];
        compressed[0] = if uncompressed[64] & 1 == 0 {
            0x02
        } else {
            0x03
        };
        compressed[1..].copy_from_slice(&uncompressed[1..33]);
        compressed
    }

    fn recover_recid(
        curve: Curve,
        signature: &EcdsaSignature,
        digest: &EcdsaDigest,
        expected: &EcdsaPublicKey,
    ) -> RecId {
        for recid in 0..=3 {
            let recid = RecId::try_from(recid).unwrap();
            if let Ok(recovered) = verify_recover(curve, signature, recid, digest) {
                if recovered == *expected {
                    return recid;
                }
            }
        }
        panic!("no recovery id produced the expected public key");
    }

    struct VerifyVector {
        curve: Curve,
        /// Uncompressed SEC1 public key (65 hex bytes + 0x04 prefix).
        pubkey: &'static str,
        /// Pre-hashed digest. If `None`, SHA-256 of `msg` is used.
        digest: Option<&'static str>,
        msg: &'static [u8],
        /// IEEE P1363 / compact `r || s` encoding.
        signature: &'static str,
        /// Recovery id when published with the vector.
        recid: Option<RecId>,
        valid: bool,
    }

    impl VerifyVector {
        fn pubkey(&self) -> Vec<u8> {
            hex::decode(self.pubkey).unwrap()
        }

        fn digest(&self) -> EcdsaDigest {
            match self.digest {
                Some(d) => hex_arr(d),
                None => digest_of(self.msg),
            }
        }

        fn signature(&self) -> EcdsaSignature {
            hex_arr(self.signature)
        }
    }

    // RFC 6979 A.2.5 (NIST P-256, SHA-256) and the widely published secp256k1
    // RFC 6979 extra vector (python-ecdsa / fpgaminer), plus Google Wycheproof
    // P1363 vectors and the go-ethereum ecrecover fixture.
    const VERIFY_VECTORS: &[VerifyVector] = &[
        // RFC 6979 A.2.5, SHA-256, message = "sample"
        // https://www.rfc-editor.org/rfc/rfc6979.html#appendix-A.2.5
        VerifyVector {
            curve: Curve::Nist256p1,
            pubkey: "0460fed4ba255a9d31c961eb74c6356d68c049b8923b61fa6ce669622e60f29fb67903fe1008b8bc99a41ae9e95628bc64f2f1b20c2d7e9f5177a3c294d4462299",
            digest: None,
            msg: b"sample",
            signature: "efd48b2aacb6a8fd1140dd9cd45e81d69d2c877b56aaf991c34d0ea84eaf3716f7cb1c942d657c41d436c7a1b6e29f65f3e900dbb9aff4064dc4ab2f843acda8",
            recid: None,
            valid: true,
        },
        // RFC 6979 A.2.5, SHA-256, message = "test"
        VerifyVector {
            curve: Curve::Nist256p1,
            pubkey: "0460fed4ba255a9d31c961eb74c6356d68c049b8923b61fa6ce669622e60f29fb67903fe1008b8bc99a41ae9e95628bc64f2f1b20c2d7e9f5177a3c294d4462299",
            digest: None,
            msg: b"test",
            signature: "f1abb023518351cd71d881567b1ea663ed3efcf6c5132b354f28d3b0b7d38367019f4113742a2b14bd25926b49c649155f267e60d3814b4c0cc84250e46f0083",
            recid: None,
            valid: true,
        },
        // RFC 6979-style secp256k1 extra vector (privkey = 1, message =
        // "Satoshi Nakamoto"), published in python-ecdsa:
        // https://github.com/tlsfuzzer/python-ecdsa/pull/10
        VerifyVector {
            curve: Curve::Secp256k1,
            pubkey: "0479be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798483ada7726a3c4655da4fbfc0e1108a8fd17b448a68554199c47d08ffb10d4b8",
            digest: None,
            msg: b"Satoshi Nakamoto",
            signature: "934b1ea10a4b3c1757e2b0c017d0b6143ce3c9a7e6a4a49860d7a6ab210ee3d8dbbd3162d46e9f9bef7feb87c16dc13b4f6568a87f4e83f728e2443ba586675c",
            recid: None,
            valid: true,
        },
        // Google Wycheproof ecdsa_secp256k1_sha256_p1363 tcId 1 (valid)
        // https://github.com/C2SP/wycheproof/blob/master/testvectors_v1/ecdsa_secp256k1_sha256_p1363_test.json
        VerifyVector {
            curve: Curve::Secp256k1,
            pubkey: "04b838ff44e5bc177bf21189d0766082fc9d843226887fc9760371100b7ee20a6ff0c9d75bfba7b31a6bca1974496eeb56de357071955d83c4b1badaa0b21832e9",
            digest: None,
            msg: b"123400",
            signature: "813ef79ccefa9a56f7ba805f0e478584fe5f0dd5f567bc09b5123ccbc9832365900e75ad233fcc908509dbff5922647db37c21f4afd3203ae8dc4ae7794b0f87",
            recid: None,
            valid: true,
        },
        // Google Wycheproof ecdsa_secp256r1_sha256_p1363 tcId 1 (valid)
        VerifyVector {
            curve: Curve::Nist256p1,
            pubkey: "042927b10512bae3eddcfe467828128bad2903269919f7086069c8c4df6c732838c7787964eaac00e5921fb1498a60f4606766b3d9685001558d1a974e7341513e",
            digest: None,
            msg: b"123400",
            signature: "2ba3a8be6b94d5ec80a6d9d1190a436effe50d85a1eee859b8cc6af9bd5c2e184cd60b855d442f5b3c7b11eb6c4e0ae7525fe710fab9aa7c77a67f79e6fadd76",
            recid: None,
            valid: true,
        },
        // Google Wycheproof secp256k1 tcId 4: r replaced by n - r (invalid)
        VerifyVector {
            curve: Curve::Secp256k1,
            pubkey: "04b838ff44e5bc177bf21189d0766082fc9d843226887fc9760371100b7ee20a6ff0c9d75bfba7b31a6bca1974496eeb56de357071955d83c4b1badaa0b21832e9",
            digest: None,
            msg: b"123400",
            signature: "7ec10863310565a908457fa0f1b87a79bc4fcf10b9e0e4320ac021c106b31ddc6ff18a52dcc0336f7af62400a6dd9b810732baf1ff758000d6f613a556eb31ba",
            recid: None,
            valid: false,
        },
        // Google Wycheproof secp256k1 tcId 11: r = 0, s = 0 (invalid)
        VerifyVector {
            curve: Curve::Secp256k1,
            pubkey: "04b838ff44e5bc177bf21189d0766082fc9d843226887fc9760371100b7ee20a6ff0c9d75bfba7b31a6bca1974496eeb56de357071955d83c4b1badaa0b21832e9",
            digest: None,
            msg: b"123400",
            signature: "00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000",
            recid: None,
            valid: false,
        },
        // go-ethereum crypto/signature_test.go (verify + ecrecover)
        // https://github.com/ethereum/go-ethereum/blob/master/crypto/signature_test.go
        VerifyVector {
            curve: Curve::Secp256k1,
            pubkey: "04e32df42865e97135acfb65f3bae71bdc86f4d49150ad6a440b6f15878109880a0a2b2667f7e725ceea70c673093bf67663e0312623c8e091b13cf2c0f11ef652",
            digest: Some("ce0677bb30baa8cf067c88db9811f4333d131bf8bcf12fe7065d211dce971008"),
            msg: b"",
            signature: "90f27b8b488db00b00606796d2987f6a5f59ae62ea05effe84fef5b8b0e549984a691139ad57a3f0b906637673aa2f63d1f55cb1a69199d4009eea23ceaddc93",
            recid: Some(RecId::new(1)),
            valid: true,
        },
    ];

    #[test]
    fn test_recid() {
        for id in 0u8..=3 {
            let recid = RecId::try_new(id).expect("0..=3 is a valid recovery id");
            assert_eq!(recid, RecId::new(id));
            assert_eq!(recid, RecId::try_from(id).unwrap());
            assert_eq!(recid, RecId::try_from(i32::from(id)).unwrap());
            assert_eq!(cty::c_int::from(recid), cty::c_int::from(id));
        }

        assert!(matches!(RecId::try_new(4), Err(Error::InvalidParams)));
        assert!(matches!(RecId::try_from(4u8), Err(Error::InvalidParams)));
        assert!(matches!(RecId::try_from(4u32), Err(Error::InvalidParams)));
        assert!(matches!(RecId::try_from(-1i8), Err(Error::InvalidParams)));
        assert!(matches!(RecId::try_from(-1i32), Err(Error::InvalidParams)));
    }

    #[test]
    #[should_panic(expected = "invalid recovery id")]
    fn test_recid_new_panics_out_of_range() {
        let _ = RecId::new(4);
    }

    #[test]
    fn test_verify_pubkey_slice() {
        let mut compressed = [0u8; ECDSA_PUBLIC_KEY_COMPRESSED_SIZE];
        compressed[0] = 0x02;
        assert!(verify_pubkey_slice(&compressed).is_ok());
        compressed[0] = 0x03;
        assert!(verify_pubkey_slice(&compressed).is_ok());

        let mut uncompressed = [0u8; ECDSA_PUBLIC_KEY_SIZE];
        uncompressed[0] = 0x04;
        assert!(verify_pubkey_slice(&uncompressed).is_ok());

        assert!(matches!(
            verify_pubkey_slice(&[]),
            Err(Error::InvalidEncoding)
        ));
        assert!(matches!(
            verify_pubkey_slice(&[0x02]),
            Err(Error::InvalidEncoding)
        ));
        assert!(matches!(
            verify_pubkey_slice(&compressed[..ECDSA_PUBLIC_KEY_COMPRESSED_SIZE - 1]),
            Err(Error::InvalidEncoding)
        ));
        assert!(matches!(
            verify_pubkey_slice(&uncompressed[..ECDSA_PUBLIC_KEY_SIZE - 1]),
            Err(Error::InvalidEncoding)
        ));

        // Compressed prefix with uncompressed length, and vice versa.
        uncompressed[0] = 0x02;
        assert!(matches!(
            verify_pubkey_slice(&uncompressed),
            Err(Error::InvalidEncoding)
        ));
        compressed[0] = 0x04;
        assert!(matches!(
            verify_pubkey_slice(&compressed),
            Err(Error::InvalidEncoding)
        ));

        uncompressed[0] = 0x01;
        assert!(matches!(
            verify_pubkey_slice(&uncompressed),
            Err(Error::InvalidEncoding)
        ));

        let mut too_long = [0u8; ECDSA_PUBLIC_KEY_SIZE + 1];
        too_long[0] = 0x04;
        assert!(matches!(
            verify_pubkey_slice(&too_long),
            Err(Error::InvalidEncoding)
        ));
    }

    #[test]
    fn test_verify_digest_vectors() {
        for v in VERIFY_VECTORS {
            let pubkey = v.pubkey();
            let sig = v.signature();
            let digest = v.digest();
            let result = verify_digest(v.curve, &pubkey, &sig, &digest);
            if v.valid {
                result.expect("valid vector failed verification");
                let uncompressed: EcdsaPublicKey = pubkey.as_slice().try_into().unwrap();
                let compressed = compress(&uncompressed);
                verify_digest(v.curve, &compressed, &sig, &digest)
                    .expect("valid vector failed with compressed key");
            } else {
                assert!(result.is_err(), "invalid vector was accepted");
            }
        }
    }

    #[test]
    fn test_verify_recover_vectors() {
        for v in VERIFY_VECTORS.iter().filter(|v| v.valid) {
            let expected: EcdsaPublicKey = v.pubkey().as_slice().try_into().unwrap();
            let sig = v.signature();
            let digest = v.digest();
            let recid = v
                .recid
                .unwrap_or_else(|| recover_recid(v.curve, &sig, &digest, &expected));

            let recovered = verify_recover(v.curve, &sig, recid, &digest).expect("recovery failed");
            assert_eq!(recovered, expected);

            // The other recovery ids must not yield this public key.
            for other in (0u8..=3u8).map(RecId::new).filter(|id| *id != recid) {
                match verify_recover(v.curve, &sig, other, &digest) {
                    Ok(pk) => assert_ne!(pk, expected),
                    Err(Error::SignatureVerificationFailed) => {}
                    Err(err) => panic!("unexpected error: {err:?}"),
                }
            }

            // Recovered key must also verify the signature.
            verify_digest(v.curve, &recovered, &sig, &digest)
                .expect("recovered key failed verification");
        }
    }

    #[test]
    fn test_verify_digest_rejects_bad_pubkey_encoding() {
        let v = &VERIFY_VECTORS[0];
        let sig = v.signature();
        let digest = v.digest();
        let pubkey = v.pubkey();

        assert!(matches!(
            verify_digest(v.curve, &[], &sig, &digest),
            Err(Error::InvalidEncoding)
        ));
        assert!(matches!(
            verify_digest(v.curve, &[0x01, 0x02, 0x03], &sig, &digest),
            Err(Error::InvalidEncoding)
        ));
        assert!(matches!(
            verify_digest(v.curve, &pubkey[..32], &sig, &digest),
            Err(Error::InvalidEncoding)
        ));
        let mut truncated_uncompressed = pubkey.clone();
        truncated_uncompressed.pop();
        assert!(matches!(
            verify_digest(v.curve, &truncated_uncompressed, &sig, &digest),
            Err(Error::InvalidEncoding)
        ));
    }

    #[test]
    fn test_verify_digest_rejects_wrong_digest_or_key() {
        let v = VERIFY_VECTORS
            .iter()
            .find(|v| v.valid)
            .expect("need a valid vector");
        let pubkey = v.pubkey();
        let sig = v.signature();
        let mut digest = v.digest();
        digest[0] ^= 1;
        assert!(verify_digest(v.curve, &pubkey, &sig, &digest).is_err());

        digest = v.digest();
        let mut wrong_key = pubkey;
        wrong_key[10] ^= 1;
        assert!(verify_digest(v.curve, &wrong_key, &sig, &digest).is_err());
    }

    #[test]
    fn test_verify_recover_rejects_invalid_signature() {
        let digest = hex_arr("ce0677bb30baa8cf067c88db9811f4333d131bf8bcf12fe7065d211dce971008");
        // r = 0
        let sig = hex_arr(
            "00000000000000000000000000000000000000000000000000000000000000000123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        );
        assert!(verify_recover(Curve::Secp256k1, &sig, RecId::new(0), &digest).is_err());
        // s = 0
        let sig = hex_arr(
            "00000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000000000000000000",
        );
        assert!(verify_recover(Curve::Secp256k1, &sig, RecId::new(0), &digest).is_err());
        // r >= order
        let sig = hex_arr(
            "fffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd03641410123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        );
        assert!(verify_recover(Curve::Secp256k1, &sig, RecId::new(0), &digest).is_err());
    }
}
