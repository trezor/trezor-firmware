pub fn uniform(n: u32) -> u32 {
    unsafe { super::ffi::random_uniform(n) }
}

pub fn shuffle<T>(slice: &mut [T]) {
    // Fisher-Yates shuffle.
    for i in (1..slice.len()).rev() {
        let j = uniform(i as u32 + 1) as usize;
        slice.swap(i, j);
    }
}

/// Returns a random number in the range [min, max].
pub fn uniform_between(min: u32, max: u32) -> u32 {
    assert!(max >= min);
    uniform(max - min + 1) + min
}

/// Returns a random number in the range [min, max] except one `except` number.
pub fn uniform_between_except(min: u32, max: u32, except: u32) -> u32 {
    assert!(max > min);
    // Generate uniform_between as long as it is not except
    loop {
        let rand = uniform_between(min, max);
        if rand != except {
            return rand;
        }
    }
}

pub fn bytes(dest: &mut [u8]) {
    unsafe { super::ffi::random_buffer(dest.as_mut_ptr(), dest.len()) }
}

pub fn bytes_array<const N: usize>() -> [u8; N] {
    let mut res = [0u8; N];
    bytes(&mut res);
    res
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn uniform_between_test() {
        for _ in 0..10 {
            assert!((10..=11).contains(&uniform_between(10, 11)));
            assert!((10..=12).contains(&uniform_between(10, 12)));
            assert!((256..=512).contains(&uniform_between(256, 512)));
        }
    }

    #[test]
    fn uniform_between_except_test() {
        for _ in 0..10 {
            assert!(uniform_between_except(10, 12, 11) != 11);
        }
    }

    #[test]
    fn bytes_array_initialized() {
        let ar = bytes_array::<32>();
        assert!(ar.iter().any(|b| b != 0));
    }
}
