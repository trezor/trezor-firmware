//! The proof format: the record of one lookup, as one byte string.
//!
//! ```text
//! proof = terminal_key ‖ terminal_digest ‖ ( crit_bit ‖ sibling )*
//!         zero bytes for the empty map
//! ```
//!
//! A leaf is [`Leaf::LEN`] bytes and a step [`Step::LEN`], so every field sits at a fixed
//! offset. The steps are listed leaf-to-root: the first is the branch directly above the terminal
//! leaf. Read root-to-leaf, their crit bits strictly increase and stay below the key width;
//! that is the shape of a real path, and [`Proof::parse`] refuses anything else before any
//! field is used. A parsed proof is therefore always well formed, and holding it against a
//! root and a key only has to check that it is the key's own path and that it folds to the
//! root.
//!
//! The in-memory form is the wire form: a proof borrows or owns its bytes and reads each
//! field where it is needed, so the verifier needs no buffer of its own and the prover
//! produces the wire form directly.

#[cfg(feature = "debug")]
use core::fmt;
use core::marker::PhantomData;
use core::slice::ChunksExact;

use super::array::ByteArray;
use super::error::Error;
use super::hash::HashFn;
use super::key::{BitPos, Key, key_bits, key_len};

/// One step of a path: the branch's crit bit and the digest of the child not taken.
pub struct Step<H: HashFn> {
    /// The bit the branch splits on.
    pub crit_bit: BitPos,
    /// The digest of the child the path does not take.
    pub sibling: H::Output,
}

impl<H: HashFn> Step<H> {
    /// Wire width: a position and a digest.
    pub const LEN: usize = BitPos::LEN + H::Output::LEN;
}

/// A step from exactly [`LEN`](Step::LEN) bytes; any other length is [`Error::Length`].
impl<H: HashFn> TryFrom<&[u8]> for Step<H> {
    type Error = Error;

    fn try_from(bytes: &[u8]) -> Result<Self, Error> {
        if bytes.len() != Self::LEN {
            return Err(Error::Length);
        }
        // The length was checked, so both pieces are exactly their widths.
        let (crit_bit, sibling) = bytes.split_at(BitPos::LEN);
        Ok(Self {
            crit_bit: BitPos::from_bytes(crit_bit.try_into().unwrap()),
            sibling: sibling.try_into().unwrap(),
        })
    }
}

/// The leaf a lookup ended at: its key and its value digest.
pub struct Leaf<K, H: HashFn> {
    /// The leaf's key.
    pub key: K,
    /// The digest of the leaf's value.
    pub value: H::Output,
}

impl<K: Key, H: HashFn> Leaf<K, H> {
    /// Wire width: a key and a digest.
    pub const LEN: usize = key_len::<K>() + H::Output::LEN;
}

/// A leaf from exactly [`LEN`](Leaf::LEN) bytes; any other length is [`Error::Length`].
impl<K: Key, H: HashFn> TryFrom<&[u8]> for Leaf<K, H> {
    type Error = Error;

    fn try_from(bytes: &[u8]) -> Result<Self, Error> {
        if bytes.len() != Self::LEN {
            return Err(Error::Length);
        }
        // The length was checked, so both pieces are exactly their widths.
        let (key, value) = bytes.split_at(key_len::<K>());
        Ok(Self {
            key: K::from_bytes(key.try_into().unwrap()),
            value: value.try_into().unwrap(),
        })
    }
}

/// The record of one lookup: the leaf it ended at and the path it took, leaf-to-root.
///
/// `B` is the storage of the bytes: `&[u8]` borrowed from a message on the verifier side,
/// `Vec<u8>` as produced by the prover. [`parse`](Self::parse) is the only way to obtain a
/// proof from untrusted bytes.
pub struct Proof<B, K, H> {
    bytes: B,
    /// No `K` or `H` is stored, but they fix the layout the bytes were parsed for.
    _marker: PhantomData<(K, H)>,
}

impl<B: AsRef<[u8]>, K: Key, H: HashFn> Proof<B, K, H> {
    /// A proof from its wire form. Refuses bytes that do not fit the layout
    /// ([`Error::Length`]) and paths that no tree has ([`Error::Shape`]).
    pub fn parse(bytes: B) -> Result<Self, Error> {
        const {
            assert!(
                key_bits::<K>() <= BitPos::MAX.index() + 1,
                "a key has more bits than a BitPos can address"
            )
        };
        let len = bytes.as_ref().len();
        if len != 0
            && (len < Leaf::<K, H>::LEN
                || !(len - Leaf::<K, H>::LEN).is_multiple_of(Step::<H>::LEN))
        {
            return Err(Error::Length);
        }
        let proof = Self {
            bytes,
            _marker: PhantomData,
        };
        proof.check_shape()?;
        Ok(proof)
    }

    /// Root first, the crit bits strictly increase and stay within the key. This also bounds
    /// the work a proof can demand: at most `key_bits::<K>()` steps, however long the bytes are.
    fn check_shape(&self) -> Result<(), Error> {
        let mut prev = None;
        for step in self.steps().rev() {
            if step.crit_bit.index() >= key_bits::<K>() || prev.is_some_and(|p| step.crit_bit <= p)
            {
                return Err(Error::Shape);
            }
            prev = Some(step.crit_bit);
        }
        Ok(())
    }

    /// The wire form.
    pub fn as_bytes(&self) -> &[u8] {
        self.bytes.as_ref()
    }

    /// The storage of the wire form.
    pub fn into_bytes(self) -> B {
        self.bytes
    }

    /// Whether this is the proof of the empty map.
    pub fn is_empty(&self) -> bool {
        self.as_bytes().is_empty()
    }

    /// The leaf the lookup ended at; `None` for the empty map.
    pub fn leaf(&self) -> Option<Leaf<K, H>> {
        let bytes = self.as_bytes();
        // `parse` checked the length, so a non-empty proof holds a whole leaf.
        (!bytes.is_empty()).then(|| Leaf::try_from(&bytes[..Leaf::<K, H>::LEN]).unwrap())
    }

    /// A proof borrowing this one's bytes. Already validated, so there is nothing to parse.
    pub(crate) fn view(&self) -> Proof<&[u8], K, H> {
        Proof {
            bytes: self.as_bytes(),
            _marker: PhantomData,
        }
    }

    /// The steps, leaf-to-root.
    pub fn steps(&self) -> Steps<'_, H> {
        let bytes = self.as_bytes();
        Steps::new(if bytes.is_empty() {
            bytes
        } else {
            &bytes[Leaf::<K, H>::LEN..]
        })
    }

    /// The wire width of a non-empty proof with `steps` steps.
    pub(crate) const fn len_with(steps: usize) -> usize {
        Leaf::<K, H>::LEN + steps * Step::<H>::LEN
    }

    /// The part of the path below the branch at `c`: the leaf and the steps whose crit bit is
    /// above `c`. The steps are leaf-to-root, so this is a prefix of the bytes, and it is what
    /// a host sends for the entry after one that parts from it at `c`, since a walk holds the
    /// rest (see [`Walk`](crate::trie::Walk)). The empty proof is its own part.
    pub fn below(&self, c: BitPos) -> Proof<&[u8], K, H> {
        let bytes = self.as_bytes();
        if bytes.is_empty() {
            return self.view();
        }
        let steps = self.steps().take_while(|step| step.crit_bit > c).count();
        // The retained steps are the deepest ones, so their crit bits still strictly
        // increase root-to-leaf: a prefix of a well-formed proof is well formed.
        Proof {
            bytes: &bytes[..Self::len_with(steps)],
            _marker: PhantomData,
        }
    }
}

/// Writes a proof, `leaf` then `steps` leaf-to-root, into `out`, which must be exactly
/// [`Proof::len_with`] of the number of steps; the callers, the prover's `build` and the
/// walk, size it so. The bytes are not parsed here, the caller does that, so that a `Proof`
/// value is well formed whatever its origin.
pub(crate) fn write_into<K: Key, H: HashFn>(
    out: &mut [u8],
    leaf: &Leaf<K, H>,
    steps: impl IntoIterator<Item = Step<H>>,
) {
    fn put(out: &mut &mut [u8], bytes: &[u8]) {
        let (head, tail) = core::mem::take(out).split_at_mut(bytes.len());
        head.copy_from_slice(bytes);
        *out = tail;
    }

    let mut out = out;
    put(&mut out, leaf.key.as_bytes().as_ref());
    put(&mut out, leaf.value.as_ref());
    for step in steps {
        put(&mut out, &step.crit_bit.to_bytes());
        put(&mut out, step.sibling.as_ref());
    }
    assert!(out.is_empty(), "the proof is shorter than the buffer");
}

#[cfg(feature = "use_std")]
impl<K: Key, H: HashFn> Proof<Vec<u8>, K, H> {
    /// The proof of the empty map.
    pub(crate) fn empty() -> Self {
        Self {
            bytes: Vec::new(),
            _marker: PhantomData,
        }
    }

    /// A proof from its parts, `steps` leaf-to-root, checked like bytes from anywhere else:
    /// a path no tree has is [`Error::Shape`], not the caller's word.
    pub(crate) fn build(
        leaf: &Leaf<K, H>,
        steps: impl IntoIterator<Item = Step<H>, IntoIter: ExactSizeIterator>,
    ) -> Result<Self, Error> {
        let steps = steps.into_iter();
        let mut bytes = vec![0; Self::len_with(steps.len())];
        write_into(&mut bytes, leaf, steps);
        Self::parse(bytes)
    }
}

/// The steps of a proof, leaf-to-root; reversed, root-to-leaf.
pub struct Steps<'a, H> {
    chunks: ChunksExact<'a, u8>,
    _marker: PhantomData<H>,
}

impl<'a, H: HashFn> Steps<'a, H> {
    /// The steps encoded in `bytes`: a whole number of them.
    fn new(bytes: &'a [u8]) -> Self {
        Self {
            chunks: bytes.chunks_exact(Step::<H>::LEN),
            _marker: PhantomData,
        }
    }

    fn step(chunk: &[u8]) -> Step<H> {
        // `chunks_exact` yields whole steps only.
        Step::try_from(chunk).unwrap()
    }
}

impl<H: HashFn> Iterator for Steps<'_, H> {
    type Item = Step<H>;

    fn next(&mut self) -> Option<Self::Item> {
        self.chunks.next().map(Self::step)
    }

    fn size_hint(&self) -> (usize, Option<usize>) {
        self.chunks.size_hint()
    }

    /// Slices the chunks, so skipping steps parses none of them.
    fn nth(&mut self, n: usize) -> Option<Self::Item> {
        self.chunks.nth(n).map(Self::step)
    }
}

impl<H: HashFn> DoubleEndedIterator for Steps<'_, H> {
    fn next_back(&mut self) -> Option<Self::Item> {
        self.chunks.next_back().map(Self::step)
    }

    fn nth_back(&mut self, n: usize) -> Option<Self::Item> {
        self.chunks.nth_back(n).map(Self::step)
    }
}

impl<H: HashFn> ExactSizeIterator for Steps<'_, H> {}

// Implemented by hand. A derive bounds the type parameters, not the fields: it would make
// `Step<H>` `Clone` only for `H: Clone`, `Debug` only for `H: Debug`, and so on, although `H`
// is a marker that merely names the hash function and the fields are a `BitPos` and an array.
// The same goes for the `K` and `H` behind `Proof`'s `PhantomData`. This is the "perfect
// derive" problem, https://github.com/rust-lang/rust/issues/26925; the alternatives are a
// derive crate with bound control, or `Copy + Eq + Debug` as supertraits of `HashFn` and
// `Key`, which would make marker types promise things they do not mean. `Proof` additionally
// compares across storage types, which no derive gives.

impl<H: HashFn> Clone for Step<H> {
    fn clone(&self) -> Self {
        *self
    }
}

impl<H: HashFn> Copy for Step<H> {}

impl<H: HashFn> PartialEq for Step<H> {
    fn eq(&self, other: &Self) -> bool {
        self.crit_bit == other.crit_bit && self.sibling == other.sibling
    }
}

impl<H: HashFn> Eq for Step<H> {}

#[cfg(feature = "debug")]
impl<H: HashFn> fmt::Debug for Step<H> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Step")
            .field("crit_bit", &self.crit_bit)
            .field("sibling", &self.sibling.as_ref())
            .finish()
    }
}

impl<K: Key, H: HashFn> Clone for Leaf<K, H> {
    fn clone(&self) -> Self {
        *self
    }
}

impl<K: Key, H: HashFn> Copy for Leaf<K, H> {}

impl<K: Key, H: HashFn> PartialEq for Leaf<K, H> {
    fn eq(&self, other: &Self) -> bool {
        self.key == other.key && self.value == other.value
    }
}

impl<K: Key, H: HashFn> Eq for Leaf<K, H> {}

#[cfg(feature = "debug")]
impl<K: Key, H: HashFn> fmt::Debug for Leaf<K, H> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Leaf")
            .field("key", &self.key.as_bytes().as_ref())
            .field("value", &self.value.as_ref())
            .finish()
    }
}

impl<B: Clone, K, H> Clone for Proof<B, K, H> {
    fn clone(&self) -> Self {
        Self {
            bytes: self.bytes.clone(),
            _marker: PhantomData,
        }
    }
}

/// Proofs are equal when their wire forms are, whatever their storage.
impl<B: AsRef<[u8]>, B2: AsRef<[u8]>, K, H> PartialEq<Proof<B2, K, H>> for Proof<B, K, H> {
    fn eq(&self, other: &Proof<B2, K, H>) -> bool {
        self.bytes.as_ref() == other.bytes.as_ref()
    }
}

impl<B: AsRef<[u8]>, K, H> Eq for Proof<B, K, H> {}

#[cfg(feature = "debug")]
impl<B: AsRef<[u8]>, K, H> fmt::Debug for Proof<B, K, H> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Proof")
            .field("bytes", &self.bytes.as_ref())
            .finish()
    }
}

#[cfg(test)]
mod tests {
    use super::super::hash::Sha256;
    use super::*;

    type P<B> = Proof<B, [u8; 1], Sha256>;

    const LEAF: usize = 1 + 32;
    const STEP: usize = 2 + 32;

    /// A leaf for key `key`, then `bits` as steps leaf-to-root, all digests zero.
    fn bytes(key: u8, bits: &[u16]) -> Vec<u8> {
        let mut out = vec![0; LEAF];
        out[0] = key;
        for bit in bits {
            out.extend_from_slice(&bit.to_be_bytes());
            out.extend_from_slice(&[0; 32]);
        }
        out
    }

    #[test]
    fn layout_constants() {
        assert_eq!(Leaf::<[u8; 1], Sha256>::LEN, LEAF);
        assert_eq!(Step::<Sha256>::LEN, STEP);
        assert_eq!(
            Leaf::<[u8; 1], Sha256>::try_from(&[0; LEAF - 1][..]).unwrap_err(),
            Error::Length
        );
        assert_eq!(
            Step::<Sha256>::try_from(&[0; STEP + 1][..]).unwrap_err(),
            Error::Length
        );
    }

    #[test]
    fn the_empty_proof() {
        let proof = P::parse(&[][..]).unwrap();
        assert!(proof.is_empty());
        assert_eq!(proof.leaf(), None);
        assert_eq!(proof.steps().len(), 0);
        assert_eq!(proof, P::parse(Vec::new()).unwrap());
    }

    #[test]
    fn lengths_are_checked_before_anything_is_read() {
        for len in [1, LEAF - 1, LEAF + 1, LEAF + STEP - 1, LEAF + STEP + 1] {
            assert_eq!(P::parse(vec![0; len]).unwrap_err(), Error::Length);
        }
        for len in [LEAF, LEAF + STEP, LEAF + 2 * STEP] {
            assert!(P::parse(vec![0; len]).is_ok() || len > LEAF);
        }
        assert!(P::parse(bytes(0, &[])).is_ok());
        assert!(P::parse(bytes(0, &[0])).is_ok());
        assert!(P::parse(bytes(0, &[1, 0])).is_ok());
    }

    #[test]
    fn the_shape_is_a_root_to_leaf_path() {
        assert!(P::parse(bytes(0, &[7, 4, 1, 0])).is_ok());
        for bits in [
            &[0, 1][..],    // decreasing root-to-leaf: reordered
            &[1, 1][..],    // the same bit twice
            &[8][..],       // beyond a one-byte key
            &[0, 8, 7][..], // out of range in the middle
        ] {
            assert_eq!(P::parse(bytes(0, bits)).unwrap_err(), Error::Shape);
        }
    }

    #[test]
    fn fields_are_read_where_the_layout_puts_them() {
        let mut raw = bytes(0b0100_0000, &[4, 1, 0]);
        raw[1..LEAF].copy_from_slice(&[0xaa; 32]);
        raw[LEAF + 2..LEAF + STEP].copy_from_slice(&[0xbb; 32]);
        let proof = P::parse(raw.as_slice()).unwrap();

        assert_eq!(
            proof.leaf(),
            Some(Leaf {
                key: [0b0100_0000],
                value: [0xaa; 32]
            })
        );
        let steps: Vec<_> = proof.steps().collect();
        assert_eq!(steps.len(), 3);
        assert_eq!(
            steps[0],
            Step {
                crit_bit: BitPos::new(4),
                sibling: [0xbb; 32]
            }
        );
        assert_eq!(steps[1].crit_bit, BitPos::new(1));
        assert_eq!(steps[2].crit_bit, BitPos::new(0));
        let root_first: Vec<BitPos> = proof.steps().rev().map(|s| s.crit_bit).collect();
        assert_eq!(root_first, [0, 1, 4].map(BitPos::new));
        assert_eq!(proof.steps().nth(1), Some(steps[1]));
        assert_eq!(proof.steps().nth_back(1), Some(steps[1]));
    }

    #[test]
    fn build_and_parse_round_trip() {
        let leaf = Leaf {
            key: [0b0000_1111],
            value: [7; 32],
        };
        let steps = [
            Step {
                crit_bit: BitPos::new(4),
                sibling: [1; 32],
            },
            Step {
                crit_bit: BitPos::new(0),
                sibling: [2; 32],
            },
        ];
        let built = P::build(&leaf, steps).unwrap();
        assert_eq!(
            P::build(&leaf, [steps[1], steps[0]]).unwrap_err(),
            Error::Shape
        );
        let parsed = P::parse(built.as_bytes()).unwrap();
        assert_eq!(parsed, built);
        assert_eq!(parsed.leaf(), Some(leaf));
        assert!(parsed.steps().eq(steps));
        assert_eq!(P::empty(), P::parse(Vec::new()).unwrap());
    }

    #[test]
    fn below_is_a_prefix_of_the_steps() {
        let raw = bytes(0b0000_0000, &[7, 4, 1, 0]);
        let proof = P::parse(raw.as_slice()).unwrap();
        let steps = |p: &Proof<&[u8], [u8; 1], Sha256>| -> Vec<usize> {
            p.steps().map(|s| s.crit_bit.index()).collect()
        };
        // Below the branch at 1: the steps at 7 and 4, which are deeper in the tree.
        let below = proof.below(BitPos::new(1));
        assert_eq!(steps(&below), [7, 4]);
        assert_eq!(below.as_bytes(), &raw[..LEAF + 2 * STEP]);
        assert_eq!(below.leaf(), proof.leaf());
        // At a bit no branch tests, the cut falls between the branches around it.
        assert_eq!(steps(&proof.below(BitPos::new(5))), [7]);
        // Below the deepest branch there is only the leaf; above the root, the whole path.
        assert_eq!(steps(&proof.below(BitPos::new(7))), []);
        assert_eq!(proof.below(BitPos::new(7)).as_bytes(), &raw[..LEAF]);
        assert_eq!(proof.below(BitPos::MAX).as_bytes(), &raw[..LEAF]);
        assert_eq!(steps(&proof.below(BitPos::new(0))), [7, 4, 1]);
        assert_eq!(
            P::parse(&[][..]).unwrap().below(BitPos::new(0)),
            P::parse(&[][..]).unwrap()
        );
        assert_eq!(P::<&[u8]>::len_with(4), raw.len());
    }

    #[test]
    fn storage_does_not_matter() {
        let raw = bytes(0b0000_1111, &[4, 0]);
        let borrowed = P::parse(raw.as_slice()).unwrap();
        let owned = P::parse(raw.clone()).unwrap();
        assert_eq!(borrowed, owned);
        assert_eq!(owned.view(), borrowed);
        assert_eq!(owned.clone().into_bytes(), raw);
        assert_eq!(borrowed.as_bytes(), owned.as_bytes());
    }
}
