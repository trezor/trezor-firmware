//! Proofs a host could tamper with, each refused with its own error.

use std::ops::Range;

use trezor_ward::trie::{Error, Proof, Root, Sha256};

use crate::T;

const A: [u8; 1] = [0b0000_0000];
const B: [u8; 1] = [0b0000_1111];
const C: [u8; 1] = [0b0100_0000];
const D: [u8; 1] = [0b1000_0000];
/// Absent; its lookup ends at A, taking the same turns.
const E: [u8; 1] = [0b0010_0000];

/// The widths of a proof over one-byte keys and SHA-256: a leaf is a key and a digest, a step
/// is a crit bit, one byte for such a key, and a digest.
const LEAF_LEN: usize = 1 + 32;
const CRIT_BIT_LEN: usize = 1;
const STEP_LEN: usize = CRIT_BIT_LEN + 32;

/// Byte offset of step `i`, leaf-to-root.
const fn step(i: usize) -> usize {
    LEAF_LEN + i * STEP_LEN
}

fn crit_bit(i: usize) -> Range<usize> {
    step(i)..step(i) + CRIT_BIT_LEN
}

fn sibling(i: usize) -> Range<usize> {
    step(i) + CRIT_BIT_LEN..step(i + 1)
}

/// The host's answer to the device's lookup of `key`: a proof, held against the root of the
/// four-leaf map of the verifier's pinned vectors. A's own path is its leaf, then steps at
/// bits 4, 1 and 0.
struct Lookup {
    tree: T<1>,
    key: [u8; 1],
    proof: Vec<u8>,
}

impl Lookup {
    /// The genuine answer: `key`'s own path.
    fn of(key: [u8; 1]) -> Self {
        let tree = T::<1>::from_entries(
            [(A, b"a"), (B, b"b"), (C, b"c"), (D, b"d")].map(|(key, value)| (key, value.to_vec())),
        );
        let proof = tree.prove(&key).into_bytes();
        Self { tree, key, proof }
    }

    /// The proof with `tamper` applied.
    fn tampered(mut self, tamper: impl FnOnce(&mut Vec<u8>)) -> Self {
        tamper(&mut self.proof);
        self
    }

    /// The proof replaced by `other`'s genuine path.
    fn with_path_of(mut self, other: [u8; 1]) -> Self {
        self.proof = self.tree.prove(&other).into_bytes();
        self
    }

    fn verify(&self) -> Result<(), Error> {
        let root = Root::trusted(self.tree.root());
        let proof = Proof::<_, [u8; 1], Sha256>::parse(&self.proof[..])?;
        root.get(&self.key, &proof).map(drop)
    }

    #[track_caller]
    fn accepted(&self) {
        assert_eq!(self.verify(), Ok(()));
    }

    #[track_caller]
    fn refused(&self, error: Error) {
        assert_eq!(self.verify(), Err(error));
    }
}

/// Holds the prover to the widths above: D's path is one step and A's is three, and A's crit
/// bits lie where `crit_bit` points.
#[test]
fn genuine_proofs_have_this_layout() {
    assert_eq!(Lookup::of(D).proof.len(), step(1));
    let proof = Lookup::of(A).proof;
    assert_eq!(proof.len(), step(3));
    let crit_bits: Vec<&[u8]> = (0..3).map(|i| &proof[crit_bit(i)]).collect();
    assert_eq!(crit_bits, [[4], [1], [0]]);
}

#[test]
fn the_genuine_proof_passes() {
    Lookup::of(A).accepted();
}

#[test]
fn truncated() {
    Lookup::of(A)
        .tampered(|p| {
            p.pop();
        })
        .refused(Error::Length);
}

#[test]
fn padded() {
    Lookup::of(A).tampered(|p| p.push(0)).refused(Error::Length);
}

#[test]
fn steps_reordered() {
    Lookup::of(A)
        .tampered(|p| p[step(0)..step(2)].rotate_left(STEP_LEN))
        .refused(Error::Shape);
}

#[test]
fn crit_bit_repeated() {
    Lookup::of(A)
        .tampered(|p| p.copy_within(crit_bit(0), crit_bit(1).start))
        .refused(Error::Shape);
}

#[test]
fn crit_bit_beyond_the_key() {
    // A one-byte key has bits 0 to 7.
    Lookup::of(A)
        .tampered(|p| p[crit_bit(0)].copy_from_slice(&[8]))
        .refused(Error::Shape);
}

#[test]
fn step_dropped() {
    Lookup::of(A)
        .tampered(|p| p.truncate(step(2)))
        .refused(Error::RootMismatch);
}

/// E takes the same turns as A, so only the leaf digest tells them apart.
#[test]
fn terminal_leaf_renamed() {
    Lookup::of(A)
        .tampered(|p| p[0] = E[0])
        .refused(Error::RootMismatch);
}

/// A is all zeros, so the turn at bit 5 is the same as at bit 4: only the branch digest,
/// which includes the crit bit, tells them apart.
#[test]
fn crit_bit_relabelled() {
    Lookup::of(A)
        .tampered(|p| p[crit_bit(0)].copy_from_slice(&[5]))
        .refused(Error::RootMismatch);
}

#[test]
fn sibling_from_another_step() {
    Lookup::of(A)
        .tampered(|p| p.copy_within(sibling(1), sibling(0).start))
        .refused(Error::RootMismatch);
}

#[test]
fn empty_proof_against_a_non_empty_root() {
    Lookup::of(A)
        .tampered(|p| p.clear())
        .refused(Error::RootMismatch);
}

/// B's genuine path branches on bit 4, where A and B differ.
#[test]
fn another_keys_path() {
    Lookup::of(A).with_path_of(B).refused(Error::OffPath);
}
