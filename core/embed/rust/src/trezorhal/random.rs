extern "C" {
    // trezor-crypto/rand.h
    fn random_uniform(n: cty::uint32_t) -> cty::uint32_t;

    // trezor-crypto/rand.h
    fn random_buffer(buf: *mut cty::uint8_t, len: cty::size_t);
}

pub fn bytes(buf: &mut [u8]) {
    unsafe { random_buffer(buf.as_mut_ptr(), buf.len()) };
}

pub fn uniform(n: u32) -> u32 {
    unsafe { random_uniform(n) }
}

pub fn shuffle<T>(slice: &mut [T]) {
    // Fisher-Yates shuffle.
    for i in (1..slice.len()).rev() {
        let j = uniform(i as u32 + 1) as usize;
        slice.swap(i, j);
    }
}
