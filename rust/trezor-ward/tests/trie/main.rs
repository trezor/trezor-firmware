//! Tests of the trie: the differential test of the two provers against the verifier, and the
//! hostile proofs the verifier must refuse.

use trezor_ward::trie::{Sha256, Tree};

mod differential;
mod hostile;

type Val = Vec<u8>;
type T<const N: usize> = Tree<[u8; N], Val, Sha256>;
