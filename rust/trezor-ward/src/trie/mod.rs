//! An authenticated crit-bit tree: a binary radix trie, which is where the module takes its
//! name, with the digests that make it a Merkle tree, which is why the prover's type is a
//! `Tree`. See the crate documentation for the structure, the encodings and the proof format.
//!
//! `common` holds what the prover and the verifier must agree on byte for byte. `verifier`
//! holds a proof against a trusted root and advances the root by the change a proof supports,
//! from the root and the proof alone, and walks the entries in key order one proof at a time.
//! `prover` (feature `use_std`) holds the whole map and serves proofs.

pub mod common;
#[cfg(feature = "use_std")]
pub mod prover;
pub mod verifier;

#[cfg(feature = "sha2")]
pub use common::Sha256;
pub use common::{ByteArray, Error, HashFn, Hashable, Key, Proof};
#[cfg(feature = "use_std")]
pub use prover::Tree;
pub use verifier::{Entry, OccupiedEntry, Root, VacantEntry, Walk};
