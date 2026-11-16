//! The verifier: holds proofs against a trusted root, from the root and the proofs alone. It
//! needs no storage and no allocation.
//!
//! Everything starts from a [`Root`], the root the caller trusts. [`Root::entry`] answers one
//! lookup: where a key sits in the tree with that root, as an [`Entry`], through which a
//! change advances the root; [`Root::get`] is the same lookup for reading. [`Root::walk`]
//! enumerates the entries in key order, one proof per entry, as a [`Walk`], so that a host
//! cannot hide one.
//!
//! The root the verifier is given is trusted by assumption. Whether the verifier holds a root
//! at all, whether the root is current, and storing it after a change, is the caller's
//! concern; so is which entry a walk stands at.

#![expect(
    clippy::type_complexity,
    reason = "an entry's type says how it holds the root and the proof; an alias would hide that"
)]

mod entry;
mod root;
mod walk;

pub use entry::{Entry, OccupiedEntry, VacantEntry};
pub use root::Root;
pub use walk::Walk;
