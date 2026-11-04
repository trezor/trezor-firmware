//! Proofs a host could tamper with, each refused with its own error.

use std::ops::Range;

use trezor_ward::trie::{BitPos, Error, Leaf, Proof, Sha256, Step, key_bits};

use crate::T;

const A: [u8; 1] = [0b0000_0000];
const B: [u8; 1] = [0b0000_1111];
const C: [u8; 1] = [0b0100_0000];
const D: [u8; 1] = [0b1000_0000];
/// Absent; its lookup ends at A, taking the same turns.
const E: [u8; 1] = [0b0010_0000];

/// Byte offset of step `i` of a proof over one-byte keys, leaf-to-root.
const fn step(i: usize) -> usize {
    Leaf::<[u8; 1], Sha256>::LEN + i * Step::<Sha256>::LEN
}

fn crit_bit(i: usize) -> Range<usize> {
    step(i)..step(i) + BitPos::LEN
}

fn sibling(i: usize) -> Range<usize> {
    step(i) + BitPos::LEN..step(i + 1)
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
        Proof::<_, [u8; 1], Sha256>::parse(&self.proof[..])
            .and_then(|proof| proof.verify(&self.tree.root(), &self.key).map(drop))
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

#[test]
fn the_genuine_proof_passes() {
    let lookup = Lookup::of(A);
    assert_eq!(lookup.proof.len(), step(3));
    lookup.accepted();
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
        .tampered(|p| p[step(0)..step(2)].rotate_left(Step::<Sha256>::LEN))
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
    let beyond = BitPos::new(key_bits::<[u8; 1]>() as u16).to_bytes();
    Lookup::of(A)
        .tampered(|p| p[crit_bit(0)].copy_from_slice(&beyond))
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
        .tampered(|p| p[crit_bit(0)].copy_from_slice(&BitPos::new(5).to_bytes()))
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
