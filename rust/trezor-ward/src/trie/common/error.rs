/// Why a proof was refused.
///
/// `Length` and `Shape` are raised by [`Proof::parse`](super::Proof::parse): the bytes are not
/// a proof at all, a malformed message. The rest are raised when a well-formed proof is held
/// against a root, by [`Proof::verify`](super::Proof::verify) or by a walk: a claim that does
/// not hold.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Error {
    /// The bytes do not fit the proof layout: neither empty, nor a terminal leaf followed by
    /// whole steps.
    Length,
    /// The crit bits, read root-to-leaf, do not strictly increase, or one of them lies beyond
    /// the key width.
    Shape,
    /// The terminal key disagrees with the queried key at a step's crit bit, so the path is
    /// not the queried key's lookup path.
    OffPath,
    /// The fold does not reach the given root.
    RootMismatch,
    /// The claimed value does not hash to the digest the proof commits to.
    ValueMismatch,
    /// The proof holds against the root, but it is not the entry the walk expects: an entry
    /// was skipped, repeated or reordered, the walk did not start at the first entry, or it
    /// is over.
    OutOfOrder,
}

impl core::fmt::Display for Error {
    fn fmt(&self, f: &mut core::fmt::Formatter<'_>) -> core::fmt::Result {
        f.write_str(match self {
            Self::Length => "proof has an invalid length",
            Self::Shape => "proof is not a root-to-leaf path",
            Self::OffPath => "proof is not the key's lookup path",
            Self::RootMismatch => "proof does not fold to the root",
            Self::ValueMismatch => "value does not match the proof",
            Self::OutOfOrder => "proof is not of the next entry in key order",
        })
    }
}

impl core::error::Error for Error {}
