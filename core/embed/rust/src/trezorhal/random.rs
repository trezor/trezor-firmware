use rand::{Error, RngCore};

extern "C" {
    // trezor-crypto/rand.h
    fn random_uniform(n: u32) -> u32;
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

pub struct HardwareRandomness;

impl RngCore for HardwareRandomness {
    fn next_u32(&mut self) -> u32 {
        uniform(u32::MAX)
    }

    fn next_u64(&mut self) -> u64 {
        (self.next_u32() as u64) + ((self.next_u32() as u64) << 32)
    }

    fn fill_bytes(&mut self, dest: &mut [u8]) {
        unimplemented!()
        //impls::fill_bytes_via_next(self, dest)
    }

    fn try_fill_bytes(&mut self, dest: &mut [u8]) -> Result<(), Error> {
        unimplemented!()
        //Ok(self.fill_bytes(dest))
    }
}
