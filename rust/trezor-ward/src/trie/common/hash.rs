use super::array::ByteArray;
use super::node::TAG_VALUE;

/// A hash function.
///
/// The tree hashes at most four pieces at a time, a tag, a crit bit and two digests, so the
/// interface is one-shot over parts and never assembles a preimage. An implementation does not
/// need to be constructible: `Self` is only a type-level choice.
pub trait HashFn {
    /// The digest type: a byte array of the function's width.
    type Output: ByteArray;

    /// The digest of the concatenation of `parts`.
    fn digest(parts: &[&[u8]]) -> Self::Output;
}

/// What the tree needs from a value: its digest under `H`, the fixed-width operand that
/// enters the leaf.
///
/// This is the shape of `core::hash::Hash`, with the hash function as a trait parameter
/// rather than a method parameter, because a value may be hashable under some functions only:
/// a stored digest is, under the hashes of its width. The standard trait itself cannot serve,
/// since its byte encoding is unspecified and platform-dependent, and the two sides of a proof
/// must agree on every byte.
///
/// Unlike a key, a value need not be a byte string. The tree routes on a key's bits, but of a
/// value it only ever sees the digest, which never occupies a node position, so no choice of
/// digest can be confused with a node.
///
/// Anything that is `AsRef<[u8]>` is hashable already, as `H(0x03 ‖ bytes)`; the tag keeps
/// this default in the same domain-separated namespace as the node encodings. The default is
/// safe for every byte string, including one that is a digest already, at the cost of one
/// extra hash. A type that wants to skip it, or has its own commitment scheme, implements the
/// trait itself; coherence then requires that it is not `AsRef<[u8]>`, so a digest used as a
/// value verbatim needs a newtype:
///
/// ```
/// use trezor_ward::trie::{HashFn, Hashable};
///
/// struct Digested<D>(D);
///
/// impl<H: HashFn> Hashable<H> for Digested<H::Output> {
///     fn digest(&self) -> H::Output {
///         self.0
///     }
/// }
/// ```
pub trait Hashable<H: HashFn> {
    /// The digest the tree commits to.
    fn digest(&self) -> H::Output;
}

impl<H: HashFn, T: AsRef<[u8]> + ?Sized> Hashable<H> for T {
    fn digest(&self) -> H::Output {
        H::digest(&[&[TAG_VALUE], self.as_ref()])
    }
}

/// SHA-256, from the `sha2` crate.
#[cfg(feature = "sha2")]
#[derive(Clone, Copy)]
#[cfg_attr(feature = "debug", derive(Debug))]
pub struct Sha256;

#[cfg(feature = "sha2")]
impl HashFn for Sha256 {
    type Output = [u8; 32];

    fn digest(parts: &[&[u8]]) -> Self::Output {
        use sha2::Digest as _;

        let mut hasher = sha2::Sha256::new();
        for part in parts {
            hasher.update(part);
        }
        hasher.finalize().into()
    }
}
