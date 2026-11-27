//! One lookup, held against the root: [`Root::entry`] answers where a key sits in the tree
//! with that root, as an [`Entry`], occupied by a value or vacant, and a change made through
//! the entry advances the root to the one the change produces, derived from the root and the
//! proof alone. The entry is the only way to change a root, so nothing is ever derived from an
//! unverified proof. The three changes are reachable only from the variant where they make
//! sense: a vacant entry can be inserted into, an occupied one can be replaced or removed.
//! [`Root::get`] is the same lookup for reading.

#[cfg(feature = "debug")]
use core::fmt;

use super::root::Root;
use crate::trie::common::{
    BitPos, Error, HashFn, Hashable, Key, Leaf, Proof, Side, Step, bit, crit_bit, empty_root,
    leaf_digest, parent_digest,
};

/// Where a key sits in the tree with a given root, as proven by a proof, and the handle for
/// changing it.
///
/// Modelled on `std::collections::hash_map::Entry`: the lookup result and the handle for the
/// change in one. Obtained from [`Root::entry`]; it borrows the root until it is used or
/// dropped, and dropping it changes nothing.
pub enum Entry<'a, K: Key, H: HashFn> {
    /// The key is present.
    Occupied(OccupiedEntry<&'a mut Root<H>, &'a [u8], K, H>),
    /// The key is absent.
    Vacant(VacantEntry<'a, K, H>),
}

/// A key proven present: its value digest and, where the root is held exclusively, the handle
/// to replace or remove it.
///
/// `R` is how the entry holds the root. Over `&Root<H>`, from [`Root::get`] or a step of a
/// [`Walk`](super::Walk), the entry is for reading. Over `&mut Root<H>`, from [`Root::entry`]
/// or [`Walk::into_entry`](super::Walk::into_entry), it can also [`replace`](Self::replace)
/// and [`remove`](Self::remove).
///
/// `B` is the storage of the proof the entry was verified with, which a change folds along.
/// It is a slice borrowed from the caller's proof or from the walk's, with one exception:
/// [`Walk::into_entry`](super::Walk::into_entry) consumes the walk, so a slice would borrow
/// from a walk that is gone, and the entry takes over the walk's own storage instead.
pub struct OccupiedEntry<R, B, K: Key, H: HashFn> {
    root: R,
    proof: Proof<B, K, H>,
    key: K,
    value_digest: H::Output,
}

/// A key proven absent, and the handle to insert it.
pub struct VacantEntry<'a, K: Key, H: HashFn> {
    root: &'a mut Root<H>,
    proof: Proof<&'a [u8], K, H>,
    key: K,
    /// The leaf the lookup ended at and the first bit on which it differs from `key`; `None`
    /// for the empty map.
    splice: Option<(Leaf<K, H>, BitPos<K>)>,
}

/// Where a key's lookup ends, once its proof is held against the root.
enum Lookup<K: Key, H: HashFn> {
    /// At the key's own leaf, which commits to this value digest.
    Present(H::Output),
    /// At another leaf, with the first bit on which the key differs from it; `None` for the
    /// empty map.
    Absent(Option<(Leaf<K, H>, BitPos<K>)>),
}

/// Holds `proof` against `root` as `key`'s lookup path; the one check behind [`Root::get`]
/// and [`Root::entry`].
fn lookup<K: Key, H: HashFn>(
    root: &Root<H>,
    key: &K,
    proof: &Proof<&[u8], K, H>,
) -> Result<Lookup<K, H>, Error> {
    let Some(leaf) = proof.leaf() else {
        // The empty map holds nothing, and nothing else has this root.
        return if root.0 == empty_root::<H>() {
            Ok(Lookup::Absent(None))
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
    let start = leaf_digest::<K, H>(&leaf.key, &leaf.value_digest);
    if fold(start, proof.steps(), key) != root.0 {
        return Err(Error::RootMismatch);
    }

    Ok(match crit_bit(key, &leaf.key) {
        None => Lookup::Present(leaf.value_digest),
        Some(c) => Lookup::Absent(Some((leaf, c))),
    })
}

impl<H: HashFn> Root<H> {
    /// `key`'s entry in the tree with this root, for reading, or `None` if `key` is absent,
    /// provided `proof` is `key`'s lookup path in that tree.
    ///
    /// The proof is refused with [`Error::OffPath`] if it is not the path a lookup for `key`
    /// takes, and with [`Error::RootMismatch`] if it does not fold to the root. Whether `key` is
    /// present is then read off the terminal leaf: a proof claims nothing by itself, and
    /// `None` is as proven as an entry.
    pub fn get<'a, K: Key>(
        &'a self,
        key: &K,
        proof: &'a Proof<impl AsRef<[u8]>, K, H>,
    ) -> Result<Option<OccupiedEntry<&'a Self, &'a [u8], K, H>>, Error> {
        let proof = proof.view();
        Ok(match lookup(self, key, &proof)? {
            Lookup::Present(value_digest) => Some(OccupiedEntry {
                root: self,
                proof,
                key: *key,
                value_digest,
            }),
            Lookup::Absent(_) => None,
        })
    }

    /// Where `key` sits in the tree with this root, as the handle for changing it. The proof
    /// is held against the root, and refused, as [`get`](Self::get) does it.
    pub fn entry<'a, K: Key>(
        &'a mut self,
        key: &K,
        proof: &'a Proof<impl AsRef<[u8]>, K, H>,
    ) -> Result<Entry<'a, K, H>, Error> {
        let proof = proof.view();
        Ok(match lookup(self, key, &proof)? {
            Lookup::Present(value_digest) => Entry::Occupied(OccupiedEntry {
                root: self,
                proof,
                key: *key,
                value_digest,
            }),
            Lookup::Absent(splice) => Entry::Vacant(VacantEntry {
                root: self,
                proof,
                key: *key,
                splice,
            }),
        })
    }
}

/// `start` hashed up `steps` (leaf-to-root) along `key`'s path: the root this path implies.
pub(super) fn fold<K: Key, H: HashFn>(
    start: H::Output,
    steps: impl Iterator<Item = Step<K, H>>,
    key: &K,
) -> H::Output {
    steps.fold(start, |node, step| {
        let side = Side::of(key, step.crit_bit);
        parent_digest::<K, H>(step.crit_bit, side, &node, &step.sibling)
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

    /// Stores `new` under the key, advancing the root: a replacement if the key is present,
    /// an insertion otherwise.
    pub fn set(self, new: &(impl Hashable<H> + ?Sized)) {
        match self {
            Self::Occupied(entry) => entry.replace(new),
            Self::Vacant(entry) => entry.insert(new),
        }
    }
}

impl<R, B: AsRef<[u8]>, K: Key, H: HashFn> OccupiedEntry<R, B, K, H> {
    /// The entry over a proof already held against `root` and found occupied, as a walk
    /// keeps one: the key and the digest are read off its leaf, which the proof has, since
    /// only the empty proof has none and the empty map holds no entry. Only the verifier may
    /// make this claim, hence `pub(super)`.
    pub(super) fn from_verified(root: R, proof: Proof<B, K, H>) -> Self {
        // An occupied entry's proof ends at a leaf.
        let leaf = proof.leaf().unwrap();
        Self {
            root,
            proof,
            key: leaf.key,
            value_digest: leaf.value_digest,
        }
    }

    /// The key this entry is for.
    pub fn key(&self) -> &K {
        &self.key
    }

    /// The digest of the stored value.
    pub fn digest(&self) -> &H::Output {
        &self.value_digest
    }

    /// The stored value, given a claim of it: `claimed` itself if it hashes to the digest the
    /// proof commits to, [`Error::ValueMismatch`] otherwise.
    pub fn value<'v, V: Hashable<H> + ?Sized>(&self, claimed: &'v V) -> Result<&'v V, Error> {
        if claimed.digest() == self.value_digest {
            Ok(claimed)
        } else {
            Err(Error::ValueMismatch)
        }
    }
}

impl<B: AsRef<[u8]>, K: Key, H: HashFn> OccupiedEntry<&mut Root<H>, B, K, H> {
    /// Replaces the value with `new`, advancing the root.
    ///
    /// Only the leaf changes, so the shape of the tree and every sibling on the path stay as
    /// they are; the new leaf folds up the same path.
    pub fn replace(self, new: &(impl Hashable<H> + ?Sized)) {
        let start = leaf_digest::<K, H>(&self.key, &new.digest());
        self.root.0 = fold(start, self.proof.steps(), &self.key);
    }

    /// Removes the key, advancing the root: to the root of the empty map if it was the last
    /// one.
    ///
    /// The branch directly above the leaf would be left with one child, so it collapses and
    /// its other child takes its place. That child keeps its digest, since a digest does not
    /// depend on depth, whether it is a leaf or a whole subtree; and it stays on the removed
    /// key's path above that point, so the fold continues along the same path.
    pub fn remove(self) {
        let mut steps = self.proof.steps();
        self.root.0 = match steps.next() {
            None => empty_root::<H>(),
            Some(parent) => fold(parent.sibling, steps, &self.key),
        };
    }
}

impl<K: Key, H: HashFn> VacantEntry<'_, K, H> {
    /// The key this entry is for.
    pub fn key(&self) -> &K {
        &self.key
    }

    /// Inserts `new` under the key, advancing the root.
    ///
    /// Into the empty map, the tree becomes the new leaf. Otherwise a new branch splits the
    /// key from the terminal leaf at the first bit on which they differ, computed here and
    /// never taken from the proof. The two keys agree at every bit the path branches on, so
    /// that bit is tested by no existing branch: the new branch goes directly above the
    /// terminal leaf, or inside a run of skipped bits further up, above some existing branches.
    /// Whatever hangs below that point moves under the new branch with its digest unchanged.
    pub fn insert(self, new: &(impl Hashable<H> + ?Sized)) {
        let new_leaf = leaf_digest::<K, H>(&self.key, &new.digest());
        let Some((terminal, c)) = self.splice else {
            self.root.0 = new_leaf;
            return;
        };
        // The steps below the new branch come first, since steps are leaf-to-root: they are
        // the ones whose crit bit is greater than `c`. None has crit bit `c` itself: the lookup
        // found the two keys agreeing wherever the path branches, and at `c` they differ.
        let mut steps = self.proof.steps().peekable();
        let subtree = fold(
            leaf_digest::<K, H>(&terminal.key, &terminal.value_digest),
            core::iter::from_fn(|| steps.next_if(|step| step.crit_bit > c)),
            &terminal.key,
        );
        let branch = parent_digest::<K, H>(c, Side::of(&self.key, c), &new_leaf, &subtree);
        // Above the branch both keys take the same turns.
        self.root.0 = fold(branch, steps, &self.key);
    }
}

// By hand for the reason given above the impls in `common/proof.rs` (a derive would bound `K`
// and `H` rather than the fields), and because these show the key and the digest only: the
// root, the proof and the splice are left out on purpose.

#[cfg(feature = "debug")]
impl<K: Key, H: HashFn> fmt::Debug for Entry<'_, K, H> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Occupied(entry) => f.debug_tuple("Occupied").field(entry).finish(),
            Self::Vacant(entry) => f.debug_tuple("Vacant").field(entry).finish(),
        }
    }
}

#[cfg(feature = "debug")]
impl<R, B, K: Key, H: HashFn> fmt::Debug for OccupiedEntry<R, B, K, H> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("OccupiedEntry")
            .field("key", &self.key.as_bytes().as_ref())
            .field("value_digest", &self.value_digest.as_ref())
            .finish_non_exhaustive()
    }
}

#[cfg(feature = "debug")]
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

    const ROOT: &str = "214c01e9e4e7bd3c342de2e12c3251610bd8ef5c63a199c04029234d257b7bbb";
    const EMPTY: &str = "dbc1b4c900ffe48d575b5da5c638040125f65db0fe3e24494b76ea986457d986";

    /// A's lookup path, which is also E's and G's.
    const PROOF_A: &str = "00c7985a722bc82b44027b3692ec1b79a2e86267e2577b9cc0e09a9dee4515e0f6\
        0466c808c49e8d051a943939af6530d34afbb3ddb6054d25823313f41a22c4cfad\
        01567cd4f15980338f90a766a300b301b7c4ad401dad3b2e327bec281bb76fb983\
        00d3fd399d63bafbde1938abcd6a556f7fd546ceb76c352754472f4e0ecf564aa9";
    const PROOF_B: &str = "0fb3645e94d1f773c429c707715dc51a3178f8b12ef2fcd149a52b5a8f69404435\
        04676388dd193dc4fde9a116f42237ef61bd8d4d6f54fca0c80ed8d83ee7f2d871\
        01567cd4f15980338f90a766a300b301b7c4ad401dad3b2e327bec281bb76fb983\
        00d3fd399d63bafbde1938abcd6a556f7fd546ceb76c352754472f4e0ecf564aa9";
    /// D's lookup path, which is also F's.
    const PROOF_D: &str = "80579dcf4b2884b4d6212e2ab4db770ebd5884415869e907457694ddd221973fdf\
        00325efa106c9af145cc41bf14c06be7a3caaf40ca92b7a0a44bd867b29267fe1d";

    fn digest(s: &str) -> [u8; 32] {
        hex::decode(s).unwrap().try_into().unwrap()
    }

    fn trusted(s: &str) -> Root<Sha256> {
        Root::trusted(digest(s))
    }

    fn proof(s: &str) -> Vec<u8> {
        hex::decode(s).unwrap()
    }

    fn occupied<'a>(
        entry: Entry<'a, Key1, Sha256>,
    ) -> OccupiedEntry<&'a mut Root<Sha256>, &'a [u8], Key1, Sha256> {
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
        let mut root = trusted(ROOT);

        let entry = root.get(&A, &proof_a).unwrap().unwrap();
        assert_eq!(entry.key(), &A);
        assert_eq!(entry.digest(), &Hashable::<Sha256>::digest(b"a"));
        assert_eq!(entry.value(b"a").unwrap(), b"a");
        assert_eq!(entry.value(b"x").unwrap_err(), Error::ValueMismatch);

        for absent in [E, G] {
            assert!(root.get(&absent, &proof_a).unwrap().is_none());
            assert_eq!(
                vacant(root.entry(&absent, &proof_a).unwrap()).key(),
                &absent
            );
        }

        let bytes = proof(PROOF_B);
        let proof_b = P::parse(&bytes).unwrap();
        let entry = occupied(root.entry(&B, &proof_b).unwrap());
        assert_eq!(entry.value(b"b").unwrap(), b"b");
    }

    #[test]
    fn a_path_is_only_good_for_the_keys_that_take_it() {
        let root = trusted(ROOT);
        // B's path branches on bit 4, where A and B differ.
        let bytes = proof(PROOF_B);
        assert_eq!(
            root.get(&A, &P::parse(&bytes).unwrap()).unwrap_err(),
            Error::OffPath
        );
        // D's path branches on bit 0 only, where C differs from D.
        let bytes = proof(PROOF_D);
        assert_eq!(
            root.get(&C, &P::parse(&bytes).unwrap()).unwrap_err(),
            Error::OffPath
        );
    }

    #[test]
    fn the_root_binds_everything() {
        let bytes = proof(PROOF_A);
        let proof = P::parse(&bytes).unwrap();
        let mut other = digest(ROOT);
        other[0] ^= 1;
        assert_eq!(
            Root::trusted(other).get(&A, &proof).unwrap_err(),
            Error::RootMismatch
        );
        assert_eq!(
            trusted(EMPTY).get(&A, &proof).unwrap_err(),
            Error::RootMismatch
        );
        // A relabelled crit bit changes the branch digest.
        let mut relabelled = bytes.clone();
        relabelled[33 + 1] = 5;
        assert_eq!(
            trusted(ROOT)
                .get(&A, &P::parse(&relabelled).unwrap())
                .unwrap_err(),
            Error::RootMismatch
        );
        // So does a claimed value: the terminal digest is inside the leaf.
        let mut other_value = bytes.clone();
        other_value[1] ^= 1;
        assert_eq!(
            trusted(ROOT)
                .get(&A, &P::parse(&other_value).unwrap())
                .unwrap_err(),
            Error::RootMismatch
        );
    }

    #[test]
    fn the_empty_map() {
        let proof = P::parse(&[]).unwrap();
        let mut root = trusted(EMPTY);
        assert!(root.get(&A, &proof).unwrap().is_none());
        assert_eq!(vacant(root.entry(&A, &proof).unwrap()).key(), &A);
        assert_eq!(
            trusted(ROOT).get(&A, &proof).unwrap_err(),
            Error::RootMismatch
        );
        // The first leaf is the whole tree.
        vacant(root.entry(&A, &proof).unwrap()).insert(b"a");
        assert_eq!(
            hex::encode(root.digest()),
            "676388dd193dc4fde9a116f42237ef61bd8d4d6f54fca0c80ed8d83ee7f2d871"
        );
        assert_eq!(
            *root.digest(),
            leaf_digest::<Key1, Sha256>(&A, &Hashable::<Sha256>::digest(b"a"))
        );
    }

    #[test]
    fn replace_keeps_the_path() {
        let bytes = proof(PROOF_A);
        let proof = P::parse(&bytes).unwrap();
        let mut root = trusted(ROOT);
        occupied(root.entry(&A, &proof).unwrap()).replace(b"a2");
        assert_eq!(
            hex::encode(root.digest()),
            "4039397b1a045ecba779552c436351f936a3706fc47e3408050a9d537e530c33"
        );
    }

    #[test]
    fn remove_promotes_the_sibling_unchanged() {
        // A's sibling is the leaf B.
        let bytes = proof(PROOF_A);
        let proof_a = P::parse(&bytes).unwrap();
        let mut root = trusted(ROOT);
        occupied(root.entry(&A, &proof_a).unwrap()).remove();
        assert_eq!(
            hex::encode(root.digest()),
            "7dbabafa74f085a6a3b1a4f1379bb5bec6fa710f83b52fdb573ab249e1e0cb7c"
        );
        // D's sibling is the branch over A, B and C, which becomes the root as it is: the
        // digest the proof carries for it.
        let bytes = proof(PROOF_D);
        let proof = P::parse(&bytes).unwrap();
        let sibling = proof.steps().next().unwrap().sibling;
        let mut root = trusted(ROOT);
        occupied(root.entry(&D, &proof).unwrap()).remove();
        assert_eq!(*root.digest(), sibling);
        assert_eq!(
            hex::encode(root.digest()),
            "325efa106c9af145cc41bf14c06be7a3caaf40ca92b7a0a44bd867b29267fe1d"
        );
    }

    #[test]
    fn remove_the_last_leaf() {
        let mut bytes = A.to_vec();
        bytes.extend_from_slice(&Hashable::<Sha256>::digest(b"a"));
        let proof = P::parse(&bytes).unwrap();
        let mut root = Root::trusted(leaf_digest::<Key1, Sha256>(
            &A,
            &Hashable::<Sha256>::digest(b"a"),
        ));
        occupied(root.entry(&A, &proof).unwrap()).remove();
        assert_eq!(root, Root::empty());
    }

    #[test]
    fn insert_splices_at_the_first_differing_bit() {
        for (key, value, proof_hex, expected) in [
            // inside the compressed run between the branches at bits 1 and 4
            (
                E,
                &b"e"[..],
                PROOF_A,
                "1332219b91225b1d87a0256eaa0281869c08625c553ee87f08fe3b836040dc42",
            ),
            // above an existing branch's leaf, below the root
            (
                F,
                b"f",
                PROOF_D,
                "b1bd9a9977e6f7d81dc3090870f6fb1dcfe2ba82e45e821e84e09c4fdb4d6e78",
            ),
            // directly above the terminal leaf
            (
                G,
                b"g",
                PROOF_A,
                "e03f8a7310bada52e8565a713b1efb36256b174f25852568069704a00ec1ec04",
            ),
        ] {
            let bytes = proof(proof_hex);
            let proof = P::parse(&bytes).unwrap();
            let mut root = trusted(ROOT);
            vacant(root.entry(&key, &proof).unwrap()).insert(value);
            assert_eq!(hex::encode(root.digest()), expected, "key {key:?}");
        }
    }

    #[test]
    fn set_dispatches_on_presence() {
        let bytes = proof(PROOF_A);
        let proof = P::parse(&bytes).unwrap();
        let mut root = trusted(ROOT);
        root.entry(&A, &proof).unwrap().set(b"a2");
        assert_eq!(
            hex::encode(root.digest()),
            "4039397b1a045ecba779552c436351f936a3706fc47e3408050a9d537e530c33"
        );
        let mut root = trusted(ROOT);
        root.entry(&E, &proof).unwrap().set(b"e");
        assert_eq!(
            hex::encode(root.digest()),
            "1332219b91225b1d87a0256eaa0281869c08625c553ee87f08fe3b836040dc42"
        );
    }

    #[test]
    fn a_change_leaves_the_proofs_of_the_old_root_behind() {
        // Both proofs are of the tree with `ROOT`.
        let (bytes_a, bytes_b) = (proof(PROOF_A), proof(PROOF_B));
        let proof_a = P::parse(&bytes_a).unwrap();
        let proof_b = P::parse(&bytes_b).unwrap();
        let mut root = trusted(ROOT);
        // An entry that is looked at and dropped changes nothing.
        assert_eq!(root.entry(&A, &proof_a).unwrap().key(), &A);
        assert_eq!(root, trusted(ROOT));

        root.entry(&A, &proof_a).unwrap().set(b"a2");
        let changed = root.clone();
        assert_ne!(changed, trusted(ROOT));
        // The second of two changes proven against one root is refused, not applied on its
        // own; and so is every other proof of the tree as it was.
        assert_eq!(root.entry(&B, &proof_b).unwrap_err(), Error::RootMismatch);
        assert_eq!(root.get(&A, &proof_a).unwrap_err(), Error::RootMismatch);
        assert_eq!(root, changed, "a refused proof moved the root");
    }
}
