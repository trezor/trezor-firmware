//! The verifier: holds proofs against a trusted root, from the root and the proofs alone. It
//! needs no storage and no allocation.
//!
//! `entry` answers one lookup: where a key sits in the tree with that root, as an [`Entry`],
//! and the root a change to it produces. `walk` enumerates the entries in key order, one
//! proof per entry, as a [`Walk`], so that a host cannot hide one.
//!
//! The root the verifier is given is trusted by assumption. Whether the verifier holds a root
//! at all, and whether the root is current, is the caller's concern; so is which entry a walk
//! stands at.

mod entry;
mod walk;

pub use entry::{Entry, OccupiedEntry, VacantEntry};
pub use walk::Walk;
