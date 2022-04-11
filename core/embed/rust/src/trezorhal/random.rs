use heapless::Vec;

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

// TODO: it seems it gets the same results every time? (could be seeded with
// device seed)
pub fn get_random_bytes<const N: usize>() -> Vec<u8, N> {
    let mut buf: [u8; N] = [0; N];
    unsafe { random_buffer(&mut buf as *mut _, N as u16) };

    (&buf).iter().cloned().collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_get_random_bytes() {
        let result = get_random_bytes::<12>();
        assert_eq!(result.len(), 12);

        let result_2 = get_random_bytes::<12>();
        assert_eq!(result_2.len(), 12);

        assert_ne!(result, result_2);
    }
}
