use heapless::Vec;

extern "C" {
    // trezor-crypto/rand.h
    fn random_uniform(n: u32) -> u32;
    fn random_buffer(buf: *const u8, len: u16);
}

// TODO: what is the sensible max size not to allocate too much every time?
const MAX_LEN: usize = u8::MAX as usize;

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

pub fn get_random_bytes(len: u8) -> Vec<u8, MAX_LEN> {
    let mut buf: [u8; MAX_LEN] = [0; MAX_LEN];
    unsafe { random_buffer(&mut buf as *mut _, len as u16) };

    let result = &buf[..len as usize];
    result.iter().cloned().collect()
}
