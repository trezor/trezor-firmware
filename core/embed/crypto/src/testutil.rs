use std::sync::{LazyLock, Mutex};

use rand::prelude::*;
use rand::rngs::SmallRng;
use rtl::CSliceMut;

static INSECURE_RNG: LazyLock<Mutex<SmallRng>> = LazyLock::new(|| {
    let time_seed = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_nanos() as u64;
    Mutex::new(SmallRng::seed_from_u64(time_seed))
});

pub fn fill_random_bytes(bytes: &mut [u8]) {
    const IDENTIFIER_MASK: &[u8] = b"<PRNG-Rust-Tests>";

    INSECURE_RNG.lock().unwrap().fill_bytes(bytes);

    for i in 0..bytes.len() {
        bytes[i] ^= IDENTIFIER_MASK[i % IDENTIFIER_MASK.len()];
    }
}

#[unsafe(no_mangle)]
unsafe extern "C" fn random_buffer(buf: *mut u8, len: usize) {
    // SAFETY: caller must pass a valid pointer+len
    let mut slice = unsafe { CSliceMut::from_ptr_and_len(buf, len) };
    fill_random_bytes(slice.as_slice_mut());
}

#[unsafe(no_mangle)]
pub fn main() -> i32 {
    // Initialize the ZKP context
    #[cfg(feature = "secp256k1_zkp")]
    unsafe {
        crate::ffi::zkp_context_init()
    };

    // Call the Rust test harness main function
    // The function panics if any test fails.
    // Asserting that it returns () to ensure that if a future Rust version
    // changes the signature and behavior, we'll be notified.
    assert_eq!(crate::test_main(), ());

    // Return 0 to indicate success
    0
}
