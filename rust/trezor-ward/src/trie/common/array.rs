//! The one place where "fixed width" is said to the type system.

use core::array::TryFromSliceError;

mod sealed {
    pub trait Sealed {}
    impl<const N: usize> Sealed for [u8; N] {}
}

/// A byte array of some width.
///
/// Implemented for every `[u8; N]` and, being sealed, for nothing else, so a `ByteArray` is
/// exactly [`LEN`](Self::LEN) bytes by construction: `LEN` is `N`, `as_ref()` is the array,
/// and the conversion from a slice is core's, which checks the length. The node encodings and
/// the proof layout rest on every operand having a fixed width, and this is what makes the
/// compiler hold that invariant instead of a comment.
///
/// ```compile_fail
/// use trezor_ward::trie::ByteArray;
///
/// #[derive(Clone, Copy, PartialEq, Eq)]
/// struct Lie;
/// impl AsRef<[u8]> for Lie {
///     fn as_ref(&self) -> &[u8] {
///         &[]
///     }
/// }
/// impl TryFrom<&[u8]> for Lie {
///     type Error = core::array::TryFromSliceError;
///     fn try_from(_: &[u8]) -> Result<Self, Self::Error> {
///         Ok(Lie)
///     }
/// }
/// impl ByteArray for Lie {
///     const LEN: usize = 64;
/// }
/// ```
pub trait ByteArray:
    Copy + Eq + AsRef<[u8]> + for<'a> TryFrom<&'a [u8], Error = TryFromSliceError> + sealed::Sealed
{
    /// Width in bytes.
    const LEN: usize;
}

impl<const N: usize> ByteArray for [u8; N] {
    const LEN: usize = N;
}
