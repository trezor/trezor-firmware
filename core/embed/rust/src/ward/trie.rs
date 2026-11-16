//! The WARD trie on the device: `trezor_ward`'s verifier over the firmware's
//! SHA-256, with 32-byte entry keys. The device holds only the root; every root
//! it derives comes from a proof that `Proof::verify` (or a `Walk`) has held
//! against a root it trusts.

use crypto::sha256::{Sha256 as Sha256Hasher, Sha256Ctx};
use trezor_ward::trie::{
    bit, branch_digest, crit_bit, leaf_digest, BitPos, Entry, Error, HashFn, Leaf, Proof, Step,
    Walk,
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
    Ok(match parse(proof)?.verify(root, key)? {
        Entry::Occupied(entry) => Some(*entry.digest()),
        Entry::Vacant(_) => None,
    })
}

/// The root after inserting `commit` under `key`, which must be absent.
pub fn insert(root: &Digest, key: &Key, proof: &[u8], commit: &Digest) -> Result<Digest, Refusal> {
    match parse(proof)?.verify(root, key)? {
        Entry::Vacant(entry) => Ok(entry.insert(&Committed(commit))),
        Entry::Occupied(_) => Err(Refusal::Present),
    }
}

/// The root after replacing the value of `key`, which must be present.
pub fn replace(root: &Digest, key: &Key, proof: &[u8], commit: &Digest) -> Result<Digest, Refusal> {
    match parse(proof)?.verify(root, key)? {
        Entry::Occupied(entry) => Ok(entry.replace(&Committed(commit))),
        Entry::Vacant(_) => Err(Refusal::Absent),
    }
}

/// The root after removing `key`, which must be present.
pub fn remove(root: &Digest, key: &Key, proof: &[u8]) -> Result<Digest, Refusal> {
    match parse(proof)?.verify(root, key)? {
        Entry::Occupied(entry) => Ok(entry.remove()),
        Entry::Vacant(_) => Err(Refusal::Absent),
    }
}

/// Why a change was refused: the proof, or a key the change needs absent
/// (insert) or present (replace, remove) that the proof shows otherwise.
#[cfg_attr(test, derive(Debug, PartialEq))]
pub enum Refusal {
    Refused(Error),
    Absent,
    Present,
}

impl From<Error> for Refusal {
    fn from(error: Error) -> Self {
        Self::Refused(error)
    }
}

/// Brings `other`, a proof for `other_key` held against the root before `key`
/// changed to `commit`, up to date with that change, in place. `proof` is the
/// proof `key` changed under. Only replacements are followed: the shape of the
/// tree stays, and on `other`'s path only the sibling at the branch where the
/// two keys part changes, to the subtree that now holds `key`'s new leaf. The
/// patched proof proves nothing by itself; it is held against the new root like
/// any other before it is used.
pub fn follow_replace(
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

/// The walk over the tree with `root`, at the entry `current` proves, or before
/// the first entry without one.
fn walk_at<B: AsRef<[u8]>>(
    root: &Digest,
    current: Option<B>,
) -> Result<Walk<B, Key, Sha256>, Error> {
    match current {
        None => Ok(Walk::new(*root)),
        Some(current) => Walk::at(*root, Proof::parse(current)?),
    }
}

/// Whether the walk at `current` is over.
pub fn walk_done(root: &Digest, current: Option<&[u8]>) -> Result<bool, Error> {
    Ok(walk_at(root, current)?.is_done())
}

/// The length of the full proof `walk_next` writes for `proof`.
pub fn walk_next_len(root: &Digest, current: Option<&[u8]>, proof: &[u8]) -> Result<usize, Error> {
    Ok(walk_at(root, current)?.next_len(&parse(proof)?))
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
    let mut walk = walk_at(root, current)?;
    let proof = parse(proof)?;
    if buf.len() != walk.next_len(&proof) {
        return Err(Error::Length);
    }
    let entry = walk.next_into(&proof, buf)?;
    Ok((*entry.key(), *entry.digest()))
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

    #[test]
    fn a_followed_proof_holds_against_the_new_root() {
        let t = Three::new();
        let root = t.root();
        let (mut p0, p1, mut p2) = (t.proof(0), t.proof(1), t.proof(2));

        // 0x40.. changes; the proofs of 0x00.. and 0x80.. follow it
        let new_root = replace(&root, &t.keys[1], &p1, &commit(9)).unwrap();
        for (other_key, other) in [(&t.keys[0], &mut p0), (&t.keys[2], &mut p2)] {
            follow_replace(&t.keys[1], &p1, &commit(9), other_key, other).unwrap();
        }
        // and 0x00.. changes next, against the new root
        let newer = replace(&new_root, &t.keys[0], &p0, &commit(8)).unwrap();
        follow_replace(&t.keys[0], &p0, &commit(8), &t.keys[2], &mut p2).unwrap();
        let last = replace(&newer, &t.keys[2], &p2, &commit(7)).unwrap();

        let mut expected = Three::new();
        expected.commits = [commit(8), commit(9), commit(7)];
        assert_eq!(last, expected.root());

        // an unfollowed proof no longer holds
        assert_eq!(
            replace(&new_root, &t.keys[2], &t.proof(2), &commit(7)),
            Err(Refusal::Refused(Error::RootMismatch))
        );
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
