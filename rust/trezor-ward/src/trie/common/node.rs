//! The node encodings: the Merkle construction every root commits to.
//!
//! ```text
//! leaf   = H(0x00 ‖ key ‖ value_digest)
//! branch = H(0x01 ‖ crit_bit ‖ left ‖ right)
//! empty  = H(0x02)
//! value  = H(0x03 ‖ bytes)        any `AsRef<[u8]>` value, see `Hashable`
//! ```
//!
//! `key` is the key's bytes, `crit_bit` a [`BitPos`] as [`BitPos::to_bytes`] writes it, and the
//! rest are digests. Every operand has a fixed width, so the preimages need no separators. The three node tags
//! make a leaf, a branch and the empty root unforgeable from one another: a leaf can never be
//! read as a branch or the reverse, and no fold can produce the empty root. A node's depth is
//! not part of its digest, so a subtree keeps its digest when a change moves it up or down.

use super::hash::HashFn;
use super::key::{BitPos, Key};

pub(crate) const TAG_LEAF: u8 = 0x00;
pub(crate) const TAG_BRANCH: u8 = 0x01;
pub(crate) const TAG_EMPTY: u8 = 0x02;
pub(crate) const TAG_VALUE: u8 = 0x03;

/// The root of the empty map.
pub fn empty_root<H: HashFn>() -> H::Output {
    H::digest(&[&[TAG_EMPTY]])
}

/// The digest of a leaf.
pub fn leaf_digest<K: Key, H: HashFn>(key: &K, value: &H::Output) -> H::Output {
    H::digest(&[&[TAG_LEAF], key.as_bytes().as_ref(), value.as_ref()])
}

/// The digest of a branch. Children are positional: `left` holds the keys whose crit bit is 0.
pub fn branch_digest<H: HashFn>(
    crit_bit: BitPos,
    left: &H::Output,
    right: &H::Output,
) -> H::Output {
    H::digest(&[
        &[TAG_BRANCH],
        &crit_bit.to_bytes(),
        left.as_ref(),
        right.as_ref(),
    ])
}

#[cfg(test)]
mod tests {
    use super::super::hash::Sha256;
    use super::*;

    #[test]
    fn empty_root_is_sha256_of_the_tag() {
        // sha256(0x02), derived independently with Python's hashlib
        assert_eq!(
            empty_root::<Sha256>(),
            hex("dbc1b4c900ffe48d575b5da5c638040125f65db0fe3e24494b76ea986457d986")
        );
    }

    #[test]
    fn children_are_positional() {
        let (a, b) = ([0u8; 32], [1u8; 32]);
        assert_ne!(
            branch_digest::<Sha256>(BitPos::new(0), &a, &b),
            branch_digest::<Sha256>(BitPos::new(0), &b, &a)
        );
    }

    #[test]
    fn the_crit_bit_is_in_the_digest() {
        let (a, b) = ([0u8; 32], [1u8; 32]);
        assert_ne!(
            branch_digest::<Sha256>(BitPos::new(1), &a, &b),
            branch_digest::<Sha256>(BitPos::new(2), &a, &b)
        );
    }

    fn hex(s: &str) -> [u8; 32] {
        let mut out = [0u8; 32];
        for (i, byte) in out.iter_mut().enumerate() {
            *byte = u8::from_str_radix(&s[2 * i..2 * i + 2], 16).unwrap();
        }
        out
    }
}
