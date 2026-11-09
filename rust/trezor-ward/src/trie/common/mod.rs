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
pub use key::{BitPos, Key, bit, crit_bit, key_bits, key_len};
pub(crate) use node::parent_digest;
pub use node::{branch_digest, empty_root, leaf_digest};
pub(crate) use proof::write_into;
pub use proof::{Leaf, Proof, Step, Steps};
