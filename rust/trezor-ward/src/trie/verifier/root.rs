//! The root: all the verifier holds of the map, and the one thing a change changes.

#[cfg(feature = "debug")]
use core::fmt;

use crate::trie::common::{HashFn, empty_root};

/// The root of a tree the caller trusts.
///
/// Every answer of the verifier is held against it: [`get`](Self::get) reads,
/// [`entry`](Self::entry) is the handle for a change, [`walk`](Self::walk) enumerates. A change
/// advances the root in place, through a handle that borrows it exclusively, so the next proof
/// can only be held against the tree as it then is. Not `Copy` for the same reason: a copy is
/// a second root that the changes pass by, so it is asked for with `clone`.
///
/// Whether the root is current, and storing it after a change, is the caller's concern.
pub struct Root<H: HashFn>(pub(super) H::Output);

impl<H: HashFn> Root<H> {
    /// The root with this digest, trusted on the caller's word.
    pub fn trusted(digest: H::Output) -> Self {
        Self(digest)
    }

    /// The root of the empty map.
    pub fn empty() -> Self {
        Self(empty_root::<H>())
    }

    /// The root's digest: what to store, sign or compare.
    pub fn digest(&self) -> &H::Output {
        &self.0
    }
}

// By hand for the reason given above the impls in `common/proof.rs`.

impl<H: HashFn> Clone for Root<H> {
    fn clone(&self) -> Self {
        Self(self.0)
    }
}

impl<H: HashFn> PartialEq for Root<H> {
    fn eq(&self, other: &Self) -> bool {
        self.0 == other.0
    }
}

impl<H: HashFn> Eq for Root<H> {}

#[cfg(feature = "debug")]
impl<H: HashFn> fmt::Debug for Root<H> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_tuple("Root").field(&self.0.as_ref()).finish()
    }
}
