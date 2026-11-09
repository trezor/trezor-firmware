//! The verifier: holds proofs against a trusted root, from the root and the proofs alone. It
//! needs no storage and no allocation.
//!
//! `entry` answers one lookup: where a key sits in the tree with that root, as an [`Entry`],
//! and the root a change to it produces.
//!
//! The root the verifier is given is trusted by assumption. Whether the verifier holds a root
//! at all, and whether the root is current, is the caller's concern.
//!
//! TODO(ward): iteration with proofs (see the trie design note).

mod entry;

pub use entry::{Entry, OccupiedEntry, VacantEntry};
