//! The prover: the whole map, with every node's digest kept current, serving proofs for any
//! key. Host side; needs `std`.
//!
//! The tree is canonical by construction: every branch tests the first bit on which the keys
//! below it differ, so its shape, and therefore its root, depends on the key set alone, never
//! on the order of changes. [`Tree::from_entries`] builds it that way from scratch;
//! [`Tree::set`] and [`Tree::remove`] maintain it one change at a time. The two are
//! deliberately separate code paths: their agreement after every change is what the tests
//! check, and it is also what lets the verifier, which only ever derives roots one change at
//! a time, agree with a prover that rebuilt from scratch.

use super::common::{
    BitPos, HashFn, Hashable, Key, Leaf, Proof, Side, Step, bit, branch_digest, crit_bit,
    empty_root, key_bits, leaf_digest,
};

enum Node<K, V, H: HashFn> {
    Leaf {
        key: K,
        value: V,
        digest: H::Output,
    },
    Branch {
        crit_bit: BitPos,
        /// `[left, right]`: indexed by the key's crit bit.
        children: [Box<Node<K, V, H>>; 2],
        digest: H::Output,
    },
}

impl<K: Key, V: Hashable<H>, H: HashFn> Node<K, V, H> {
    fn leaf(key: K, value: V) -> Box<Self> {
        let digest = leaf_digest::<K, H>(&key, &value.digest());
        Box::new(Self::Leaf { key, value, digest })
    }

    fn branch(crit_bit: BitPos, children: [Box<Self>; 2]) -> Box<Self> {
        let digest = branch_digest::<H>(crit_bit, children[0].digest(), children[1].digest());
        Box::new(Self::Branch {
            crit_bit,
            children,
            digest,
        })
    }

    fn digest(&self) -> &H::Output {
        match self {
            Self::Leaf { digest, .. } | Self::Branch { digest, .. } => digest,
        }
    }

    /// The leaf a lookup for `key` ends at, reporting one step per branch passed, root-to-leaf.
    fn descend<'a>(&'a self, key: &K, mut visit: impl FnMut(Step<H>)) -> &'a Self {
        let mut node = self;
        while let Self::Branch {
            crit_bit, children, ..
        } = node
        {
            let (next, other) = Side::of(key, *crit_bit).pick(children.each_ref());
            visit(Step {
                crit_bit: *crit_bit,
                sibling: *other.digest(),
            });
            node = next;
        }
        node
    }
}

/// A possibly absent subtree.
type Link<K, V, H> = Option<Box<Node<K, V, H>>>;

/// An authenticated crit-bit tree holding the whole map.
pub struct Tree<K, V, H: HashFn> {
    top: Link<K, V, H>,
    len: usize,
}

impl<K: Key, V: Hashable<H>, H: HashFn> Default for Tree<K, V, H> {
    fn default() -> Self {
        Self::new()
    }
}

impl<K: Key, V: Hashable<H>, H: HashFn> Tree<K, V, H> {
    /// The empty map.
    pub fn new() -> Self {
        const {
            assert!(
                key_bits::<K>() <= BitPos::MAX.index() + 1,
                "a key has more bits than a BitPos can address"
            )
        };
        Self { top: None, len: 0 }
    }

    /// The tree over `entries`, built from scratch. Of several entries with one key, the last
    /// one in input order counts, as it would after setting them in that order.
    ///
    /// This is the definition of the canonical form: the keys are sorted, which is their
    /// MSB-first bit order, and each range is split at the first bit on which its first and
    /// last key differ. Sorted keys agree with both of those on every earlier bit, so that is
    /// the lowest bit on which the range disagrees, and the keys with a 1 there form a suffix.
    pub fn from_entries(entries: impl IntoIterator<Item = (K, V)>) -> Self {
        let mut tree = Self::new();
        let mut entries: Vec<(K, V)> = entries.into_iter().collect();
        // Stable sort after a reverse: of equal keys, the last in input order comes first, and
        // `dedup_by_key` keeps the first of each run.
        entries.reverse();
        entries.sort_by(|a, b| a.0.as_bytes().as_ref().cmp(b.0.as_bytes().as_ref()));
        entries.dedup_by_key(|entry| entry.0);
        tree.len = entries.len();
        if !entries.is_empty() {
            tree.top = Some(Self::build(entries));
        }
        tree
    }

    /// The canonical subtree over a sorted, non-empty range of distinct keys.
    fn build(mut entries: Vec<(K, V)>) -> Box<Node<K, V, H>> {
        let [first, .., last] = entries.as_slice() else {
            let (key, value) = entries.pop().expect("a non-empty range");
            return Node::leaf(key, value);
        };
        let c = crit_bit(&first.0, &last.0).expect("distinct keys");
        let split = entries.partition_point(|(key, _)| !bit(key, c));
        let right = entries.split_off(split);
        Node::branch(c, [Self::build(entries), Self::build(right)])
    }

    /// The root: what commits to the whole map.
    pub fn root(&self) -> H::Output {
        self.top
            .as_ref()
            .map_or_else(empty_root::<H>, |node| *node.digest())
    }

    /// The number of entries.
    pub fn len(&self) -> usize {
        self.len
    }

    /// Whether there are no entries.
    pub fn is_empty(&self) -> bool {
        self.len == 0
    }

    /// The value stored under `key`.
    pub fn get(&self, key: &K) -> Option<&V> {
        match self.top.as_ref()?.descend(key, |_| ()) {
            Node::Leaf { key: k, value, .. } if k == key => Some(value),
            _ => None,
        }
    }

    /// Stores `value` under `key`, returning the value it replaces.
    pub fn set(&mut self, key: K, value: V) -> Option<V> {
        let Some(top) = self.top.take() else {
            self.top = Some(Node::leaf(key, value));
            self.len = 1;
            return None;
        };
        // The first bit on which the key differs from the leaf its lookup ends at: where the
        // new branch goes; `None`: the key is present.
        let c = match top.descend(&key, |_| ()) {
            Node::Leaf { key: k, .. } => crit_bit(&key, k),
            Node::Branch { .. } => unreachable!("a lookup ends at a leaf"),
        };
        let (top, old) = Self::set_at(*top, key, value, c);
        self.top = Some(top);
        if old.is_none() {
            self.len += 1;
        }
        old
    }

    /// Walks down while the node branches on a bit before `c`, then either replaces the leaf
    /// (`c` is `None`) or splices a branch at `c` above whatever node the walk stopped at.
    fn set_at(
        node: Node<K, V, H>,
        key: K,
        value: V,
        c: Option<BitPos>,
    ) -> (Box<Node<K, V, H>>, Option<V>) {
        match node {
            // A branch on a bit before `c`: the change is further down, on the key's side.
            Node::Branch {
                crit_bit, children, ..
            } if c.is_none_or(|c| crit_bit < c) => {
                let side = Side::of(&key, crit_bit);
                let (hit, other) = side.pick(children);
                let (hit, old) = Self::set_at(*hit, key, value, c);
                (Node::branch(crit_bit, side.place(hit, other)), old)
            }
            // The key's own leaf: the value is replaced.
            Node::Leaf {
                key: k, value: old, ..
            } if c.is_none() => (Node::leaf(k, value), Some(old)),
            // The first node branching at or after `c`, or the terminal leaf: it moves under
            // the new branch unchanged, since a digest does not depend on depth.
            node => {
                let c = c.expect("an absent key differs from its terminal leaf");
                let children = Side::of(&key, c).place(Node::leaf(key, value), Box::new(node));
                (Node::branch(c, children), None)
            }
        }
    }

    /// Removes `key`, returning the value stored under it.
    pub fn remove(&mut self, key: &K) -> Option<V> {
        // Decided here, so that the rebuild below always has a leaf to take out.
        self.get(key)?;
        let top = self.top.take().expect("a present key has a tree");
        let (top, old) = Self::remove_at(*top, key);
        self.top = top;
        self.len -= 1;
        Some(old)
    }

    /// Removes `key`, which is present, from the subtree; the branch above the removed leaf
    /// collapses into its other child.
    fn remove_at(node: Node<K, V, H>, key: &K) -> (Link<K, V, H>, V) {
        match node {
            // The key's leaf: it goes, and whatever is above it collapses.
            Node::Leaf { value, .. } => (None, value),
            Node::Branch {
                crit_bit, children, ..
            } => {
                let side = Side::of(key, crit_bit);
                let (hit, other) = side.pick(children);
                match Self::remove_at(*hit, key) {
                    // The child was the leaf: this branch collapses into its other child,
                    // which keeps its digest since a digest does not depend on depth.
                    (None, old) => (Some(other), old),
                    // The leaf was further down: the branch stays, with a new digest.
                    (Some(hit), old) => (Some(Node::branch(crit_bit, side.place(hit, other))), old),
                }
            }
        }
    }

    /// The proof for `key`: its lookup path, whether or not `key` is present.
    pub fn prove(&self, key: &K) -> Proof<Vec<u8>, K, H> {
        let Some(top) = &self.top else {
            return Proof::empty();
        };
        let mut steps = Vec::new();
        let Node::Leaf { key, value, .. } = top.descend(key, |step| steps.push(step)) else {
            unreachable!("a lookup ends at a leaf");
        };
        let leaf = Leaf {
            key: *key,
            value: value.digest(),
        };
        Proof::build(&leaf, steps.into_iter().rev())
            .expect("a lookup path in a canonical tree is well formed")
    }

    /// The entries in key order, each with the proof a [`Walk`](crate::trie::Walk) accepts for
    /// it: the first entry's whole lookup path, then for every entry the part of its path
    /// below the branch where it parts from the previous one, which is all the walk needs
    /// since it holds the rest. The sum of these is one step per branch of the tree.
    pub fn walk(&self) -> impl Iterator<Item = (&K, &V, Proof<Vec<u8>, K, H>)> {
        let mut previous: Option<K> = None;
        self.iter().map(move |(key, value)| {
            let proof = self.prove(key);
            let proof = match previous.replace(*key) {
                None => proof,
                Some(previous) => {
                    let c = crit_bit(&previous, key).expect("the entries have distinct keys");
                    Proof::parse(proof.below(c).as_bytes().to_vec())
                        .expect("a prefix of a well-formed proof is well formed")
                }
            };
            (key, value, proof)
        })
    }

    /// The entries in key order; [`walk`](Self::walk) adds the proofs.
    pub fn iter(&self) -> Iter<'_, K, V, H> {
        // The stack starts with the root, if there is one.
        Iter {
            stack: self.top.as_deref().into_iter().collect(),
        }
    }
}

impl<'a, K: Key, V: Hashable<H>, H: HashFn> IntoIterator for &'a Tree<K, V, H> {
    type Item = (&'a K, &'a V);
    type IntoIter = Iter<'a, K, V, H>;

    fn into_iter(self) -> Self::IntoIter {
        self.iter()
    }
}

/// The entries of a [`Tree`] in key order.
pub struct Iter<'a, K, V, H: HashFn> {
    stack: Vec<&'a Node<K, V, H>>,
}

impl<'a, K, V, H: HashFn> Iterator for Iter<'a, K, V, H> {
    type Item = (&'a K, &'a V);

    fn next(&mut self) -> Option<Self::Item> {
        loop {
            match self.stack.pop()? {
                Node::Leaf { key, value, .. } => return Some((key, value)),
                Node::Branch { children, .. } => {
                    self.stack.push(&children[1]);
                    self.stack.push(&children[0]);
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::super::common::Sha256;
    use super::*;

    type Key1 = [u8; 1];
    type T = Tree<Key1, Vec<u8>, Sha256>;

    fn val(s: &[u8]) -> Vec<u8> {
        s.to_vec()
    }

    /// The four-leaf example of the design document, with its pinned root and proofs.
    const ABCD: [(Key1, &[u8]); 4] = [
        ([0b0000_0000], b"a"),
        ([0b0000_1111], b"b"),
        ([0b0100_0000], b"c"),
        ([0b1000_0000], b"d"),
    ];
    const ROOT: &str = "801c76a17f759146fdc24b4bbc66c1f6fbbe63cf0c5a15121c274e9e7146c54c";
    const PROOF_A: &str = "00c7985a722bc82b44027b3692ec1b79a2e86267e2577b9cc0e09a9dee4515e0f6\
        000466c808c49e8d051a943939af6530d34afbb3ddb6054d25823313f41a22c4cfad\
        0001567cd4f15980338f90a766a300b301b7c4ad401dad3b2e327bec281bb76fb983\
        0000d3fd399d63bafbde1938abcd6a556f7fd546ceb76c352754472f4e0ecf564aa9";
    const PROOF_D: &str = "80579dcf4b2884b4d6212e2ab4db770ebd5884415869e907457694ddd221973fdf\
        00008451117f60bd9938110b0b0539e0e7bb42367564f17b55bdfd27cbcbf9aa5568";

    fn abcd() -> impl Iterator<Item = (Key1, Vec<u8>)> {
        ABCD.into_iter().map(|(k, v)| (k, val(v)))
    }

    #[test]
    fn the_empty_tree() {
        let tree = T::new();
        assert_eq!(tree.root(), empty_root::<Sha256>());
        assert!(tree.is_empty());
        assert_eq!(tree.get(&[0]), None);
        assert_eq!(tree.iter().count(), 0);
        assert!(tree.prove(&[0]).is_empty());
        assert_eq!(T::from_entries([]).root(), tree.root());
    }

    #[test]
    fn one_leaf_is_its_own_root() {
        let mut tree = T::new();
        assert_eq!(tree.set([7], val(b"x")), None);
        let digest = Hashable::<Sha256>::digest(&val(b"x"));
        assert_eq!(tree.root(), leaf_digest::<Key1, Sha256>(&[7], &digest));
        assert_eq!(tree.len(), 1);
        assert_eq!(tree.prove(&[7]).steps().len(), 0);
        assert_eq!(tree.remove(&[7]), Some(val(b"x")));
        assert_eq!(tree.root(), empty_root::<Sha256>());
    }

    #[test]
    fn bulk_and_incremental_agree_on_the_pinned_example() {
        let bulk = T::from_entries(abcd());
        let mut incremental = T::new();
        for (key, value) in ABCD.into_iter().rev() {
            incremental.set(key, val(value));
        }
        assert_eq!(hex::encode(bulk.root()), ROOT);
        assert_eq!(incremental.root(), bulk.root());
        assert_eq!(hex::encode(bulk.prove(&[0b0000_0000]).as_bytes()), PROOF_A);
        assert_eq!(hex::encode(bulk.prove(&[0b0010_0000]).as_bytes()), PROOF_A); // absent E ends at A
        assert_eq!(
            hex::encode(incremental.prove(&[0b1000_0000]).as_bytes()),
            PROOF_D
        );
    }

    #[test]
    fn get_set_remove() {
        let mut tree = T::from_entries(abcd());
        assert_eq!(tree.get(&[0b0000_1111]), Some(&val(b"b")));
        assert_eq!(tree.get(&[0b0000_1110]), None);
        assert_eq!(tree.set([0b0000_1111], val(b"b2")), Some(val(b"b")));
        assert_eq!(tree.len(), 4);
        assert_eq!(tree.remove(&[0b0000_1110]), None);
        assert_eq!(tree.remove(&[0b0000_1111]), Some(val(b"b2")));
        assert_eq!(tree.len(), 3);
        assert_eq!(tree.get(&[0b0000_1111]), None);
        let keys: Vec<Key1> = tree.iter().map(|(k, _)| *k).collect();
        assert_eq!(keys, [[0b0000_0000], [0b0100_0000], [0b1000_0000]]);
    }

    #[test]
    fn from_entries_keeps_the_last_of_equal_keys() {
        let tree = T::from_entries([([1], val(b"first")), ([2], val(b"x")), ([1], val(b"last"))]);
        assert_eq!(tree.len(), 2);
        assert_eq!(tree.get(&[1]), Some(&val(b"last")));
        let mut incremental = T::new();
        incremental.set([2], val(b"x"));
        incremental.set([1], val(b"first"));
        incremental.set([1], val(b"last"));
        assert_eq!(tree.root(), incremental.root());
    }
}
