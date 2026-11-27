//! The exhaustive test: over keys of a few bits, every set of keys there is. For each set the
//! tree is built, and every key of the key space, in the set or not, is looked up in it. The
//! proof must say which of the two it is, and the change it then allows, removing a key that
//! is there or inserting one that is not, must lead to the root of the set that results, as
//! building that set from scratch gives it.
//!
//! Where the differential test samples trees over wide keys, this one goes through every
//! shape a tree of that depth can take and every single-key change between them.

use std::collections::{BTreeMap, BTreeSet};
use std::fmt;

use trezor_ward::trie::{Entry, Key, Root, Sha256, Tree};

/// A key shorter than a byte: `N` bits, 1 to 7, at the top of one byte, the rest zero. No
/// other byte makes one, so a test over `N`-bit keys cannot stray into a wider key space.
#[derive(Clone, Copy, PartialEq, Eq)]
struct SubByte<const N: usize>([u8; 1]);

impl<const N: usize> SubByte<N> {
    /// How many keys there are: 128 at most.
    const COUNT: u8 = {
        assert!(0 < N && N < 8, "a sub-byte key has 1 to 7 bits");
        1 << N
    };

    /// Every key, in order.
    fn all() -> impl Iterator<Item = Self> {
        // A number below `COUNT` has `N` bits, so the shift loses none of them.
        (0..Self::COUNT).map(|number| Self::from_bytes([number << (8 - N)]))
    }

    /// The key's place in that order.
    fn number(self) -> u8 {
        self.0[0] >> (8 - N)
    }
}

impl<const N: usize> Key for SubByte<N> {
    type Bytes = [u8; 1];

    fn as_bytes(&self) -> &[u8; 1] {
        &self.0
    }

    /// Refuses a byte with a bit beyond the key's `N`, also when the trie reads a key back
    /// from a proof.
    fn from_bytes(bytes: [u8; 1]) -> Self {
        assert_eq!(
            bytes[0] & (0xff >> N),
            0,
            "{:#010b} is not a key of {N} bits",
            bytes[0]
        );
        Self(bytes)
    }
}

impl<const N: usize> fmt::Debug for SubByte<N> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        // The key's `N` bits after the `0b` prefix, which counts towards the width.
        write!(f, "{:#0width$b}", self.number(), width = 2 + N)
    }
}

/// The value stored under a key: the key's own byte.
fn value<const N: usize>(key: SubByte<N>) -> [u8; 1] {
    *key.as_bytes()
}

/// A set of `N`-bit keys: bit `i` says whether key number `i` is in it. The widest sub-byte
/// key space has 128 keys, one for each bit there is.
#[derive(Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
struct KeySet<const N: usize>(u128);

impl<const N: usize> KeySet<N> {
    const EMPTY: Self = Self(0);
    /// The whole key space.
    const FULL: Self = Self(u128::MAX >> (128 - (1u32 << N)));

    /// Every set there is, from the empty one to the whole key space.
    fn all() -> impl Iterator<Item = Self> {
        (Self::EMPTY.0..=Self::FULL.0).map(Self)
    }

    fn contains(self, key: SubByte<N>) -> bool {
        self.0 >> key.number() & 1 == 1
    }

    fn with(self, key: SubByte<N>) -> Self {
        Self(self.0 | 1 << key.number())
    }

    fn without(self, key: SubByte<N>) -> Self {
        Self(self.0 & !(1 << key.number()))
    }

    fn keys(self) -> impl Iterator<Item = SubByte<N>> {
        SubByte::all().filter(move |&key| self.contains(key))
    }

    /// The tree holding exactly this set, built from scratch.
    fn tree(self) -> Tree<SubByte<N>, [u8; 1], Sha256> {
        Tree::from_entries(self.keys().map(|key| (key, value(key))))
    }
}

impl<const N: usize> fmt::Debug for KeySet<N> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_set().entries(self.keys()).finish()
    }
}

// The two helpers above, on their own.

#[test]
fn a_sub_byte_key_is_the_top_bits_of_a_byte() {
    let keys: Vec<_> = SubByte::<2>::all().collect();
    let bytes: Vec<_> = keys.iter().map(|key| key.as_bytes()[0]).collect();
    assert_eq!(bytes, [0b0000_0000, 0b0100_0000, 0b1000_0000, 0b1100_0000]);
    let numbers: Vec<_> = keys.iter().map(|key| key.number()).collect();
    assert_eq!(numbers, [0, 1, 2, 3]);
    assert_eq!(format!("{:?}", keys[1]), "0b01");
    // The widest key leaves one bit of the byte unused.
    assert_eq!(SubByte::<7>::all().count(), 128);
    assert_eq!(SubByte::<7>::all().last().unwrap().as_bytes(), &[0xfe]);
}

#[test]
#[should_panic(expected = "0b11111000 is not a key of 4 bits")]
fn a_sub_byte_key_has_no_bit_beyond_its_own() {
    SubByte::<4>::from_bytes([0b1111_1000]);
}

#[test]
fn a_key_set_holds_the_keys_put_into_it() {
    let keys: Vec<_> = SubByte::<2>::all().collect();
    assert_eq!(KeySet::<2>::all().count(), 16);
    assert_eq!(KeySet::<2>::EMPTY.keys().count(), 0);
    assert_eq!(KeySet::<2>::FULL.keys().collect::<Vec<_>>(), keys);

    let set = KeySet::EMPTY.with(keys[1]).with(keys[3]);
    assert_eq!(set.keys().collect::<Vec<_>>(), [keys[1], keys[3]]);
    assert!(set.contains(keys[1]));
    assert!(!set.contains(keys[2]));
    assert_eq!(set.without(keys[1]).keys().collect::<Vec<_>>(), [keys[3]]);
    assert_eq!(set.without(keys[2]), set);
    assert_eq!(format!("{set:?}"), "{0b01, 0b11}");
}

#[test]
fn a_key_set_has_room_for_the_widest_key_space() {
    let last = SubByte::<7>::all().last().unwrap();
    assert_eq!(last.number(), 127);
    assert_eq!(KeySet::<7>::FULL.keys().count(), 128);
    assert!(KeySet::EMPTY.with(last).contains(last));
    assert!(!KeySet::<7>::FULL.without(last).contains(last));
}

/// Goes through every set of `N`-bit keys and, in each, through every key.
fn every_key_set<const N: usize>() {
    // The root of every set: what a change has to arrive at.
    let roots: BTreeMap<_, _> = KeySet::<N>::all()
        .map(|set| (set, set.tree().root()))
        .collect();
    let mut seen = BTreeSet::new();
    assert!(
        roots.values().all(|root| seen.insert(root)),
        "two key sets share a root"
    );

    for (&set, start) in &roots {
        let tree = set.tree();
        for key in SubByte::<N>::all() {
            // Every change starts from the set's own root.
            let mut root = Root::trusted(*start);
            let proof = tree.prove(&key);
            let entry = root
                .entry(&key, &proof)
                .expect("the prover's own proof verifies against its own root");
            match entry {
                Entry::Occupied(entry) => {
                    assert!(set.contains(key), "{key:?} proves present in {set:?}");
                    assert_eq!(entry.value(&value(key)).unwrap(), &value(key));
                    entry.remove();
                    assert_eq!(
                        root.digest(),
                        &roots[&set.without(key)],
                        "removing {key:?} from {set:?}"
                    );
                }
                Entry::Vacant(entry) => {
                    assert!(!set.contains(key), "{key:?} proves absent from {set:?}");
                    entry.insert(&value(key));
                    assert_eq!(
                        root.digest(),
                        &roots[&set.with(key)],
                        "inserting {key:?} into {set:?}"
                    );
                }
            }
        }
    }
}

#[test]
fn one_bit_keys() {
    every_key_set::<1>();
}

#[test]
fn two_bit_keys() {
    every_key_set::<2>();
}

#[test]
fn three_bit_keys() {
    every_key_set::<3>();
}

/// 65536 key sets: about a second's work when optimized, most of a minute's when not.
#[test]
#[cfg_attr(
    debug_assertions,
    ignore = "slow without optimizations, run with --release"
)]
fn four_bit_keys() {
    every_key_set::<4>();
}
