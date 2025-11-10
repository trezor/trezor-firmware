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
        // It would make sense to perform clamping here but instead we rely on
        // curve25519_scalarmult* to do it as the first thing.
        Self { bytes }
    }
}

impl Point {
    pub fn from_secret(secret: Scalar) -> Self {
        let mut res = Self { bytes: [0u8; 32] };
        let dest = res.bytes.as_mut_ptr();
        let secret_bytes = secret.bytes.as_ptr();
        // SAFETY: ffi
        unsafe {
            ffi::curve25519_scalarmult_basepoint(dest, secret_bytes);
        }
        res
    }

    pub fn multiply(&self, secret: Scalar) -> Self {
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
