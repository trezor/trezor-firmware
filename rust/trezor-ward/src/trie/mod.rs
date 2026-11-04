//! An authenticated crit-bit tree: a binary radix trie, which is where the module takes its
//! name, with the digests that make it a Merkle tree, which is why the prover's type is a
//! `Tree`. See the crate documentation for the structure, the encodings and the proof format.
//!
//! `common` holds what the prover and the verifier must agree on byte for byte.

pub mod common;

#[cfg(feature = "sha2")]
pub use common::Sha256;
pub use common::{
    BitPos, ByteArray, Error, HashFn, Hashable, Key, Leaf, Proof, Step, Steps, bit, branch_digest,
    crit_bit, empty_root, key_bits, key_len, leaf_digest,
};
