extern "C" {
    // trezor-crypto/rand.h
    fn random_uniform(n: u32) -> u32;
    fn random_buffer(buf: *const u8, len: u16);
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

pub fn bytes(buf: &mut [u8]) {
    unsafe { random_buffer(buf.as_mut_ptr(), buf.len() as u16) };
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_bytes() {
        let mut buf: [u8; 12] = [0; 12];
        bytes(&mut buf);

        let mut buf2: [u8; 12] = [0; 12];
        bytes(&mut buf2);

        assert_ne!(buf, buf2);
    }
}
