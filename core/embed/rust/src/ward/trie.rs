//! The WARD trie on the device: `trezor_ward`'s verifier over the firmware's
//! SHA-256, with 32-byte entry keys. The device holds only the root; every root
//! it derives comes from proofs held against a `Root` it trusts. A `Root` here
//! lives for one call: the caller passes the root's digest in and stores what
//! comes back, so a derived root is a candidate until the caller installs it.

use crypto::sha256::{Sha256 as Sha256Hasher, Sha256Ctx};
use trezor_ward::trie::{
    bit, branch_digest, crit_bit, leaf_digest, BitPos, Entry, Error, HashFn, Leaf, Proof, Root,
    Step, Walk,
};

/// SHA-256 from trezor-crypto.
pub enum Sha256 {}

impl HashFn for Sha256 {
    type Output = Digest;

    fn digest(parts: &[&[u8]]) -> Digest {
        let mut ctx = Sha256Ctx::default();
        let mut sha = Sha256Hasher::new(&mut ctx);
        for part in parts {
            sha.update(part);
        }
        sha.finalize()
    }
}

pub type Digest = [u8; 32];
pub type Key = [u8; 32];

/// The most updates one batch can carry: the intents a wallet can queue
/// (`storage.ward_store.MAX_PENDING`).
pub const BATCH_MAX: usize = 8;

/// A value already committed to by its digest: the leaf commitment the firmware
/// computes over a leaf's key type and both encoded parts.
struct Committed<'a>(&'a Digest);

impl trezor_ward::trie::Hashable<Sha256> for Committed<'_> {
    fn digest(&self) -> Digest {
        *self.0
    }
}

fn parse(proof: &[u8]) -> Result<Proof<&[u8], Key, Sha256>, Error> {
    Proof::parse(proof)
}

/// The value digest under `key` in the tree with `root`, or `None` if `key` is
/// absent.
pub fn lookup(root: &Digest, key: &Key, proof: &[u8]) -> Result<Option<Digest>, Error> {
    let proof = parse(proof)?;
    let root = Root::<Sha256>::trusted(*root);
    Ok(root.get(key, &proof)?.map(|entry| *entry.digest()))
}

/// The root after inserting `commit` under `key`, which must be absent.
pub fn insert(root: &Digest, key: &Key, proof: &[u8], commit: &Digest) -> Result<Digest, Refusal> {
    let proof = parse(proof)?;
    let mut root = Root::<Sha256>::trusted(*root);
    match root.entry(key, &proof)? {
        Entry::Vacant(entry) => entry.insert(&Committed(commit)),
        Entry::Occupied(_) => return Err(Refusal::Present),
    }
    Ok(*root.digest())
}

/// The root after replacing the value of `key`, which must be present.
pub fn replace(root: &Digest, key: &Key, proof: &[u8], commit: &Digest) -> Result<Digest, Refusal> {
    let mut root = Root::<Sha256>::trusted(*root);
    replace_in(&mut root, key, proof, commit)?;
    Ok(*root.digest())
}

/// The root after removing `key`, which must be present.
pub fn remove(root: &Digest, key: &Key, proof: &[u8]) -> Result<Digest, Refusal> {
    let proof = parse(proof)?;
    let mut root = Root::<Sha256>::trusted(*root);
    match root.entry(key, &proof)? {
        Entry::Occupied(entry) => entry.remove(),
        Entry::Vacant(_) => return Err(Refusal::Absent),
    }
    Ok(*root.digest())
}

fn replace_in(
    root: &mut Root<Sha256>,
    key: &Key,
    proof: &[u8],
    commit: &Digest,
) -> Result<(), Refusal> {
    let proof = parse(proof)?;
    match root.entry(key, &proof)? {
        Entry::Occupied(entry) => entry.replace(&Committed(commit)),
        Entry::Vacant(_) => return Err(Refusal::Absent),
    }
    Ok(())
}

/// Why a change was refused: the proof, a key the change needs absent (insert)
/// or present (replace, remove) that the proof shows otherwise, or a batch that
/// is empty, too large or names a key twice.
#[cfg_attr(test, derive(Debug, PartialEq))]
pub enum Refusal {
    Refused(Error),
    Absent,
    Present,
    Batch,
}

impl From<Error> for Refusal {
    fn from(error: Error) -> Self {
        Self::Refused(error)
    }
}

/// One update of a batch: `key`'s value becomes `commit`, and `proof` is its
/// proof against the root the batch starts from. The proof is brought up to
/// date in place as the updates before it are made.
pub struct Update<'a> {
    pub key: &'a Key,
    pub proof: &'a mut [u8],
    pub commit: &'a Digest,
}

/// The root after a batch of replacements, all proven against `root`.
///
/// The host proves every update against the root the batch starts from: it
/// cannot prove against the tree the earlier updates leave, since only the
/// device knows their new leaves. So the updates are made one at a time on one
/// `Root`, each held against the root as the ones before left it, and after
/// each one the proofs still to come follow it. A replacement keeps the shape
/// of the tree, so on another key's path only the sibling where the two keys
/// part changes. A proof that does not follow, because the host served a wrong
/// one, is refused when its turn comes. Inserts and removals change the shape
/// and are not batched.
pub fn replace_all(root: &Digest, updates: &mut [Update<'_>]) -> Result<Digest, Refusal> {
    if updates.is_empty() || updates.len() > BATCH_MAX {
        return Err(Refusal::Batch);
    }
    for (i, update) in updates.iter().enumerate() {
        if updates[i + 1..].iter().any(|other| other.key == update.key) {
            return Err(Refusal::Batch);
        }
    }
    let mut root = Root::<Sha256>::trusted(*root);
    for i in 0..updates.len() {
        let (done, rest) = updates.split_at_mut(i + 1);
        let update = &done[i];
        replace_in(&mut root, update.key, update.proof, update.commit)?;
        for other in rest {
            follow_replace(
                update.key,
                update.proof,
                update.commit,
                other.key,
                other.proof,
            )?;
        }
    }
    Ok(*root.digest())
}

/// Brings `other`, a proof for `other_key` held against the root before `key`
/// changed to `commit`, up to date with that change, in place. `proof` is the
/// proof `key` changed under. On `other`'s path only the sibling at the branch
/// where the two keys part changes, to the subtree that now holds `key`'s new
/// leaf. The patched proof proves nothing by itself; it is held against the new
/// root like any other before it is used.
fn follow_replace(
    key: &Key,
    proof: &[u8],
    commit: &Digest,
    other_key: &Key,
    other: &mut [u8],
) -> Result<(), Error> {
    // Equal keys are one entry, which a batch refuses before it gets here.
    let Some(c) = crit_bit(key, other_key) else {
        return Err(Error::OffPath);
    };
    let subtree = parse(proof)?
        .steps()
        .take_while(|step| step.crit_bit > c)
        .fold(leaf_digest::<Key, Sha256>(key, commit), |node, step| {
            parent(key, step, &node)
        });
    let index = parse(other)?.steps().position(|step| step.crit_bit == c);
    if let Some(index) = index {
        let start =
            Leaf::<Key, Sha256>::LEN + index * Step::<Key, Sha256>::LEN + BitPos::<Key>::LEN;
        other[start..start + subtree.len()].copy_from_slice(&subtree);
    }
    // Without a step at `c` the proof is not `other_key`'s path in a tree that
    // holds `key`; it is left as it is and fails when it is held against the
    // root.
    Ok(())
}

fn parent(key: &Key, step: Step<Key, Sha256>, node: &Digest) -> Digest {
    if bit(key, step.crit_bit) {
        branch_digest::<Key, Sha256>(step.crit_bit, &step.sibling, node)
    } else {
        branch_digest::<Key, Sha256>(step.crit_bit, node, &step.sibling)
    }
}

/// Runs `f` on the walk over the tree with `root`, at the entry `current`
/// proves, or before the first entry without one.
fn with_walk<B: AsRef<[u8]>, T>(
    root: &Digest,
    current: Option<B>,
    f: impl FnOnce(&mut Walk<'_, B, Key, Sha256>) -> Result<T, Error>,
) -> Result<T, Error> {
    let mut root = Root::<Sha256>::trusted(*root);
    let mut walk = match current {
        None => root.walk(),
        Some(current) => root.walk_at(Proof::parse(current)?)?,
    };
    f(&mut walk)
}

/// Whether the walk at `current` is over.
pub fn walk_done(root: &Digest, current: Option<&[u8]>) -> Result<bool, Error> {
    with_walk(root, current, |walk| Ok(walk.is_done()))
}

/// The length of the full proof `walk_next` writes for `proof`.
pub fn walk_next_len(root: &Digest, current: Option<&[u8]>, proof: &[u8]) -> Result<usize, Error> {
    let proof = parse(proof)?;
    with_walk(root, current, |walk| Ok(walk.next_len(&proof)))
}

/// Accepts `proof`, full or cut below where it parts from `current`, as the
/// entry after `current` (the first entry without one), and writes its full
/// proof into `buf`, which must be `walk_next_len` bytes. Returns the entry's
/// key and value digest.
pub fn walk_next(
    root: &Digest,
    current: Option<&mut [u8]>,
    proof: &[u8],
    buf: &mut [u8],
) -> Result<(Key, Digest), Error> {
    let proof = parse(proof)?;
    with_walk(root, current, |walk| {
        if buf.len() != walk.next_len(&proof) {
            return Err(Error::Length);
        }
        let entry = walk.next_into(&proof, buf)?;
        Ok((*entry.key(), *entry.digest()))
    })
}

#[cfg(test)]
mod tests {
    use trezor_ward::trie::empty_root;

    use super::*;

    fn key(byte: u8) -> Key {
        let mut key = [0; 32];
        key[0] = byte;
        key
    }

    fn commit(byte: u8) -> Digest {
        [byte; 32]
    }

    /// `leaf` and the steps of `path` (leaf-to-root) as proof bytes.
    fn proof(leaf: &Key, value: &Digest, path: &[(u8, Digest)]) -> Vec<u8> {
        let mut bytes = [leaf.as_slice(), value].concat();
        for (crit_bit, sibling) in path {
            bytes.push(*crit_bit);
            bytes.extend_from_slice(sibling);
        }
        bytes
    }

    fn leaf(k: &Key, c: &Digest) -> Digest {
        leaf_digest::<Key, Sha256>(k, c)
    }

    fn branch(c: u8, left: &Digest, right: &Digest) -> Digest {
        branch_digest::<Key, Sha256>(BitPos::new(c.into()).unwrap(), left, right)
    }

    /// The vectors the hosts' provers are pinned to (`tools/ward_vectors.py`).
    #[test]
    fn shared_vectors() {
        let v: serde_json::Value = serde_json::from_str(include_str!(
            "../../../../../common/tests/fixtures/ward/trie.json"
        ))
        .unwrap();
        let hex32 = |value: &serde_json::Value| -> [u8; 32] {
            hex::decode(value.as_str().unwrap())
                .unwrap()
                .try_into()
                .unwrap()
        };
        let steps = |value: &serde_json::Value| -> Vec<u8> {
            value
                .as_array()
                .unwrap()
                .iter()
                .flat_map(|step| hex::decode(step.as_str().unwrap()).unwrap())
                .collect()
        };
        let root = hex32(&v["root"]);
        let commits: Vec<(Key, Digest)> = v["leaves"]
            .as_array()
            .unwrap()
            .iter()
            .map(|row| {
                let value = hex::decode(row["valueHex"].as_str().unwrap()).unwrap();
                (
                    hex32(&row["entryKeyHex"]),
                    Sha256::digest(&[&[0x03], &value]),
                )
            })
            .collect();
        let commit_of = |key: &Key| commits.iter().find(|(k, _)| k == key).unwrap().1;

        let member = hex32(&v["memberKey"]);
        let p = [
            member.as_slice(),
            &commit_of(&member),
            &steps(&v["memberProof"]),
        ]
        .concat();
        assert_eq!(lookup(&root, &member, &p), Ok(Some(commit_of(&member))));

        let witness = [
            hex::decode(v["witnessKey"].as_str().unwrap()).unwrap(),
            hex::decode(v["witnessCommit"].as_str().unwrap()).unwrap(),
            steps(&v["nonMemberProof"]),
        ]
        .concat();
        assert_eq!(lookup(&root, &hex32(&v["absentKey"]), &witness), Ok(None));

        let mut current: Option<Vec<u8>> = None;
        for entry in v["walk"].as_array().unwrap() {
            let key = hex32(&entry["entryKeyHex"]);
            let p = [key.as_slice(), &commit_of(&key), &steps(&entry["proof"])].concat();
            let mut buf = vec![0; walk_next_len(&root, current.as_deref(), &p).unwrap()];
            let got = walk_next(&root, current.as_deref_mut(), &p, &mut buf).unwrap();
            assert_eq!(got, (key, commit_of(&key)));
            current = Some(buf);
        }
        assert_eq!(walk_done(&root, current.as_deref()), Ok(true));
    }

    #[test]
    fn empty_root_is_the_firmware_constant() {
        // sha256(0x02), service.EMPTY_ROOT_HASH
        assert_eq!(
            hex::encode(empty_root::<Sha256>()),
            "dbc1b4c900ffe48d575b5da5c638040125f65db0fe3e24494b76ea986457d986"
        );
    }

    /// Three keys, 0x00.., 0x40.. and 0x80..: the root splits on bit 0, its
    /// left child on bit 1.
    struct Three {
        keys: [Key; 3],
        commits: [Digest; 3],
    }

    impl Three {
        fn new() -> Self {
            Self {
                keys: [key(0x00), key(0x40), key(0x80)],
                commits: [commit(1), commit(2), commit(3)],
            }
        }

        fn root(&self) -> Digest {
            let [a, b, c] = self.leaves();
            branch(0, &branch(1, &a, &b), &c)
        }

        fn leaves(&self) -> [Digest; 3] {
            [0, 1, 2].map(|i| leaf(&self.keys[i], &self.commits[i]))
        }

        fn proof(&self, i: usize) -> Vec<u8> {
            let [a, b, c] = self.leaves();
            let path: Vec<(u8, Digest)> = match i {
                0 => vec![(1, b), (0, c)],
                1 => vec![(1, a), (0, c)],
                _ => vec![(0, branch(1, &a, &b))],
            };
            proof(&self.keys[i], &self.commits[i], &path)
        }
    }

    #[test]
    fn lookup_set_and_remove() {
        let t = Three::new();
        let root = t.root();
        assert_eq!(
            lookup(&root, &t.keys[1], &t.proof(1)),
            Ok(Some(t.commits[1]))
        );
        // the proof of 0x40.. shows 0x60.. absent, and where it would go
        let absent = key(0x60);
        assert_eq!(lookup(&root, &absent, &t.proof(1)), Ok(None));
        assert!(remove(&root, &absent, &t.proof(1)) == Err(Refusal::Absent));

        let mut t2 = Three::new();
        t2.commits[1] = commit(9);
        // an insert is refused where the key is present
        assert!(insert(&root, &t.keys[1], &t.proof(1), &commit(9)) == Err(Refusal::Present));
        assert_eq!(
            replace(&root, &t.keys[1], &t.proof(1), &commit(9)),
            Ok(t2.root())
        );

        let [a, _, c] = t.leaves();
        assert_eq!(
            remove(&root, &t.keys[1], &t.proof(1)),
            Ok(branch(0, &a, &c))
        );
        // a proof against another root is refused
        assert_eq!(
            lookup(&t2.root(), &t.keys[1], &t.proof(1)),
            Err(Error::RootMismatch)
        );
    }

    fn batch(t: &Three, order: &[usize], commits: &[Digest]) -> Result<Digest, Refusal> {
        let mut proofs: Vec<Vec<u8>> = order.iter().map(|&i| t.proof(i)).collect();
        let mut updates: Vec<Update> = order
            .iter()
            .zip(proofs.iter_mut())
            .zip(commits)
            .map(|((&i, proof), commit)| Update {
                key: &t.keys[i],
                proof,
                commit,
            })
            .collect();
        replace_all(&t.root(), &mut updates)
    }

    #[test]
    fn a_batch_is_every_update_in_any_order() {
        let t = Three::new();
        let new = [commit(8), commit(9), commit(7)];
        let mut expected = Three::new();
        expected.commits = new;
        for order in [
            [0, 1, 2],
            [0, 2, 1],
            [1, 0, 2],
            [1, 2, 0],
            [2, 0, 1],
            [2, 1, 0],
        ] {
            let commits: Vec<Digest> = order.iter().map(|&i| new[i]).collect();
            assert_eq!(batch(&t, &order, &commits), Ok(expected.root()));
        }
        // a part of the keys, and a single update
        expected = Three::new();
        expected.commits[2] = commit(7);
        expected.commits[0] = commit(8);
        assert_eq!(
            batch(&t, &[2, 0], &[commit(7), commit(8)]),
            Ok(expected.root())
        );
        let mut one = Three::new();
        one.commits[1] = commit(9);
        assert_eq!(batch(&t, &[1], &[commit(9)]), Ok(one.root()));
    }

    #[test]
    fn a_batch_refuses_a_wrong_proof_or_shape() {
        let t = Three::new();
        let root = t.root();
        let c = [commit(8), commit(9)];

        // a forged sibling in the second proof, one the first update does not
        // rewrite: 0x00.. and 0x40.. part at bit 1, the forged step is at bit 0
        let mut p0 = t.proof(0);
        let mut p1 = t.proof(1);
        let last = p1.len() - 1;
        p1[last] ^= 1;
        let mut updates = [
            Update {
                key: &t.keys[0],
                proof: &mut p0,
                commit: &c[0],
            },
            Update {
                key: &t.keys[1],
                proof: &mut p1,
                commit: &c[1],
            },
        ];
        assert_eq!(
            replace_all(&root, &mut updates),
            Err(Refusal::Refused(Error::RootMismatch))
        );

        // an absent key, its proof ending at another leaf
        let absent = key(0x60);
        let mut pa = t.proof(1);
        let mut updates = [Update {
            key: &absent,
            proof: &mut pa,
            commit: &c[0],
        }];
        assert_eq!(replace_all(&root, &mut updates), Err(Refusal::Absent));

        // a key twice, an empty batch, a batch beyond the queue
        let (mut pa, mut pb) = (t.proof(1), t.proof(1));
        let mut updates = [
            Update {
                key: &t.keys[1],
                proof: &mut pa,
                commit: &c[0],
            },
            Update {
                key: &t.keys[1],
                proof: &mut pb,
                commit: &c[1],
            },
        ];
        assert_eq!(replace_all(&root, &mut updates), Err(Refusal::Batch));
        assert_eq!(replace_all(&root, &mut []), Err(Refusal::Batch));
        let mut proofs: Vec<Vec<u8>> = (0..=BATCH_MAX).map(|_| t.proof(0)).collect();
        let keys: Vec<Key> = (0..=BATCH_MAX).map(|i| key(i as u8)).collect();
        let mut updates: Vec<Update> = keys
            .iter()
            .zip(proofs.iter_mut())
            .map(|(key, proof)| Update {
                key,
                proof,
                commit: &c[0],
            })
            .collect();
        assert_eq!(replace_all(&root, &mut updates), Err(Refusal::Batch));
    }

    #[test]
    fn walk_in_key_order() {
        let t = Three::new();
        let root = t.root();
        let mut current: Option<Vec<u8>> = None;
        for i in 0..3 {
            assert_eq!(walk_done(&root, current.as_deref()), Ok(false));
            let next = t.proof(i);
            let len = walk_next_len(&root, current.as_deref(), &next).unwrap();
            let mut buf = vec![0; len];
            let got = walk_next(&root, current.as_deref_mut(), &next, &mut buf).unwrap();
            assert_eq!(got, (t.keys[i], t.commits[i]));
            current = Some(buf);
        }
        assert_eq!(walk_done(&root, current.as_deref()), Ok(true));

        // skipping an entry is refused
        let first = t.proof(0);
        let mut buf = vec![0; walk_next_len(&root, None, &first).unwrap()];
        walk_next(&root, None, &first, &mut buf).unwrap();
        let skip = t.proof(2);
        let mut buf2 = vec![0; walk_next_len(&root, Some(buf.as_slice()), &skip).unwrap()];
        assert_eq!(
            walk_next(&root, Some(buf.as_mut_slice()), &skip, &mut buf2),
            Err(Error::OutOfOrder)
        );
    }
}
