//! Zero-copy, no_std, no_alloc codec for the hashbuffers wire format.
//!
//! This module provides types for parsing hashbuffer blocks from byte slices
//! without any heap allocation. All returned values are either inline or
//! borrow from the input data.
//!
//! # Alignment
//!
//! The hashbuffers wire format guarantees that all values within a block are
//! properly aligned relative to the block start. Callers MUST ensure that
//! the input data slice is aligned to at least 2 bytes (the minimum block
//! alignment). For blocks containing u32/u64 values or links, the input
//! must be aligned to 4 or 8 bytes respectively.
//!
//! On little-endian platforms, this enables direct pointer reads: after
//! upfront validation, typed slices (`&[u16]`, `&[RawLink]`, etc.) are
//! used for subsequent access with no byte-shuffling overhead.
//!
//! # Block types
//!
//! - [`TableBlock`] -- heterogeneous container with a vtable and heap
//! - [`DataBlock`] -- array of fixed-size elements
//! - [`SlotsBlock`] -- array of variable-size byte strings
//! - [`LinksBlock`] -- array of 36-byte links (link tree inner node)

#![cfg_attr(not(test), no_std)]

// Require little-endian. The wire format is LE and we rely on aligned reads
// being correct without byte-swapping.
#[cfg(not(target_endian = "little"))]
compile_error!("hashbuffers codec requires a little-endian target");

pub mod data;
pub mod links;
pub mod slots;
pub mod table;

use bytemuck::{AnyBitPattern, NoUninit, PodCastError};
pub use data::DataBlock;
pub use links::LinksBlock;
pub use slots::SlotsBlock;
pub use table::{TableBlock, VTableEntry, VTableEntryType};

/// Maximum block size (13-bit number field).
pub const SIZE_MAX: usize = 0x1FFF; // 8191

/// Size of a Link structure: 32-byte digest + 4-byte limit.
pub const LINK_SIZE: usize = 36;

/// Alignment of a Link structure.
pub const LINK_ALIGN: usize = 4;

macro_rules! unwrap_unreachable {
    ($expr:expr, $msg:expr) => {
        match $expr {
            Ok(x) => x,
            Err(_) => unreachable!($msg),
        }
    };
    ($expr:expr) => {
        match $expr {
            Ok(x) => x,
            Err(_) => unreachable!(stringify!($expr)),
        }
    };
}
#[allow(clippy::needless_pub_self, unused)]
pub(self) use unwrap_unreachable;

impl From<PodCastError> for CodecError {
    fn from(e: PodCastError) -> Self {
        match e {
            PodCastError::TargetAlignmentGreaterAndInputNotAligned => CodecError::AlignmentError,
            PodCastError::OutputSliceWouldHaveSlop => CodecError::OutOfBounds,
            PodCastError::SizeMismatch => CodecError::OutOfBounds,
            PodCastError::AlignmentMismatch => CodecError::AlignmentError,
        }
    }
}

// ---------------------------------------------------------------------------
// Tagged16 -- the fundamental building block of the wire format
// ---------------------------------------------------------------------------

#[derive(Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
#[repr(transparent)]
pub struct Params(u8);

impl Params {
    pub const fn new(value: u8) -> Result<Self, CodecError> {
        if value & !0b111 != 0 {
            return Err(CodecError::ValueOverflow);
        }
        Ok(Self(value))
    }

    #[inline]
    pub const fn from_tagged16(t16: Tagged16) -> Self {
        Self(t16.params())
    }
}

impl TryFrom<u8> for Params {
    type Error = CodecError;
    fn try_from(value: u8) -> Result<Self, Self::Error> {
        Self::new(value)
    }
}

impl From<Params> for u8 {
    fn from(value: Params) -> Self {
        value.0
    }
}

#[derive(Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
#[repr(transparent)]
pub struct Size(usize);

impl Size {
    pub const MAX: Self = Self(SIZE_MAX);

    pub const fn new(value: usize) -> Result<Self, CodecError> {
        if value > SIZE_MAX {
            return Err(CodecError::ValueOverflow);
        }
        Ok(Self(value))
    }

    #[inline]
    pub const fn sign_extend(self) -> isize {
        if self.0 & 0x1000 != 0 {
            (self.0 as isize) | !(SIZE_MAX as isize)
        } else {
            self.0 as isize
        }
    }

    #[inline]
    pub const fn from_tagged16(t16: Tagged16) -> Self {
        Self(t16.size())
    }
}

impl TryFrom<usize> for Size {
    type Error = CodecError;
    fn try_from(value: usize) -> Result<Self, Self::Error> {
        Self::new(value)
    }
}

impl From<Size> for usize {
    fn from(value: Size) -> Self {
        value.0
    }
}

impl From<Size> for u16 {
    fn from(value: Size) -> Self {
        value.0 as u16
    }
}

impl From<Size> for isize {
    fn from(value: Size) -> Self {
        value.sign_extend()
    }
}

impl From<Size> for i16 {
    fn from(value: Size) -> Self {
        value.sign_extend() as i16
    }
}

/// A tagged u16 value: 3-bit parameters in the high bits, 13-bit number below.
///
/// Used for block headers, vtable entry counts, and vtable entries.
/// `repr(transparent)` over a native-endian `u16` so that a `&[Tagged16]`
/// can be directly cast from aligned block data on LE platforms.
#[derive(Clone, Copy, PartialEq, Eq, AnyBitPattern, NoUninit)]
#[repr(transparent)]
pub struct Tagged16(u16);

impl Tagged16 {
    pub const fn build(params: Params, size: Size) -> Self {
        let param_bits = (params.0 as u16) << 13;
        let size_bits = size.0 as u16;
        Self(param_bits | size_bits)
    }

    pub fn new(params: u8, number: usize) -> Result<Self, CodecError> {
        let params = Params::try_from(params)?;
        let size = Size::try_from(number)?;
        Ok(Self::build(params, size))
    }

    /// The 3-bit parameter field (bits 15..13).
    #[inline]
    pub const fn params(self) -> u8 {
        (self.0 >> 13) as u8
    }

    /// The 13-bit number field (bits 12..0).
    #[inline]
    pub const fn size(self) -> usize {
        (self.0 & SIZE_MAX as u16) as usize
    }
}

#[cfg(feature = "debug")]
impl ufmt::uDebug for Tagged16 {
    fn fmt<W>(&self, w: &mut ufmt::Formatter<'_, W>) -> Result<(), W::Error>
    where
        W: ufmt::uWrite + ?Sized,
    {
        w.write_str("Tagged16(")?;
        Params::from_tagged16(*self).fmt(w)?;
        w.write_str(", ")?;
        Size::from_tagged16(*self).fmt(w)?;
        w.write_str(")")?;
        Ok(())
    }
}

#[repr(transparent)]
#[derive(Copy, Clone)]
#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
pub struct BlockData<'a>(&'a [u8]);

impl<'a> BlockData<'a> {
    pub fn new_from_prefix(data: &'a [u8]) -> Result<Self, CodecError> {
        // validate block header (try_from_bytes_prefix checks size & alignment)
        let header = try_from_bytes_prefix::<Tagged16>(data)?;
        let block_header = BlockHeader::from_tagged16(*header)?;
        if block_header.size() > data.len() {
            return Err(CodecError::OutOfBounds);
        }
        Ok(Self(&data[..block_header.size()]))
    }

    #[inline]
    pub fn as_tagged16_prefix(&self) -> &'a [Tagged16] {
        let (_prefix, header, _suffix) = bytemuck::pod_align_to::<u8, Tagged16>(self.0);
        debug_assert!(
            _prefix.is_empty(),
            "Unaligned block should not have been possible to construct"
        );
        // suffix can be non-empty
        header
    }

    #[inline]
    pub fn block_header(&self) -> BlockHeader {
        let header = expect_from_bytes_prefix::<Tagged16>(self.0);
        unwrap_unreachable!(BlockHeader::from_tagged16(*header))
    }

    #[inline]
    pub fn block_type(&self) -> BlockType {
        self.block_header().block_type
    }

    #[inline]
    pub fn max_alignment(&self) -> usize {
        // calculate maximum alignment available in the block
        let start_offset = self.0.as_ptr() as usize;
        debug_assert!(start_offset != 0);
        start_offset & !(start_offset - 1)
    }

    #[inline]
    pub fn is_aligned_to(&self, align: usize) -> bool {
        (self.0.as_ptr() as usize).is_multiple_of(align)
    }

    #[inline]
    pub fn len(&self) -> usize {
        self.0.len()
    }

    #[inline]
    pub fn is_empty(&self) -> bool {
        self.0.is_empty()
    }
}

// ---------------------------------------------------------------------------
// Block types and headers
// ---------------------------------------------------------------------------

/// Block type encoded in the header.
#[derive(Clone, Copy, PartialEq, Eq)]
#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
#[repr(u8)]
pub enum BlockType {
    Table = 0b00,
    Data = 0b01,
    Slots = 0b10,
    Links = 0b11,
}

impl BlockType {
    pub fn from_params(params: Params) -> Result<Self, CodecError> {
        if params.0 & 0b001 != 0 {
            return Err(CodecError::InvalidValue);
        }
        let type_bits = params.0 >> 1;
        match type_bits {
            0b00 => Ok(Self::Table),
            0b01 => Ok(Self::Data),
            0b10 => Ok(Self::Slots),
            0b11 => Ok(Self::Links),
            _ => unreachable!(),
        }
    }

    pub fn to_params(self) -> Params {
        Params((self as u8) << 1)
    }
}

/// Parsed block header.
#[derive(Clone, Copy)]
#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
pub struct BlockHeader {
    pub block_type: BlockType,
    /// Total size of the block including the 2-byte header.
    size: Size,
}

impl BlockHeader {
    pub fn new(block_type: BlockType, size: Size) -> Self {
        Self { block_type, size }
    }

    pub fn from_tagged16(t16: Tagged16) -> Result<Self, CodecError> {
        Ok(Self {
            block_type: BlockType::from_params(Params::from_tagged16(t16))?,
            size: Size::from_tagged16(t16),
        })
    }

    pub fn to_tagged16(self) -> Tagged16 {
        Tagged16::build(self.block_type.to_params(), self.size)
    }

    pub fn size(&self) -> usize {
        self.size.into()
    }
}

// ---------------------------------------------------------------------------
// Link
// ---------------------------------------------------------------------------

/// On-wire layout of a 36-byte link: 32-byte digest + u32 limit.
///
/// `repr(C)` with 4-byte alignment so that a `&[RawLink]` can be cast
/// directly from 4-aligned block data.
#[derive(Copy, Clone, bytemuck::AnyBitPattern)]
#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
#[repr(C)]
pub struct Link {
    pub digest: [u8; 32],
    pub limit: u32,
}

const _: () = {
    // assert validity of constants
    assert!(core::mem::size_of::<Link>() == LINK_SIZE);
    assert!(core::mem::align_of::<Link>() == LINK_ALIGN);
    // assert packing
    assert!(
        core::mem::size_of::<Link>()
            == core::mem::size_of::<[u8; 32]>() + core::mem::size_of::<u32>()
    );
};

impl Link {
    pub fn new_from_prefix(data: &[u8]) -> Result<&Self, CodecError> {
        let link = try_from_bytes_prefix::<Self>(data)?;
        if link.limit == 0 {
            return Err(CodecError::InvalidValue);
        }
        Ok(link)
    }
}

// ---------------------------------------------------------------------------
// Error
// ---------------------------------------------------------------------------

/// Error type for codec operations.
#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CodecError {
    /// Alignment error
    AlignmentError,
    /// Out of bounds access
    OutOfBounds,
    /// Value overflow.
    ValueOverflow,
    /// Invalid value in some field (reserved bits set, disallowed value, etc.)
    InvalidValue,
    /// Invalid block
    InvalidBlock,
    /// Block type in header doesn't match expected type.
    UnexpectedBlockType,
    /// Requested value not stored in expected entry type.
    InvalidEntryType,
}

// ---------------------------------------------------------------------------
// Alignment math
// ---------------------------------------------------------------------------

/// Round up `value` to the next multiple of `align`.
/// `align` must be a power of two.
#[inline]
pub const fn align_up(value: usize, align: usize) -> usize {
    (value + align - 1) & !(align - 1)
}

/// Try to convert the first bytes of `data` to a `T`
///
/// Helper on top of bytemuck::try_from_bytes to cut off trailing bytes.
/// Returns `Err(CodecError::OutOfBounds)` if the data is too short.
/// Returns `Err(CodecError::AlignmentError)` if the data is not aligned.
#[inline]
pub fn try_from_bytes_prefix<T: AnyBitPattern>(data: &[u8]) -> Result<&T, CodecError> {
    let maxlen = core::mem::size_of::<T>().min(data.len());
    let bytes = &data[..maxlen];
    Ok(bytemuck::try_from_bytes::<T>(bytes)?)
}

/// Convert the first bytes of `data` to a `T`, expecting to succeed.
///
/// Helper for reading data that we previously validated. Wraps
/// `try_from_bytes_prefix`` in `unwrap_unreachable!``.
#[inline]
pub fn expect_from_bytes_prefix<T: AnyBitPattern>(data: &[u8]) -> &T {
    unwrap_unreachable!(try_from_bytes_prefix::<T>(data))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_size_sign_extend() {
        assert_eq!(Size(0).sign_extend(), 0);
        assert_eq!(Size(1).sign_extend(), 1);
        assert_eq!(Size(0x0FFF).sign_extend(), 0x0FFF);
        assert_eq!(Size(0x1FFF).sign_extend(), -1);
        assert_eq!(Size(0x1000).sign_extend(), -4096);
        assert_eq!(Size(0x1FFE).sign_extend(), -2);
    }

    pub struct BlockBuilder {
        data: Vec<u64>,
        written: usize,
    }

    impl BlockBuilder {
        pub fn new() -> Self {
            Self {
                data: Vec::new(),
                written: 0,
            }
        }

        fn bytes_to_words(bytes: usize) -> usize {
            (bytes + 7) / 8
        }

        fn words_to_bytes(words: usize) -> usize {
            words * 8
        }

        pub fn new_block(block_type: BlockType, size: usize) -> Result<Self, CodecError> {
            let mut new = Self {
                data: Vec::with_capacity(Self::words_to_bytes(size)),
                written: 0,
            };
            new.push_block_header(BlockHeader::new(block_type, size.try_into()?));
            Ok(new)
        }

        pub fn as_mut_buf(&mut self) -> &mut [u8] {
            let native_slice = self.data.as_mut_slice();
            bytemuck::cast_slice_mut(native_slice)
        }

        pub fn as_bytes(&self) -> &[u8] {
            let native_slice = self.data.as_slice();
            bytemuck::cast_slice(native_slice)
        }

        pub fn to_block_data<'a>(&'a self) -> Result<BlockData<'a>, CodecError> {
            BlockData::new_from_prefix(self.as_bytes())
        }

        pub fn extend(&mut self, iter: impl Iterator<Item = u8>) -> &mut Self {
            self.extend_from_slice(iter.collect::<Vec<u8>>().as_slice());
            self
        }

        pub fn extend_from_slice(&mut self, slice: &[u8]) -> &mut Self {
            let words_needed = Self::bytes_to_words(self.written + slice.len());
            self.data.resize(words_needed, 0);
            let written = self.written;
            let buf = self.as_mut_buf();
            buf[written..(written + slice.len())].copy_from_slice(slice);
            self.written = written + slice.len();
            self
        }

        pub fn push_t16(&mut self, t16: Tagged16) -> &mut Self {
            self.extend_from_slice(&t16.0.to_le_bytes());
            self
        }

        pub fn push_block_header(&mut self, block_header: BlockHeader) -> &mut Self {
            self.push_t16(block_header.to_tagged16());
            self
        }
    }
}
