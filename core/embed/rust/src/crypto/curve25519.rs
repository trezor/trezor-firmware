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

    // No need for validation, every 32 byte array represents a valid point.
    // See https://cr.yp.to/ecdh/curve25519-20060209.pdf
    pub fn from_bytes(bytes: [u8; 32]) -> Self {
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
            let pk = Point::from_bytes(*pk.first_chunk::<32>().unwrap());

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

    #[cfg(feature = "layout_eckhart")] // TODO replace with feature = "thp"
    #[test]
    fn test_elligator2() {
        // https://elligator.org/vectors/curve25519_direct.vec
        const VECTORS: &[(&'static str, &'static str)] = &[
            (
                "0000000000000000000000000000000000000000000000000000000000000000",
                "0000000000000000000000000000000000000000000000000000000000000000",
            ),
            (
                "66665895c5bc6e44ba8d65fd9307092e3244bf2c18877832bd568cb3a2d38a12",
                "04d44290d13100b2c25290c9343d70c12ed4813487a07ac1176daa5925e7975e",
            ),
            (
                "673a505e107189ee54ca93310ac42e4545e9e59050aaac6f8b5f64295c8ec02f",
                "242ae39ef158ed60f20b89396d7d7eef5374aba15dc312a6aea6d1e57cacf85e",
            ),
            (
                "990b30e04e1c3620b4162b91a33429bddb9f1b70f1da6e5f76385ed3f98ab131",
                "998e98021eb4ee653effaa992f3fae4b834de777a953271baaa1fa3fef6b776e",
            ),
            (
                "341a60725b482dd0de2e25a585b208433044bc0a1ba762442df3a0e888ca063c",
                "683a71d7fca4fc6ad3d4690108be808c2e50a5af3174486741d0a83af52aeb01",
            ),
            (
                "922688fa428d42bc1fa8806998fbc5959ae801817e85a42a45e8ec25a0d7541a",
                "696f341266c64bcfa7afa834f8c34b2730be11c932e08474d1a22f26ed82410b",
            ),
            (
                "0d3b0eb88b74ed13d5f6a130e03c4ad607817057dc227152827c0506a538bb3a",
                "0b00df174d9fb0b6ee584d2cf05613130bad18875268c38b377e86dfefef177f",
            ),
            (
                "01a3ea5658f4e00622eeacf724e0bd82068992fae66ed2b04a8599be16662e35",
                "7ae4c58bc647b5646c9f5ae4c2554ccbf7c6e428e7b242a574a5a9c293c21f7e",
            ),
            (
                "1d991dff82a84afe97874c0f03a60a56616a15212fbe10d6c099aa3afcfabe35",
                "f81f235696f81df90ac2fc861ceee517bff611a394b5be5faaee45584642fb0a",
            ),
            (
                "185435d2b005a3b63f3187e64a1ef3582533e1958d30e4e4747b4d1d3376c728",
                "f938b1b320abb0635930bd5d7ced45ae97fa8b5f71cc21d87b4c60905c125d34",
            ),
        ];

        for (input, output) in VECTORS {
            let input_bytes = hex::decode(input).unwrap();
            let input_bytes = input_bytes.first_chunk::<32>().unwrap();
            let point = Point::map_to_curve_elligator2(input_bytes);
            assert_eq!(hex::encode(point.to_bytes()), *output);
        }
    }
}
