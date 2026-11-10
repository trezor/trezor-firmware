//! The differential test: after every change, the root the verifier derives from the proof,
//! the incremental prover's root and the root of a tree rebuilt from scratch must agree, every
//! stored key must still verify, and a walk through the prover's proofs must visit exactly the
//! model's entries in order.
//!
//! The rebuild is the definition of the canonical form, so any disagreement is a bug in the
//! incremental prover or the verifier, and checking after every operation names the operation.
//! Keys come in several geometries and widths so that branches land at different depths in the
//! key.

use std::collections::{BTreeMap, BTreeSet};

use rand::seq::{IndexedRandom as _, IteratorRandom as _};
use rand::{Rng as _, SeedableRng as _};
// Seeded, so a failure reproduces from the seed; the stream is stable across patch releases.
use rand_xorshift::XorShiftRng as Rng;
use trezor_ward::trie::{Entry, Sha256, Walk, empty_root};

use crate::{T, Val};

/// A random change is a set or a removal with equal probability.
const REMOVE_PROBABILITY: f64 = 0.5;

/// The reference the tree is checked against: what the driver knows it has set and removed.
type Model<const N: usize> = BTreeMap<[u8; N], Val>;
type Digest = [u8; 32];

fn value(rng: &mut Rng) -> Val {
    let len = 1 + rng.random_range(0..5);
    (0..len).map(|_| rng.random()).collect()
}

mod keys {
    //! Key geometries: each decides where the branches land in the key.

    use super::*;

    fn distinct<const N: usize>(n: usize, mut generate: impl FnMut() -> [u8; N]) -> Vec<[u8; N]> {
        let mut keys = BTreeSet::new();
        while keys.len() < n {
            keys.insert(generate());
        }
        keys.into_iter().collect()
    }

    /// Independent keys, what HMAC outputs look like: shallow trees.
    pub(super) fn random<const N: usize>(rng: &mut Rng, n: usize) -> Vec<[u8; N]> {
        distinct(n, || {
            let mut key = [0; N];
            rng.fill(&mut key[..]);
            key
        })
    }

    /// Keys agreeing on their first five eighths: every branch sits deep in the key.
    pub(super) fn shared_prefix<const N: usize>(rng: &mut Rng, n: usize) -> Vec<[u8; N]> {
        distinct(n, || {
            let mut key = [0xab; N];
            rng.fill(&mut key[N * 5 / 8..]);
            key
        })
    }

    /// Key `i` is `first + i` one-bits then zeros, so the tree is a spine with a branch at every
    /// bit from `first` up and one leaf per level: the longest proofs, and every removal or
    /// re-insertion moves a whole subtree a level down or up.
    pub(super) fn ladder<const N: usize>(first: usize, n: usize) -> Vec<[u8; N]> {
        (first..(first + n).min(8 * N + 1))
            .map(|ones| {
                let mut key = [0; N];
                (0..ones).for_each(|j| key[j / 8] |= 0x80 >> (j % 8));
                key
            })
            .collect()
    }

    /// All three geometries at once, chosen per key, with the ladder's rungs picked at random.
    pub(super) fn mixed<const N: usize>(rng: &mut Rng, n: usize) -> Vec<[u8; N]> {
        distinct(n, || match rng.random_range(0..3) {
            0 => random(rng, 1)[0],
            1 => shared_prefix(rng, 1)[0],
            _ => ladder(rng.random_range(0..=8 * N), 1)[0],
        })
    }
}

/// Sets every key, then `steps` random changes over `keys`, then a drain to the empty tree.
fn run<const N: usize>(keys: &[[u8; N]], rng: &mut Rng, steps: usize) {
    let mut tree = T::<N>::new();
    let mut model = Model::<N>::new();
    let mut root = empty_root::<Sha256>();

    for &key in keys {
        change(&mut tree, &mut model, &mut root, key, false, rng);
    }
    for _ in 0..steps {
        let key = *keys.choose(rng).unwrap();
        let remove = rng.random_bool(REMOVE_PROBABILITY);
        change(&mut tree, &mut model, &mut root, key, remove, rng);
    }
    while !model.is_empty() {
        let key = *model.keys().choose(rng).unwrap();
        change(&mut tree, &mut model, &mut root, key, true, rng);
    }
    assert_eq!(root, empty_root::<Sha256>());
}

/// One change, made by the verifier on its root from the proof, by the prover on its map, and
/// on the model.
fn change<const N: usize>(
    tree: &mut T<N>,
    model: &mut Model<N>,
    root: &mut Digest,
    key: [u8; N],
    remove: bool,
    rng: &mut Rng,
) {
    let proof = tree.prove(&key);
    let entry = proof
        .verify(root, &key)
        .expect("the prover's own proof verifies against its own root");

    *root = match (entry, model.get(&key).cloned()) {
        (Entry::Occupied(entry), Some(old)) => {
            assert_eq!(entry.value(&old).unwrap(), &old);
            if remove {
                assert_eq!(tree.remove(&key), Some(old));
                model.remove(&key);
                entry.remove()
            } else {
                let new = value(rng);
                let derived = entry.replace(&new);
                assert_eq!(tree.set(key, new.clone()), Some(old));
                model.insert(key, new);
                derived
            }
        }
        (Entry::Vacant(entry), None) => {
            if remove {
                assert_eq!(tree.remove(&key), None);
                *root
            } else {
                let new = value(rng);
                let derived = entry.insert(&new);
                assert_eq!(tree.set(key, new.clone()), None);
                model.insert(key, new);
                derived
            }
        }
        (entry, stored) => panic!("presence of {key:?} disagrees: {entry:?} vs {stored:?}"),
    };

    check(tree, model, *root);
}

/// The tree holds what the model holds, the three roots agree, and so do all proofs; and a
/// walk through the prover's proofs is the model, in order.
fn check<const N: usize>(tree: &T<N>, model: &Model<N>, derived: Digest) {
    assert_eq!(tree.root(), derived, "incremental prover vs verifier");
    let rebuilt = T::<N>::from_entries(model.iter().map(|(key, value)| (*key, value.clone())));
    assert_eq!(rebuilt.root(), derived, "canonical rebuild vs verifier");
    assert!(tree.iter().eq(model.iter()), "entries in key order");
    assert_eq!(tree.len(), model.len());
    for (key, value) in model {
        assert_eq!(tree.get(key), Some(value));
        let proof = tree.prove(key);
        assert_eq!(
            rebuilt.prove(key),
            proof,
            "the two provers' proofs for {key:?}"
        );
        match proof.verify(&derived, key).unwrap() {
            Entry::Occupied(entry) => assert_eq!(entry.value(value).unwrap(), value),
            Entry::Vacant(_) => panic!("{key:?} is stored but proves absent"),
        }
    }
    walk(tree, model, derived);
}

/// The prover's walk, one truncated proof per entry, is accepted by the verifier's walk and
/// visits the model's entries in the model's order; after every step the walk's proof is the
/// entry's own full proof, and the step is also made again from the kept proof alone, as a
/// device that keeps nothing between messages makes it; the walk is done where the model ends.
fn walk<const N: usize>(tree: &T<N>, model: &Model<N>, derived: Digest) {
    let mut walk = Walk::new(derived);
    let mut expected = model.iter();
    for (key, value, proof) in tree.walk() {
        assert_eq!(expected.next(), Some((key, value)), "walk order");
        let entry = walk.next(&proof).expect("the prover's walk is accepted");
        assert_eq!(entry.key(), key);
        assert_eq!(entry.value(value).unwrap(), value);
        let kept = walk.proof().expect("a proof after a step");
        assert_eq!(kept, &tree.prove(key), "the walk's proof is {key:?}'s own");
        walk = Walk::at(derived, kept.clone()).expect("the kept proof resumes the walk");
    }
    assert_eq!(
        expected.next(),
        None,
        "the walk stopped before the model's end"
    );
    assert!(walk.is_done(), "the walk is not done where the model ends");
}

const SEED: u64 = 0;
/// Key widths in bytes. A narrow key space is tiny and its keys read as bit patterns; normal
/// is WARD's width, the widest whose crit bits take one byte; a wide key's take two, and
/// huge is the narrowest whose take three.
const NARROW: usize = 1;
const NORMAL: usize = 32;
const WIDE: usize = 64;
const HUGE: usize = 8193;
/// Keys per run. Enough for a tree five or six levels deep; more only slows the rebuilds.
const KEYS: usize = 16;
/// Random changes per run: each key is changed about a dozen times.
const STEPS: usize = 200;

#[test]
fn random_keys() {
    let mut rng = Rng::seed_from_u64(SEED);
    // Narrow keys have only 256 values: take more of them, for a dense tree.
    run::<NARROW>(&keys::random(&mut rng, 3 * KEYS), &mut rng, STEPS);
    run::<NORMAL>(&keys::random(&mut rng, KEYS), &mut rng, STEPS);
    run::<WIDE>(&keys::random(&mut rng, KEYS), &mut rng, STEPS);
}

#[test]
fn shared_prefix_keys() {
    let mut rng = Rng::seed_from_u64(SEED);
    // Not narrow: five eighths of one byte is no prefix at all.
    run::<NORMAL>(&keys::shared_prefix(&mut rng, KEYS), &mut rng, STEPS);
    run::<WIDE>(&keys::shared_prefix(&mut rng, KEYS), &mut rng, STEPS);
}

#[test]
fn ladder_keys() {
    let mut rng = Rng::seed_from_u64(SEED);
    // Every rung a byte has: a branch at each of its eight bits.
    run::<NARROW>(&keys::ladder(0, 9), &mut rng, STEPS);
    run::<NORMAL>(&keys::ladder(0, KEYS), &mut rng, STEPS);
    // Starts past the last bit of a normal key, so every crit bit needs its second byte.
    run::<WIDE>(&keys::ladder(8 * NORMAL, KEYS), &mut rng, STEPS);
    // A branch at each bit of the last byte, which only the third byte of a crit bit reaches;
    // few changes, since every leaf hashes eight kilobytes of key.
    run::<HUGE>(&keys::ladder(8 * (HUGE - 1), 9), &mut rng, STEPS / 10);
}

#[test]
fn mixed_keys() {
    let mut rng = Rng::seed_from_u64(SEED);
    run::<NARROW>(&keys::mixed(&mut rng, KEYS), &mut rng, STEPS);
    run::<NORMAL>(&keys::mixed(&mut rng, KEYS), &mut rng, STEPS);
    run::<WIDE>(&keys::mixed(&mut rng, KEYS), &mut rng, STEPS);
}
