//! One lookup, held against the root: [`Proof::verify`] answers where a key sits in the tree
//! with that root, as an [`Entry`], occupied by a value or vacant, and derives the root a
//! change produces from the root and the proof alone. The entry is the only way to derive a
//! new root, so nothing is ever derived from an unverified proof. The three changes are
//! reachable only from the variant where they make sense: a vacant entry can be inserted
//! into, an occupied one can be replaced or removed.

use core::fmt;

use crate::trie::common::{
    BitPos, Error, HashFn, Hashable, Key, Leaf, Proof, Step, bit, crit_bit, empty_root,
    leaf_digest, parent_digest,
};

/// Where a key sits in the tree with a given root, as proven by a proof.
///
/// Modelled on `std::collections::hash_map::Entry`: the lookup result and the handle for the
/// change in one. Obtained from [`Proof::verify`].
pub enum Entry<'a, K: Key, H: HashFn> {
    /// The key is present.
    Occupied(OccupiedEntry<'a, K, H>),
    /// The key is absent.
    Vacant(VacantEntry<'a, K, H>),
}

/// A key proven present: its value digest, and the handle to replace or remove it.
pub struct OccupiedEntry<'a, K: Key, H: HashFn> {
    proof: Proof<&'a [u8], K, H>,
    key: K,
    value: H::Output,
}

/// A key proven absent, and the handle to insert it.
pub struct VacantEntry<'a, K: Key, H: HashFn> {
    proof: Proof<&'a [u8], K, H>,
    key: K,
    /// The leaf the lookup ended at and the first bit on which it differs from `key`; `None`
    /// for the empty map.
    splice: Option<(Leaf<K, H>, BitPos)>,
}

impl<B: AsRef<[u8]>, K: Key, H: HashFn> Proof<B, K, H> {
    /// Where `key` sits in the tree with root `root`, if this is `key`'s lookup path in that
    /// tree.
    ///
    /// The proof is refused with [`Error::OffPath`] if it is not the path a lookup for `key`
    /// takes, and with [`Error::RootMismatch`] if it does not fold to `root`. Whether `key` is
    /// present is then read off the terminal leaf: a proof claims nothing by itself.
    pub fn verify(&self, root: &H::Output, key: &K) -> Result<Entry<'_, K, H>, Error> {
        let proof = self.view();
        let Some(leaf) = proof.leaf() else {
            // The empty map holds nothing, and nothing else has this root.
            return if *root == empty_root::<H>() {
                Ok(Entry::Vacant(VacantEntry {
                    proof,
                    key: *key,
                    splice: None,
                }))
            } else {
                Err(Error::RootMismatch)
            };
        };

        // A lookup for `key` reads exactly the bits the path branches on; it ends at the
        // terminal leaf only if the two keys agree at all of them.
        if proof
            .steps()
            .any(|step| bit(key, step.crit_bit) != bit(&leaf.key, step.crit_bit))
        {
            return Err(Error::OffPath);
        }
        // The crit bit sits inside every branch digest, so a path that folds to the root
        // branches on exactly the bits it claims to.
        let start = leaf_digest::<K, H>(&leaf.key, &leaf.value);
        if fold(start, proof.steps(), key) != *root {
            return Err(Error::RootMismatch);
        }

        Ok(match crit_bit(key, &leaf.key) {
            None => Entry::Occupied(OccupiedEntry {
                proof,
                key: *key,
                value: leaf.value,
            }),
            Some(c) => Entry::Vacant(VacantEntry {
                proof,
                key: *key,
                splice: Some((leaf, c)),
            }),
        })
    }
}

/// `start` hashed up `steps` (leaf-to-root) along `key`'s path: the root this path implies.
pub(super) fn fold<K: Key, H: HashFn>(
    start: H::Output,
    steps: impl Iterator<Item = Step<H>>,
    key: &K,
) -> H::Output {
    steps.fold(start, |node, step| {
        parent_digest::<H>(step.crit_bit, bit(key, step.crit_bit), &node, &step.sibling)
    })
}

impl<K: Key, H: HashFn> Entry<'_, K, H> {
    /// The key this entry is for.
    pub fn key(&self) -> &K {
        match self {
            Self::Occupied(entry) => entry.key(),
            Self::Vacant(entry) => entry.key(),
        }
    }

    /// The root after storing `new` under the key: a replacement if the key is present, an
    /// insertion otherwise.
    pub fn set(self, new: &(impl Hashable<H> + ?Sized)) -> H::Output {
        match self {
            Self::Occupied(entry) => entry.replace(new),
            Self::Vacant(entry) => entry.insert(new),
        }
    }
}

impl<'a, K: Key, H: HashFn> OccupiedEntry<'a, K, H> {
    /// The entry over a proof already held against the root and found occupied, as a walk
    /// keeps one: the key and the digest are read off its leaf, which the proof has, since
    /// only the empty proof has none and the empty map holds no entry. Only the verifier may
    /// make this claim, hence `pub(super)`.
    pub(super) fn from_verified(proof: Proof<&'a [u8], K, H>) -> Self {
        // An occupied entry's proof ends at a leaf.
        let leaf = proof.leaf().unwrap();
        Self {
            proof,
            key: leaf.key,
            value: leaf.value,
        }
    }
}

impl<K: Key, H: HashFn> OccupiedEntry<'_, K, H> {
    /// The key this entry is for.
    pub fn key(&self) -> &K {
        &self.key
    }

    /// The digest of the stored value.
    pub fn digest(&self) -> &H::Output {
        &self.value
    }

    /// The stored value, given a claim of it: `claimed` itself if it hashes to the digest the
    /// proof commits to, [`Error::ValueMismatch`] otherwise.
    pub fn value<'v, V: Hashable<H> + ?Sized>(&self, claimed: &'v V) -> Result<&'v V, Error> {
        if claimed.digest() == self.value {
            Ok(claimed)
        } else {
            Err(Error::ValueMismatch)
        }
    }

    /// The root after replacing the value with `new`.
    ///
    /// Only the leaf changes, so the shape of the tree and every sibling on the path stay as
    /// they are; the new leaf folds up the same path.
    pub fn replace(self, new: &(impl Hashable<H> + ?Sized)) -> H::Output {
        let start = leaf_digest::<K, H>(&self.key, &new.digest());
        fold(start, self.proof.steps(), &self.key)
    }

    /// The root after removing the key: the root of the empty map if it was the last one.
    ///
    /// The branch directly above the leaf would be left with one child, so it collapses and
    /// its other child takes its place. That child keeps its digest, since a digest does not
    /// depend on depth, whether it is a leaf or a whole subtree; and it stays on the removed
    /// key's path above that point, so the fold continues along the same path.
    pub fn remove(self) -> H::Output {
        let mut steps = self.proof.steps();
        match steps.next() {
            None => empty_root::<H>(),
            Some(parent) => fold(parent.sibling, steps, &self.key),
        }
    }
}

impl<K: Key, H: HashFn> VacantEntry<'_, K, H> {
    /// The key this entry is for.
    pub fn key(&self) -> &K {
        &self.key
    }

    /// The root after inserting `new` under the key.
    ///
    /// Into the empty map, the tree becomes the new leaf. Otherwise a new branch splits the
    /// key from the terminal leaf at the first bit on which they differ, computed here and
    /// never taken from the proof. The two keys agree at every bit the path branches on, so
    /// that bit is tested by no existing branch: the new branch goes directly above the
    /// terminal leaf, or inside a run of skipped bits further up, above some existing branches.
    /// Whatever hangs below that point moves under the new branch with its digest unchanged.
    pub fn insert(self, new: &(impl Hashable<H> + ?Sized)) -> H::Output {
        let new_leaf = leaf_digest::<K, H>(&self.key, &new.digest());
        let Some((terminal, c)) = self.splice else {
            return new_leaf;
        };
        // Steps are leaf-to-root, so those below the new branch come first: the terminal
        // leaf's own path, up to the first branch at or above `c`.
        let mut steps = self.proof.steps().peekable();
        let subtree = fold(
            leaf_digest::<K, H>(&terminal.key, &terminal.value),
            core::iter::from_fn(|| steps.next_if(|step| step.crit_bit > c)),
            &terminal.key,
        );
        let branch = parent_digest::<H>(c, bit(&self.key, c), &new_leaf, &subtree);
        // Above the branch both keys take the same turns.
        fold(branch, steps, &self.key)
    }
}

// By hand for the reason given above the impls in `common/proof.rs` (a derive would bound `K`
// and `H` rather than the fields), and because these show the key and the digest only: the
// proof and the splice are left out on purpose.

impl<K: Key, H: HashFn> fmt::Debug for Entry<'_, K, H> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Occupied(entry) => f.debug_tuple("Occupied").field(entry).finish(),
            Self::Vacant(entry) => f.debug_tuple("Vacant").field(entry).finish(),
        }
    }
}

impl<K: Key, H: HashFn> fmt::Debug for OccupiedEntry<'_, K, H> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("OccupiedEntry")
            .field("key", &self.key.as_bytes().as_ref())
            .field("value", &self.value.as_ref())
            .finish_non_exhaustive()
    }
}

impl<K: Key, H: HashFn> fmt::Debug for VacantEntry<'_, K, H> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("VacantEntry")
            .field("key", &self.key.as_bytes().as_ref())
            .finish_non_exhaustive()
    }
}

#[cfg(test)]
mod tests {
    //! The four-leaf example of the design document, over one-byte keys:
    //!
    //! ```text
    //!   A = 0000 0000   B = 0000 1111   C = 0100 0000   D = 1000 0000
    //!   root = branch(0, branch(1, branch(4, La, Lb), Lc), Ld)
    //! ```
    //!
    //! Every constant below was derived independently with Python's hashlib from the
    //! encodings in the crate documentation, and every expected root after a change is the
    //! canonical rebuild of the changed map, not the verifier's own output.

    use super::*;
    use crate::trie::common::Sha256;

    type Key1 = [u8; 1];
    type P<'a> = Proof<&'a [u8], Key1, Sha256>;

    // The four-leaf map over one-byte keys. A branch is labelled with its crit bit and its
    // left child holds the keys whose bit is 0. The arrows mark where the three absent keys
    // below would splice their branch in.
    //
    //                 (bit 0)
    //                /       \
    //           (bit 1)       D 1000_0000   <- F: new branch at bit 1, between D and the root
    //          /       \
    //     (bit 4)       C 0100_0000         <- E: new branch at bit 2, between bits 1 and 4
    //    /       \
    //   A         B                         <- G: new branch at bit 7, directly above A
    //   0000_0000 0000_1111
    const A: Key1 = [0b0000_0000];
    const B: Key1 = [0b0000_1111];
    const C: Key1 = [0b0100_0000];
    const D: Key1 = [0b1000_0000];
    const E: Key1 = [0b0010_0000]; // absent: parts from A at bit 2, inside the run between the branches at 1 and 4
    const F: Key1 = [0b1111_1111]; // absent: parts from D at bit 1, above D's leaf and below the root
    const G: Key1 = [0b0000_0001]; // absent: parts from A at bit 7, directly above A's leaf

    const ROOT: &str = "801c76a17f759146fdc24b4bbc66c1f6fbbe63cf0c5a15121c274e9e7146c54c";
    const EMPTY: &str = "dbc1b4c900ffe48d575b5da5c638040125f65db0fe3e24494b76ea986457d986";

    /// A's lookup path, which is also E's and G's.
    const PROOF_A: &str = "00c7985a722bc82b44027b3692ec1b79a2e86267e2577b9cc0e09a9dee4515e0f6\
        000466c808c49e8d051a943939af6530d34afbb3ddb6054d25823313f41a22c4cfad\
        0001567cd4f15980338f90a766a300b301b7c4ad401dad3b2e327bec281bb76fb983\
        0000d3fd399d63bafbde1938abcd6a556f7fd546ceb76c352754472f4e0ecf564aa9";
    const PROOF_B: &str = "0fb3645e94d1f773c429c707715dc51a3178f8b12ef2fcd149a52b5a8f69404435\
        0004676388dd193dc4fde9a116f42237ef61bd8d4d6f54fca0c80ed8d83ee7f2d871\
        0001567cd4f15980338f90a766a300b301b7c4ad401dad3b2e327bec281bb76fb983\
        0000d3fd399d63bafbde1938abcd6a556f7fd546ceb76c352754472f4e0ecf564aa9";
    /// D's lookup path, which is also F's.
    const PROOF_D: &str = "80579dcf4b2884b4d6212e2ab4db770ebd5884415869e907457694ddd221973fdf\
        00008451117f60bd9938110b0b0539e0e7bb42367564f17b55bdfd27cbcbf9aa5568";

    fn digest(s: &str) -> [u8; 32] {
        hex::decode(s).unwrap().try_into().unwrap()
    }

    fn proof(s: &str) -> Vec<u8> {
        hex::decode(s).unwrap()
    }

    fn occupied<'a>(entry: Entry<'a, Key1, Sha256>) -> OccupiedEntry<'a, Key1, Sha256> {
        match entry {
            Entry::Occupied(entry) => entry,
            Entry::Vacant(_) => panic!("expected an occupied entry"),
        }
    }

    fn vacant<'a>(entry: Entry<'a, Key1, Sha256>) -> VacantEntry<'a, Key1, Sha256> {
        match entry {
            Entry::Vacant(entry) => entry,
            Entry::Occupied(_) => panic!("expected a vacant entry"),
        }
    }

    #[test]
    fn present_and_absent_are_read_off_the_same_proof() {
        let bytes = proof(PROOF_A);
        let proof_a = P::parse(&bytes).unwrap();
        let root = digest(ROOT);

        let entry = occupied(proof_a.verify(&root, &A).unwrap());
        assert_eq!(entry.key(), &A);
        assert_eq!(entry.digest(), &Hashable::<Sha256>::digest(b"a"));
        assert_eq!(entry.value(b"a").unwrap(), b"a");
        assert_eq!(entry.value(b"x").unwrap_err(), Error::ValueMismatch);

        for absent in [E, G] {
            let entry = vacant(proof_a.verify(&root, &absent).unwrap());
            assert_eq!(entry.key(), &absent);
        }

        let bytes = proof(PROOF_B);
        let proof_b = P::parse(&bytes).unwrap();
        let entry = occupied(proof_b.verify(&root, &B).unwrap());
        assert_eq!(entry.value(b"b").unwrap(), b"b");
    }

    #[test]
    fn a_path_is_only_good_for_the_keys_that_take_it() {
        let root = digest(ROOT);
        // B's path branches on bit 4, where A and B differ.
        let bytes = proof(PROOF_B);
        assert_eq!(
            P::parse(&bytes).unwrap().verify(&root, &A).unwrap_err(),
            Error::OffPath
        );
        // D's path branches on bit 0 only, where C differs from D.
        let bytes = proof(PROOF_D);
        assert_eq!(
            P::parse(&bytes).unwrap().verify(&root, &C).unwrap_err(),
            Error::OffPath
        );
    }

    #[test]
    fn the_root_binds_everything() {
        let bytes = proof(PROOF_A);
        let proof = P::parse(&bytes).unwrap();
        let mut other = digest(ROOT);
        other[0] ^= 1;
        assert_eq!(proof.verify(&other, &A).unwrap_err(), Error::RootMismatch);
        assert_eq!(
            proof.verify(&digest(EMPTY), &A).unwrap_err(),
            Error::RootMismatch
        );
        // A relabelled crit bit changes the branch digest.
        let mut relabelled = bytes.clone();
        relabelled[33 + 1] = 5;
        assert_eq!(
            P::parse(&relabelled)
                .unwrap()
                .verify(&digest(ROOT), &A)
                .unwrap_err(),
            Error::RootMismatch
        );
        // So does a claimed value: the terminal digest is inside the leaf.
        let mut other_value = bytes.clone();
        other_value[1] ^= 1;
        assert_eq!(
            P::parse(&other_value)
                .unwrap()
                .verify(&digest(ROOT), &A)
                .unwrap_err(),
            Error::RootMismatch
        );
    }

    #[test]
    fn the_empty_map() {
        let proof = P::parse(&[]).unwrap();
        let entry = vacant(proof.verify(&digest(EMPTY), &A).unwrap());
        assert_eq!(entry.key(), &A);
        assert_eq!(
            proof.verify(&digest(ROOT), &A).unwrap_err(),
            Error::RootMismatch
        );
        // The first leaf is the whole tree.
        let root = vacant(proof.verify(&digest(EMPTY), &A).unwrap()).insert(b"a");
        assert_eq!(
            hex::encode(root),
            "676388dd193dc4fde9a116f42237ef61bd8d4d6f54fca0c80ed8d83ee7f2d871"
        );
        assert_eq!(
            root,
            leaf_digest::<Key1, Sha256>(&A, &Hashable::<Sha256>::digest(b"a"))
        );
    }

    #[test]
    fn replace_keeps_the_path() {
        let bytes = proof(PROOF_A);
        let proof = P::parse(&bytes).unwrap();
        let entry = occupied(proof.verify(&digest(ROOT), &A).unwrap());
        assert_eq!(
            hex::encode(entry.replace(b"a2")),
            "3baadcdebe3ea5616c2a8eccb82e5c7bdd44568fd898a8d45939bc1174556d49"
        );
    }

    #[test]
    fn remove_promotes_the_sibling_unchanged() {
        // A's sibling is the leaf B.
        let bytes = proof(PROOF_A);
        let proof_a = P::parse(&bytes).unwrap();
        let entry = occupied(proof_a.verify(&digest(ROOT), &A).unwrap());
        assert_eq!(
            hex::encode(entry.remove()),
            "0ee5df752cd27d4c46f96139335753da2b93287f0125a9a05d36f93bb0f6462a"
        );
        // D's sibling is the branch over A, B and C, which becomes the root as it is: the
        // digest the proof carries for it.
        let bytes = proof(PROOF_D);
        let proof = P::parse(&bytes).unwrap();
        let sibling = proof.steps().next().unwrap().sibling;
        let entry = occupied(proof.verify(&digest(ROOT), &D).unwrap());
        let root = entry.remove();
        assert_eq!(root, sibling);
        assert_eq!(
            hex::encode(root),
            "8451117f60bd9938110b0b0539e0e7bb42367564f17b55bdfd27cbcbf9aa5568"
        );
    }

    #[test]
    fn remove_the_last_leaf() {
        let mut bytes = A.to_vec();
        bytes.extend_from_slice(&Hashable::<Sha256>::digest(b"a"));
        let proof = P::parse(&bytes).unwrap();
        let root = leaf_digest::<Key1, Sha256>(&A, &Hashable::<Sha256>::digest(b"a"));
        let entry = occupied(proof.verify(&root, &A).unwrap());
        assert_eq!(entry.remove(), digest(EMPTY));
    }

    #[test]
    fn insert_splices_at_the_first_differing_bit() {
        let root = digest(ROOT);
        for (key, value, proof_hex, expected) in [
            // inside the compressed run between the branches at bits 1 and 4
            (
                E,
                &b"e"[..],
                PROOF_A,
                "1bf82b3f829c5f1f403ea66a13b96d7e648072fafd9f621359db3a45e13fa6b2",
            ),
            // above an existing branch's leaf, below the root
            (
                F,
                b"f",
                PROOF_D,
                "5df6915caa33b931da5ed17dba221c9f78a5ef935f07cb4be34315cf3aa83431",
            ),
            // directly above the terminal leaf
            (
                G,
                b"g",
                PROOF_A,
                "11d96e004a6eb7fede1894989bb54269ae0e9ae24beb9a1ec0420febfbcd46e0",
            ),
        ] {
            let bytes = proof(proof_hex);
            let proof = P::parse(&bytes).unwrap();
            let entry = vacant(proof.verify(&root, &key).unwrap());
            assert_eq!(hex::encode(entry.insert(value)), expected, "key {key:?}");
        }
    }

    #[test]
    fn set_dispatches_on_presence() {
        let bytes = proof(PROOF_A);
        let proof = P::parse(&bytes).unwrap();
        let root = digest(ROOT);
        assert_eq!(
            hex::encode(proof.verify(&root, &A).unwrap().set(b"a2")),
            "3baadcdebe3ea5616c2a8eccb82e5c7bdd44568fd898a8d45939bc1174556d49"
        );
        assert_eq!(
            hex::encode(proof.verify(&root, &E).unwrap().set(b"e")),
            "1bf82b3f829c5f1f403ea66a13b96d7e648072fafd9f621359db3a45e13fa6b2"
        );
    }
}
