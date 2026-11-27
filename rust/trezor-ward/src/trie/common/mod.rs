//! What the prover and the verifier must agree on, byte for byte: the trait contracts for the
//! hash function, keys and values; the node encodings; and the proof format. Nothing else
//! belongs here.

mod array;
mod error;
mod hash;
mod key;
mod node;
mod proof;

pub use array::ByteArray;
pub use error::Error;
#[cfg(feature = "sha2")]
pub use hash::Sha256;
pub use hash::{HashFn, Hashable};
pub use key::Key;
pub(crate) use key::{BitPos, Side, bit, crit_bit};
#[cfg(feature = "use_std")]
pub(crate) use node::branch_digest;
pub(crate) use node::{empty_root, leaf_digest, parent_digest};
pub use proof::Proof;
pub(crate) use proof::{Leaf, Step, write_into};
