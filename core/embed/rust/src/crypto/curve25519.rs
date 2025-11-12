use zeroize::Zeroize;

use super::ffi;

pub struct Point {
    bytes: [u8; 32],
}

impl Drop for Point {
    fn drop(&mut self) {
        self.bytes.zeroize()
    }
}

pub struct Scalar {
    bytes: [u8; 32],
}

impl Drop for Scalar {
    fn drop(&mut self) {
        self.bytes.zeroize()
    }
}

impl Scalar {
    pub fn from_bytes(bytes: [u8; 32]) -> Self {
        let mut res = Self { bytes };
        // taken from https://cr.yp.to/ecdh.html
        res.bytes[0] &= 248;
        res.bytes[31] &= 127;
        res.bytes[31] |= 64;
        res
    }

    #[cfg(feature = "test")]
    pub fn generate() -> Self {
        let mut bytes = [0u8; 32];
        crate::trezorhal::random::bytes(&mut bytes);
        Self::from_bytes(bytes)
    }
}

impl Point {
    pub fn from_secret(secret: &Scalar) -> Self {
        let mut res = Self { bytes: [0u8; 32] };
        let dest = res.bytes.as_mut_ptr();
        let secret_bytes = secret.bytes.as_ptr();
        // SAFETY: ffi
        unsafe {
            ffi::curve25519_scalarmult_basepoint(dest, secret_bytes);
        }
        res
    }

    pub fn multiply(&self, secret: &Scalar) -> Self {
        let mut res = Self { bytes: [0u8; 32] };
        let dest = res.bytes.as_mut_ptr();
        let secret_bytes = secret.bytes.as_ptr();
        let point_bytes = self.bytes.as_ptr();
        // SAFETY: ffi
        unsafe { ffi::curve25519_scalarmult(dest, secret_bytes, point_bytes) }
        res
    }

    /// SAFETY: not all byte arrays are valid points - caller must ensure the
    /// input was obtained from `Point::to_bytes()`.
    pub unsafe fn from_bytes(bytes: [u8; 32]) -> Self {
        Self { bytes }
    }

    pub fn to_bytes(&self) -> [u8; 32] {
        self.bytes
    }

    pub fn map_to_curve_elligator2(input: &[u8; 32]) -> Self {
        let mut res = Self { bytes: [0u8; 32] };
        let dest = res.bytes.as_mut_ptr();
        // SAFETY: ffi
        let ok = unsafe { ffi::map_to_curve_elligator2_curve25519(input.as_ptr(), dest) };
        assert!(ok); // always returns true
        res
    }
}

#[cfg(test)]
mod test {
    use super::*;

    #[test]
    fn test_generate() {
        for _ in 0..100 {
            let bytes = Scalar::generate().bytes;
            assert!(bytes[0] & 7 == 0 && bytes[31] & 128 == 0 && bytes[31] & 64 == 64)
        }
    }

    #[test]
    fn test_multiply() {
        const VECTORS: &[(&'static str, &'static str, &'static str)] = &[(
            "38c9d9b17911de26ed812f5cc19c0029e8d016bcbc6078bc9db2af33f1761e4a",
            "311b6248af8dabec5cc81eac5bf229925f6d218a12e0547fb1856e015cc76f5d",
            "a93dbdb23e5c99da743e203bd391af79f2b83fb8d0fd6ec813371c71f08f2d4d",
        )];

        for (sk, pk, session) in VECTORS {
            let sk = hex::decode(sk).unwrap();
            let sk = Scalar::from_bytes(*sk.first_chunk::<32>().unwrap());

            let pk = hex::decode(pk).unwrap();
            let pk = unsafe { Point::from_bytes(*pk.first_chunk::<32>().unwrap()) };

            let session = hex::decode(session).unwrap();
            let session = session.first_chunk::<32>().unwrap();

            let session2 = pk.multiply(&sk);
            assert_eq!(session2.to_bytes(), *session);
        }
    }

    #[test]
    fn test_multiply_random() {
        for _ in 0..100 {
            let sk1 = Scalar::generate();
            let sk2 = Scalar::generate();
            let pk1 = Point::from_secret(&sk1);
            let pk2 = Point::from_secret(&sk2);
            let session1 = pk2.multiply(&sk1);
            let session2 = pk1.multiply(&sk2);
            assert_eq!(session1.to_bytes(), session2.to_bytes());
        }
    }

    #[test]
    fn test_clamping() {
        let mut bytes1 = [0u8; 32];
        crate::trezorhal::random::bytes(&mut bytes1);

        let mut bytes2 = bytes1;
        // flipping the bits affected by clamping should not change the results
        bytes2[0] |= !0xf8;
        bytes2[31] |= !0x7f;
        bytes2[31] &= !0x40;

        let sk1 = Scalar::from_bytes(bytes1);
        let sk2 = Scalar::from_bytes(bytes2);

        let pk1 = Point::from_secret(&sk1);
        let pk2 = Point::from_secret(&sk2);
        assert_eq!(pk1.to_bytes(), pk2.to_bytes());

        let sk3 = Scalar::generate();
        let pk3 = Point::from_secret(&sk3);
        let res1 = pk3.multiply(&sk1);
        let res2 = pk3.multiply(&sk2);
        assert_eq!(res1.to_bytes(), res2.to_bytes());
    }
}
