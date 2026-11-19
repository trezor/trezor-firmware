//! Merkle tree over byte values, compatible with `trezorlib.merkle_tree` and
//! the on-device verifier (`crypto::merkle::merkle_root`).
//!
//! - Leaf entries are hashes of `0x00 || value`.
//! - Internal entries are hashes of `0x01 || min(left, right) || max(left, right)`,
//!   so a proof is a plain list of sibling hashes, with no left/right flags.
//! - Leaves are ordered by their hash and the tree is balanced: the first leaves
//!   are pushed one level deeper so that the level above them is a power of two.
//!   Any two proofs differ in length by at most one.

use sha2::{Digest, Sha256};
use std::collections::HashMap;

pub fn leaf_hash(value: &[u8]) -> [u8; 32] {
    Sha256::new()
        .chain_update([0x00])
        .chain_update(value)
        .finalize()
        .into()
}

pub fn internal_hash(left: &[u8; 32], right: &[u8; 32]) -> [u8; 32] {
    Sha256::new()
        .chain_update([0x01])
        .chain_update(left.min(right))
        .chain_update(left.max(right))
        .finalize()
        .into()
}

/// Reconstructs the root hash of a tree that contains `value` with `proof`.
pub fn evaluate_proof(value: &[u8], proof: &[[u8; 32]]) -> [u8; 32] {
    proof
        .iter()
        .fold(leaf_hash(value), |hash, entry| internal_hash(&hash, entry))
}

pub struct MerkleTree {
    root_hash: [u8; 32],
    proofs: HashMap<[u8; 32], Vec<[u8; 32]>>,
}

struct Subtree {
    hash: [u8; 32],
    leaves: Vec<usize>,
}

impl MerkleTree {
    /// Builds the tree, or returns `None` if there are no values.
    pub fn new<V: AsRef<[u8]>>(values: impl IntoIterator<Item = V>) -> Option<Self> {
        let mut leaf_hashes: Vec<[u8; 32]> = values
            .into_iter()
            .map(|value| leaf_hash(value.as_ref()))
            .collect();
        leaf_hashes.sort();

        let mut proofs = vec![Vec::new(); leaf_hashes.len()];
        let mut level: Vec<Subtree> = leaf_hashes
            .iter()
            .enumerate()
            .map(|(index, &hash)| Subtree {
                hash,
                leaves: vec![index],
            })
            .collect();

        if level.len() > 1 {
            let capacity = level.len().next_power_of_two();
            let split = 2 * level.len() - capacity;
            let shallow = level.split_off(split);
            level = pair_up(level, &mut proofs);
            level.extend(shallow);

            while level.len() > 1 {
                level = pair_up(level, &mut proofs);
            }
        }

        let root_hash = level.first()?.hash;
        Some(MerkleTree {
            root_hash,
            proofs: leaf_hashes.into_iter().zip(proofs).collect(),
        })
    }

    pub fn root_hash(&self) -> [u8; 32] {
        self.root_hash
    }

    /// Returns the proof for `value`, or `None` if it is not in the tree.
    pub fn proof(&self, value: &[u8]) -> Option<&[[u8; 32]]> {
        self.proofs.get(&leaf_hash(value)).map(Vec::as_slice)
    }
}

fn pair_up(nodes: Vec<Subtree>, proofs: &mut [Vec<[u8; 32]>]) -> Vec<Subtree> {
    let mut nodes = nodes.into_iter();
    let mut parents = Vec::new();
    while let Some(left) = nodes.next() {
        let right = nodes.next().expect("levels are paired up in full");
        for &leaf in &left.leaves {
            proofs[leaf].push(right.hash);
        }
        for &leaf in &right.leaves {
            proofs[leaf].push(left.hash);
        }
        let mut leaves = left.leaves;
        leaves.extend(right.leaves);
        parents.push(Subtree {
            hash: internal_hash(&left.hash, &right.hash),
            leaves,
        });
    }
    parents
}

#[cfg(test)]
mod tests {
    use super::*;

    // Vectors from python/tests/test_merkle_tree.py and roots computed with
    // trezorlib.merkle_tree.

    fn from_hex(hex: &str) -> [u8; 32] {
        let mut out = [0u8; 32];
        for (i, byte) in out.iter_mut().enumerate() {
            *byte = u8::from_str_radix(&hex[2 * i..2 * i + 2], 16).unwrap();
        }
        out
    }

    fn values(count: usize) -> Vec<Vec<u8>> {
        (0..count)
            .map(|i| format!("value-{i}").into_bytes())
            .collect()
    }

    #[test]
    fn node_hashes() {
        let hello = leaf_hash(b"hello");
        let world = leaf_hash(b"world");
        assert_eq!(
            hello,
            from_hex("8a2a5c9b768827de5a9552c38a044c66959c68f6d2f21b5260af54d2f87db827")
        );
        assert_eq!(
            internal_hash(&hello, &world),
            from_hex("24233339aadcedf287d262413f03c028eb8db397edd32a2878091151b99bf20f")
        );
        assert_eq!(
            internal_hash(&internal_hash(&hello, &world), &leaf_hash(b"!")),
            from_hex("c3727420dc97c0dbd89678ee195957e44cfa69f5759b395a07bc171b21468633")
        );
    }

    #[test]
    fn empty_tree() {
        assert!(MerkleTree::new(Vec::<Vec<u8>>::new()).is_none());
    }

    #[test]
    fn one_value() {
        let tree = MerkleTree::new([b"Merkle"]).unwrap();
        assert_eq!(tree.root_hash(), leaf_hash(b"Merkle"));
        assert_eq!(tree.proof(b"Merkle").unwrap(), &[] as &[[u8; 32]]);
    }

    #[test]
    fn two_values() {
        let tree = MerkleTree::new([b"Haber".as_slice(), b"Stornetta"]).unwrap();
        let haber = leaf_hash(b"Haber");
        let stornetta = leaf_hash(b"Stornetta");
        assert_eq!(tree.root_hash(), internal_hash(&haber, &stornetta));
        assert_eq!(tree.proof(b"Haber").unwrap(), [stornetta]);
        assert_eq!(tree.proof(b"Stornetta").unwrap(), [haber]);
    }

    #[test]
    fn three_values() {
        let tree = MerkleTree::new([b"Andersen".as_slice(), b"Wuille", b"Maxwell"]).unwrap();
        let andersen = leaf_hash(b"Andersen");
        let maxwell = leaf_hash(b"Maxwell");
        let wuille = leaf_hash(b"Wuille");
        let deep = internal_hash(&maxwell, &wuille);
        assert_eq!(tree.root_hash(), internal_hash(&deep, &andersen));
        assert_eq!(tree.proof(b"Andersen").unwrap(), [deep]);
        assert_eq!(tree.proof(b"Maxwell").unwrap(), [wuille, andersen]);
        assert_eq!(tree.proof(b"Wuille").unwrap(), [maxwell, andersen]);
    }

    #[test]
    fn uneven_trees_match_python() {
        let five = MerkleTree::new(values(5)).unwrap();
        assert_eq!(
            five.root_hash(),
            from_hex("036de634959061ca405410d7c9f67f063844773924893004ea4c0498f5bad977")
        );
        let six = MerkleTree::new(values(6)).unwrap();
        assert_eq!(
            six.root_hash(),
            from_hex("410d5f6d907abc76f407da7cec62057478d96a946a8679002d82dbae1c3e13f4")
        );
    }

    #[test]
    fn missing_value_has_no_proof() {
        let tree = MerkleTree::new(values(3)).unwrap();
        assert!(tree.proof(b"missing").is_none());
    }

    #[test]
    fn proofs_evaluate_to_root_and_tree_is_balanced() {
        for count in 1..34 {
            let values = values(count);
            let tree = MerkleTree::new(&values).unwrap();
            let lengths: Vec<usize> = values
                .iter()
                .map(|value| {
                    let proof = tree.proof(value).unwrap();
                    assert_eq!(evaluate_proof(value, proof), tree.root_hash());
                    proof.len()
                })
                .collect();
            let (min, max) = (lengths.iter().min(), lengths.iter().max());
            assert!(max.unwrap() - min.unwrap() <= 1, "{count} values");
        }
    }
}
