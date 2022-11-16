//! Generates Poseidon round constants according to apendix F of article
//!
//! POSEIDON: A New Hash Function for Zero-Knowledge Proof Systems
//! <https://eprint.iacr.org/2019/458>
//!
//! for paraments defined in
//! <https://zips.z.cash/protocol/protocol.pdf#poseidonhash>

use core::cmp::Ordering;
use pasta_curves::Fp;

/// Size of Pallas base field in little-endian
const MODULUS: [u64; 4] = [
    0x992d30ed00000001,
    0x224698fc094cf91b,
    0x0000000000000000,
    0x4000000000000000,
];

fn is_less_then_modulus(number: &[u64; 4]) -> bool {
    for i in (0..4).rev() {
        match number[i].cmp(&MODULUS[i]) {
            Ordering::Less => return true,
            Ordering::Greater => return false,
            Ordering::Equal => continue,
        };
    }
    false // numbers are equal
}

// the newest bit is the lowest bit of `reg0`
// the oldest bit is the highest bit of `reg2`
pub struct ConstantsGenerator {
    reg0: u32,
    reg1: u32,
    reg2: u16,
}

impl ConstantsGenerator {
    pub fn new() -> Self {
        // LSFR state is precomputed as follows:
        // 1. initialize LSFR according to the step 1
        //    with parameters from the Zcash protocol paper §5.4.1.10
        // 2. drop first 160 bits according to the step 3
        // 3. convert the LSFR state from Fibonacci representation to Galois repr.
        ConstantsGenerator {
            reg0: 0x7858ff5e,
            reg1: 0xb8da546e,
            reg2: 0xfbfe,
        }
    }

    /// Returns next LSFR bit
    fn next_bit(&mut self) -> u8 {
        // pop the oldest bit
        let new_bit = (self.reg2 >> 15) as u8;
        // shift register
        self.reg2 = (self.reg2 << 1) | (self.reg1 >> 31) as u16;
        self.reg1 = (self.reg1 << 1) | (self.reg0 >> 31);
        self.reg0 <<= 1;
        // add feedback
        if new_bit == 1 {
            // s_80 = s_62 + s_51 + s_38 + s_23 + s_13 + s_0
            self.reg0 ^= 0b00000000100000000010000000000001;
            self.reg1 ^= 0b01000000000010000000000001000000;
        }
        new_bit
    }

    /// Filter bits according to the step 4
    fn next_filtered_bit(&mut self) -> u8 {
        loop {
            let b1 = self.next_bit();
            let b2 = self.next_bit();
            if b1 == 1 {
                break b2;
            }
        }
    }

    fn next_digit(&mut self, n: usize) -> u64 {
        (0..n).fold(0u64, |acc, _| (acc << 1) + self.next_filtered_bit() as u64)
    }

    fn next_field_element(&mut self) -> Fp {
        loop {
            // sample the number in the big-endian
            let mut digits = [
                self.next_digit(63),
                self.next_digit(64),
                self.next_digit(64),
                self.next_digit(64),
            ];
            // then convert it to the little-endian
            digits.reverse();
            if is_less_then_modulus(&digits) {
                break Fp::from_raw(digits);
            }
        }
    }
}

impl Iterator for ConstantsGenerator {
    type Item = [Fp; 3];

    fn next(&mut self) -> Option<[Fp; 3]> {
        Some([
            self.next_field_element(),
            self.next_field_element(),
            self.next_field_element(),
        ])
    }
}
