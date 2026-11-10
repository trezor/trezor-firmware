//! The walk: the entries of the tree with one root, in key order, one proof per entry, so that
//! the device can enumerate what the host holds and the host can neither hide, repeat nor
//! reorder an entry.
//!
//! Keys are byte strings and the tree routes on their bits, so the entries in key order are
//! the leaves in in-order, and two facts about a canonical tree carry the walk: every key
//! under a branch agrees with the others on every bit before the branch's crit bit, and the
//! smallest key under a branch is the leaf whose path below it turns left at every branch.
//! The entry after the current one therefore parts from it at `C`, the lowest branch where the
//! current key turns left, has bit 1 there, and turns left at every branch below `C`; the first
//! entry turns left at every branch of the tree; and the last entry turns left nowhere, which
//! is how the walk knows it is done. The host sends no end marker and has no way to.
//!
//! A [`Walk`] holds the current entry's full proof. For the next entry the host may send its
//! full proof, or only the part of its path below `C`, which the walk splices onto the steps
//! it already holds above `C`: both proofs share them, and the step at `C` changes its sibling
//! from the right child, where the next entry lives, to the left child, which the walk is
//! leaving and can fold itself. Either way the result is the entry's full proof, held against
//! the root by
//! [`Proof::verify`] like any other, and only then checked for the successor rule. The walk
//! allocates nothing: the caller hands in the storage for each proof, sized by
//! [`Walk::next_len`], and may keep the proof between steps and come back with [`Walk::at`].

#[cfg(feature = "debug")]
use core::fmt;
use core::iter;

use super::entry::{OccupiedEntry, fold};
use crate::trie::common::{
    BitPos, Error, HashFn, Key, Leaf, Proof, Side, Step, crit_bit, empty_root, leaf_digest,
    write_into,
};

/// A position in the walk over the entries of the tree with one root, in key order: before
/// the first entry, or at the entry whose proof it holds.
///
/// `B` is the storage of that proof: `Vec<u8>` on a host, a buffer the caller allocated on a
/// device. The walk reads the proof through `AsRef<[u8]>` and writes a new one only into a
/// buffer the caller provides for [`next_into`](Self::next_into).
pub struct Walk<B, K: Key, H: HashFn> {
    root: H::Output,
    /// The current entry's full proof; `None` before the first entry.
    current: Option<Proof<B, K, H>>,
}

/// Where the next entry parts from the current one: the current entry's proof and leaf, the
/// crit bit `C` of its lowest left turn, and how many of its steps lie below `C` and above it.
struct Turn<'a, B, K: Key, H: HashFn> {
    current: &'a Proof<B, K, H>,
    leaf: Leaf<K, H>,
    crit_bit: BitPos<K>,
    below: usize,
    above: usize,
}

/// Whether every step of `proof` lies below the branch at `c`: the shape of a truncated proof
/// for the entry after one that turns left at `c`. A full proof of that entry has a step at
/// `c` itself.
fn lies_below<K: Key, H: HashFn>(proof: &Proof<impl AsRef<[u8]>, K, H>, c: BitPos<K>) -> bool {
    // Steps are leaf-to-root, so the last one has the smallest crit bit.
    proof
        .steps()
        .next_back()
        .is_none_or(|step| step.crit_bit > c)
}

impl<B: AsRef<[u8]>, K: Key, H: HashFn> Walk<B, K, H> {
    /// Before the first entry of the tree with `root`; done at once if `root` is the root of
    /// the empty map.
    pub fn new(root: H::Output) -> Self {
        Self {
            root,
            current: None,
        }
    }

    /// At the entry `proof` proves, in the tree with `root`. The proof is held against the
    /// root as [`Proof::verify`] holds it: one that does not fold to it is
    /// [`Error::RootMismatch`], and the proof of the empty map, which names no entry, gives
    /// the walk over the empty tree, done at once as [`new`](Self::new) gives it for that
    /// root. Which entry the walk is at is the caller's position, as the root is the caller's
    /// trust: a proof kept from an earlier step resumes from there.
    pub fn at(root: H::Output, proof: Proof<B, K, H>) -> Result<Self, Error> {
        let Some(leaf) = proof.leaf() else {
            // The empty proof folds to the empty root alone, and there is nothing to hold.
            return if root == empty_root::<H>() {
                Ok(Self::new(root))
            } else {
                Err(Error::RootMismatch)
            };
        };
        // The key is the proof's own, so the entry is occupied or the proof is refused.
        proof.verify(&root, &leaf.key)?;
        Ok(Self {
            root,
            current: Some(proof),
        })
    }

    /// The root of the tree being walked.
    pub fn root(&self) -> &H::Output {
        &self.root
    }

    /// The current entry's full proof; `None` before the first entry.
    pub fn proof(&self) -> Option<&Proof<B, K, H>> {
        self.current.as_ref()
    }

    /// The current entry's full proof with its storage; `None` before the first entry.
    pub fn into_proof(self) -> Option<Proof<B, K, H>> {
        self.current
    }

    /// The current entry; `None` before the first.
    pub fn current(&self) -> Option<OccupiedEntry<'_, K, H>> {
        self.current
            .as_ref()
            .map(|proof| OccupiedEntry::from_verified(proof.view()))
    }

    /// Whether nothing follows: the current key is the largest, since its path never turns
    /// left, or the tree is empty.
    pub fn is_done(&self) -> bool {
        match &self.current {
            None => self.root == empty_root::<H>(),
            Some(_) => self.turn().is_none(),
        }
    }

    /// The number of bytes [`next_into`](Self::next_into) writes for `proof`: the proof's own
    /// length, plus the step at `C` and the steps above it if the proof is a truncated one.
    pub fn next_len(&self, proof: &Proof<impl AsRef<[u8]>, K, H>) -> usize {
        let spliced = match self.turn() {
            Some(turn) if lies_below(proof, turn.crit_bit) => (1 + turn.above) * Step::<K, H>::LEN,
            _ => 0,
        };
        proof.as_bytes().len() + spliced
    }

    /// Accepts `proof` as the entry after the current one, or as the first entry of a fresh
    /// walk, and moves to it: that entry's full proof is written into `buf`, which becomes
    /// the current proof, and the entry is returned.
    ///
    /// `proof` is either the entry's full proof or the part of its path below the branch
    /// where it parts from the current entry ([`Proof::below`]), at the host's choice on
    /// every step; the walk tells the two apart by whether every step lies below that
    /// branch, which a full proof of the next entry never does, since it has a step at the
    /// branch itself. The first entry has nothing to be cut below and comes in full. A proof
    /// that does not fold to the root, once completed, is [`Error::RootMismatch`]; one that
    /// does but is not the next entry in key order is [`Error::OutOfOrder`], as is any proof
    /// once the walk is done. A refused proof leaves the walk as it was.
    ///
    /// `buf` must be exactly [`next_len`](Self::next_len) bytes, or this panics.
    pub fn next_into(
        &mut self,
        proof: &Proof<impl AsRef<[u8]>, K, H>,
        mut buf: B,
    ) -> Result<OccupiedEntry<'_, K, H>, Error>
    where
        B: AsMut<[u8]>,
    {
        assert_eq!(
            buf.as_ref().len(),
            self.next_len(proof),
            "the buffer is not `next_len` bytes"
        );
        if self.is_done() {
            return Err(Error::OutOfOrder);
        }
        // The root is not the empty one, so the empty proof is not its.
        let Some(leaf) = proof.leaf() else {
            return Err(Error::RootMismatch);
        };

        // The entry's full proof: the host's as it is, or the host's steps spliced onto the
        // current proof's steps above `C`, with the step at `C` taking the left child as its
        // sibling, which is what the walk is leaving: the current leaf folded up the steps
        // below `C`.
        let turn = self.turn();
        match &turn {
            Some(turn) if lies_below(proof, turn.crit_bit) => {
                let left = fold(
                    leaf_digest::<K, H>(&turn.leaf.key, &turn.leaf.value),
                    turn.current.steps().take(turn.below),
                    &turn.leaf.key,
                );
                let at_c = Step {
                    crit_bit: turn.crit_bit,
                    sibling: left,
                };
                write_into(
                    buf.as_mut(),
                    &leaf,
                    proof
                        .steps()
                        .chain(iter::once(at_c))
                        .chain(turn.current.steps().skip(turn.below + 1)),
                );
            }
            _ => buf.as_mut().copy_from_slice(proof.as_bytes()),
        }
        // Parsed and held against the root before it replaces the current proof. The key is
        // the proof's own, so the entry is occupied or the proof is refused.
        let new = Proof::parse(buf)?;
        new.verify(&self.root, &leaf.key)?;

        // The successor rule: the entry parts from the current one at `C`, where the current
        // key has 0 since it turned left there, so the entry has 1 and lies on the far side of
        // that branch; and it turns left at every branch below `C`, so it is the smallest key
        // there. The first entry turns left at every branch, so it is the smallest key of all.
        let lower = match &turn {
            None => None,
            Some(turn) => {
                if crit_bit(&turn.leaf.key, &leaf.key) != Some(turn.crit_bit) {
                    return Err(Error::OutOfOrder);
                }
                Some(turn.crit_bit)
            }
        };
        if new
            .steps()
            .take_while(|step| lower.is_none_or(|c| step.crit_bit > c))
            .any(|step| Side::of(&leaf.key, step.crit_bit) == Side::Right)
        {
            return Err(Error::OutOfOrder);
        }

        Ok(OccupiedEntry::from_verified(
            self.current.insert(new).view(),
        ))
    }

    /// Where the next entry parts from the current one: `None` before the first entry, and at
    /// the last one, whose path never turns left.
    fn turn(&self) -> Option<Turn<'_, B, K, H>> {
        let current = self.current.as_ref()?;
        // The current proof is an entry's, so it has a leaf.
        let leaf = current.leaf()?;
        let (below, step) = current
            .steps()
            .enumerate()
            .find(|(_, step)| Side::of(&leaf.key, step.crit_bit) == Side::Left)?;
        Some(Turn {
            current,
            leaf,
            crit_bit: step.crit_bit,
            below,
            above: current.steps().len() - below - 1,
        })
    }
}

#[cfg(feature = "use_std")]
impl<K: Key, H: HashFn> Walk<Vec<u8>, K, H> {
    /// [`next_into`](Self::next_into) with a vector of the right length.
    pub fn next(
        &mut self,
        proof: &Proof<impl AsRef<[u8]>, K, H>,
    ) -> Result<OccupiedEntry<'_, K, H>, Error> {
        let buf = vec![0; self.next_len(proof)];
        self.next_into(proof, buf)
    }
}

// By hand for the reason given above the impls in `common/proof.rs`.
#[cfg(feature = "debug")]
impl<B: AsRef<[u8]>, K: Key, H: HashFn> fmt::Debug for Walk<B, K, H> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Walk")
            .field("root", &self.root.as_ref())
            .field("current", &self.current())
            .finish()
    }
}

#[cfg(all(test, feature = "use_std"))]
mod tests {
    //! The six-leaf tree of the design note, built with `Tree`, whose `prove` is the oracle:
    //! after every accepted step the walk's proof must be the entry's own full proof, byte for
    //! byte. A branch is labelled with its crit bit.
    //!
    //! ```text
    //!                      (0)
    //!                   /       \
    //!               (1)           (7)
    //!              /    \         /   \
    //!          (4)      (2)      E     F
    //!         /   \    /   \
    //!        A     B  C     D
    //! ```

    use super::*;
    use crate::trie::common::Sha256;
    use crate::trie::prover::Tree;

    type Key1 = [u8; 1];
    type T = Tree<Key1, Vec<u8>, Sha256>;
    type W = Walk<Vec<u8>, Key1, Sha256>;
    type P = Proof<Vec<u8>, Key1, Sha256>;

    const A: Key1 = [0b0000_0000];
    const B: Key1 = [0b0000_1111];
    const C: Key1 = [0b0100_0000];
    const D: Key1 = [0b0110_0000];
    const E: Key1 = [0b1000_0000];
    const F: Key1 = [0b1000_0001];
    const KEYS: [Key1; 6] = [A, B, C, D, E, F];

    /// The six-leaf tree; a key's value is its byte.
    fn tree() -> T {
        T::from_entries(KEYS.map(|key| (key, key.to_vec())))
    }

    /// What the host sends, in order: A's full proof, then each entry's part below the branch
    /// where it parts from the previous one.
    fn proofs(tree: &T) -> Vec<P> {
        tree.walk().map(|(_, _, proof)| proof).collect()
    }

    /// `key`'s proof cut below bit `c`, as a host cuts it.
    fn cut(tree: &T, key: Key1, c: usize) -> P {
        let full = tree.prove(&key);
        P::parse(full.below(BitPos::new(c).unwrap()).as_bytes().to_vec()).unwrap()
    }

    /// The walk at `key`, reached the honest way.
    fn walk_to(tree: &T, key: Key1) -> W {
        let mut walk = W::new(tree.root());
        for (k, _, proof) in tree.walk() {
            walk.next(&proof).unwrap();
            if *k == key {
                break;
            }
        }
        walk
    }

    /// `walk` refuses `proof` with `error` and stays where it was.
    #[track_caller]
    fn refused(walk: &mut W, proof: &P, error: Error) {
        let before = walk.proof().cloned();
        assert_eq!(walk.next(proof).unwrap_err(), error);
        assert_eq!(
            walk.proof().cloned(),
            before,
            "a refused proof moved the walk"
        );
    }

    #[test]
    fn the_six_entries_in_order() {
        let tree = tree();
        let proofs = proofs(&tree);
        // One step per branch over the whole walk: A's three, then C's and E's one each.
        let steps: Vec<usize> = proofs.iter().map(|proof| proof.steps().len()).collect();
        assert_eq!(steps, [3, 0, 1, 0, 1, 0]);

        let mut walk = W::new(tree.root());
        assert!(!walk.is_done());
        assert!(walk.current().is_none() && walk.proof().is_none());
        for (key, proof) in KEYS.iter().zip(&proofs) {
            let entry = walk.next(proof).unwrap();
            assert_eq!(entry.key(), key);
            assert_eq!(entry.value(&key[..]).unwrap(), &key[..]);
            assert_eq!(
                walk.proof().unwrap(),
                &tree.prove(key),
                "the stored proof is {key:?}'s own"
            );
            assert_eq!(walk.current().unwrap().key(), key);
            assert_eq!(walk.is_done(), *key == F);
        }
        assert_eq!(walk.into_proof().unwrap(), tree.prove(&F));
    }

    #[test]
    fn a_full_proof_is_accepted_where_a_truncated_one_is_due() {
        let tree = tree();
        let mut walk = walk_to(&tree, A);
        walk.next(&tree.prove(&B)).unwrap();
        assert_eq!(walk.proof().unwrap(), &tree.prove(&B));
        // And the truncated form again after it.
        walk.next(&cut(&tree, C, 1)).unwrap();
        assert_eq!(walk.proof().unwrap(), &tree.prove(&C));
    }

    #[test]
    fn resumed_from_a_kept_proof() {
        // The binding's path: every step from the kept bytes alone.
        let tree = tree();
        let mut kept: Option<P> = None;
        for (key, _, proof) in tree.walk() {
            let mut walk = match kept.take() {
                None => W::new(tree.root()),
                Some(kept) => W::at(tree.root(), kept).unwrap(),
            };
            let len = walk.next_len(&proof);
            let entry = walk.next_into(&proof, vec![0; len]).unwrap();
            assert_eq!(entry.key(), key);
            assert_eq!(walk.is_done(), *key == F);
            kept = walk.into_proof();
        }
        assert_eq!(kept.unwrap(), tree.prove(&F));
        // `at` stands where the proof says.
        assert!(W::at(tree.root(), tree.prove(&F)).unwrap().is_done());
        assert!(!W::at(tree.root(), tree.prove(&A)).unwrap().is_done());
    }

    #[test]
    fn next_len_counts_the_step_at_c_and_the_shared_steps() {
        let tree = tree();
        // B's path has three steps and turns left at bit 1, with one step above it.
        let walk = walk_to(&tree, B);
        let part = cut(&tree, C, 1);
        assert_eq!(part.steps().len(), 1);
        assert_eq!(
            walk.next_len(&part),
            part.as_bytes().len() + 2 * Step::<Key1, Sha256>::LEN
        );
        assert_eq!(walk.next_len(&part), tree.prove(&C).as_bytes().len());
        let full = tree.prove(&C);
        assert_eq!(walk.next_len(&full), full.as_bytes().len());
    }

    #[test]
    fn the_empty_tree() {
        let root = empty_root::<Sha256>();
        let empty = || P::parse(Vec::new()).unwrap();
        let mut walk = W::new(root);
        assert!(walk.is_done());
        assert_eq!(walk.next(&empty()).unwrap_err(), Error::OutOfOrder);
        // The proof of the empty map describes the whole tree: nothing to walk, nothing held.
        let walk = W::at(root, empty()).unwrap();
        assert!(walk.is_done() && walk.proof().is_none() && walk.current().is_none());
    }

    #[test]
    fn one_leaf() {
        let tree = T::from_entries([(A, b"a".to_vec())]);
        let proofs = proofs(&tree);
        assert_eq!(proofs.len(), 1);
        assert_eq!(proofs[0].steps().len(), 0);
        let mut walk = W::new(tree.root());
        walk.next(&proofs[0]).unwrap();
        assert!(walk.is_done());
    }

    #[test]
    fn the_empty_proof_against_a_non_empty_root() {
        let tree = tree();
        let empty = P::parse(Vec::new()).unwrap();
        refused(&mut W::new(tree.root()), &empty, Error::RootMismatch);
        assert_eq!(W::at(tree.root(), empty).unwrap_err(), Error::RootMismatch);
    }

    #[test]
    fn a_skipped_entry() {
        let tree = tree();
        // C's part after A: its step at bit 2 is not below A's turn at 4, so it is taken for a
        // full proof, which it is not.
        refused(
            &mut walk_to(&tree, A),
            &cut(&tree, C, 1),
            Error::RootMismatch,
        );
        // C's full proof after A: genuine, but A and C part at bit 1, not 4.
        refused(&mut walk_to(&tree, A), &tree.prove(&C), Error::OutOfOrder);
    }

    #[test]
    fn a_repeated_entry() {
        let tree = tree();
        let mut walk = walk_to(&tree, B);
        // B's part, a bare leaf, splices to a proof that puts B on the wrong side of bit 1.
        refused(&mut walk, &cut(&tree, B, 4), Error::RootMismatch);
        // B's full proof: equal keys part nowhere.
        refused(&mut walk, &tree.prove(&B), Error::OutOfOrder);
    }

    #[test]
    fn going_backwards() {
        let tree = tree();
        refused(&mut walk_to(&tree, B), &tree.prove(&A), Error::OutOfOrder);
    }

    #[test]
    fn not_the_first_entry() {
        let tree = tree();
        // B turns right at bit 4.
        refused(&mut W::new(tree.root()), &tree.prove(&B), Error::OutOfOrder);
        // A bare leaf is a full proof only of a one-leaf tree.
        refused(
            &mut W::new(tree.root()),
            &cut(&tree, B, 4),
            Error::RootMismatch,
        );
    }

    #[test]
    fn anything_after_the_last_entry() {
        let tree = tree();
        let mut walk = walk_to(&tree, F);
        assert!(walk.is_done());
        refused(&mut walk, &tree.prove(&A), Error::OutOfOrder);
        refused(&mut walk, &cut(&tree, F, 7), Error::OutOfOrder);
    }

    #[test]
    fn not_the_smallest_beyond_the_branch() {
        let tree = tree();
        // D's part where C's is due splices to D's genuine proof, which holds against the
        // root; but D turns right at bit 2, so C lies between.
        refused(&mut walk_to(&tree, B), &cut(&tree, D, 1), Error::OutOfOrder);
    }

    #[test]
    fn a_cut_one_step_too_many_or_too_few() {
        let tree = tree();
        // C's part cut below the root carries the step at bit 1: taken for a full proof, it
        // stops short of the root.
        refused(
            &mut walk_to(&tree, B),
            &cut(&tree, C, 0),
            Error::RootMismatch,
        );
        // E's bare leaf where its step at bit 7 is due: the splice lacks that step.
        refused(
            &mut walk_to(&tree, D),
            &cut(&tree, E, 7),
            Error::RootMismatch,
        );
    }

    #[test]
    fn a_proof_of_another_tree() {
        let tree = tree();
        let other = T::from_entries(KEYS.map(|key| (key, b"x".to_vec())));
        assert_eq!(
            W::at(tree.root(), other.prove(&A)).unwrap_err(),
            Error::RootMismatch
        );
        let (_, _, part) = other.walk().nth(1).unwrap();
        refused(&mut walk_to(&tree, A), &part, Error::RootMismatch);
    }

    #[test]
    #[should_panic(expected = "the buffer is not `next_len` bytes")]
    fn the_buffer_must_be_next_len_bytes() {
        let tree = tree();
        let mut walk = W::new(tree.root());
        let proof = tree.prove(&A);
        let len = walk.next_len(&proof);
        let _ = walk.next_into(&proof, vec![0; len + 1]);
    }
}
