//! TABLE block: heterogeneous container with vtable and heap.
//!
//! Layout: `[t16 header] [t16 entry_count] [t16 entries...] [heap]`
//!
//! Each vtable entry is a tagged u16 with a 3-bit type tag and 13-bit
//! offset (or inline value). The heap contains variable-size data
//! referenced by DIRECT, BLOCK, and LINK entries.
//!
//! After upfront validation in [`TableBlock::parse`], the vtable is cast
//! to a `&[u16]` slice for direct indexed access without further bounds
//! checks or byte shuffling.

use bytemuck::AnyBitPattern;

use crate::{
    BlockData, BlockType, CodecError, Link, Params, Size, Tagged16, try_from_bytes_prefix,
};

/// Type tag for a vtable entry.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u8)]
pub enum VTableEntryType {
    /// Field is absent / not set.
    Null = 0b000,
    /// Length-prefixed bytestring on the heap.
    DirectData = 0b001,
    /// Raw 4-byte primitive on the heap.
    Direct4 = 0b010,
    /// Raw 8-byte primitive on the heap.
    Direct8 = 0b011,
    /// Small integer value encoded directly in the offset field (13 bits).
    Inline = 0b100,
    /// Offset to a sub-block on the heap (has its own block header).
    Block = 0b101,
    /// Offset to a 36-byte Link structure on the heap.
    Link = 0b110,
    /// Reserved type
    Reserved = 0b111,
}

impl VTableEntryType {
    fn from_params(params: Params) -> Self {
        match params.0 {
            0b000 => Self::Null,
            0b001 => Self::DirectData,
            0b010 => Self::Direct4,
            0b011 => Self::Direct8,
            0b100 => Self::Inline,
            0b101 => Self::Block,
            0b110 => Self::Link,
            0b111 => Self::Reserved,
            _ => unreachable!(),
        }
    }

    fn to_params(self) -> Params {
        Params(match self {
            Self::Null => 0b000,
            Self::DirectData => 0b001,
            Self::Direct4 => 0b010,
            Self::Direct8 => 0b011,
            Self::Inline => 0b100,
            Self::Block => 0b101,
            Self::Link => 0b110,
            Self::Reserved => 0b111,
        })
    }
}

/// A parsed vtable entry.
#[derive(Clone, Copy, bytemuck::AnyBitPattern)]
#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
#[repr(transparent)]
pub struct VTableEntry(Tagged16);

impl VTableEntry {
    #[inline]
    pub fn entry_type(self) -> VTableEntryType {
        VTableEntryType::from_params(Params::from_tagged16(self.0))
    }

    #[inline]
    pub fn value(&self) -> usize {
        self.0.size()
    }

    /// Returns true if this entry is NULL (absent).
    #[inline]
    pub fn is_null(&self) -> bool {
        matches!(self.entry_type(), VTableEntryType::Null)
    }

    pub fn in_bounds(&self, heap_start: usize, block_size: usize) -> bool {
        match self.entry_type() {
            VTableEntryType::Null | VTableEntryType::Inline => true,
            VTableEntryType::DirectData
            | VTableEntryType::Direct4
            | VTableEntryType::Direct8
            | VTableEntryType::Block
            | VTableEntryType::Link => {
                let offset = self.value();
                offset >= heap_start && offset < heap_start + block_size
            }
            VTableEntryType::Reserved => false,
        }
    }

    pub fn null() -> Self {
        Self(Tagged16::build(VTableEntryType::Null.to_params(), Size(0)))
    }
}

/// A parsed TABLE block, borrowing from the input data.
///
/// After validation, the vtable is available as a `&[Tagged16]` slice
/// for direct indexed access with no byte-shuffling. Heap data is a
/// `&[u8]` sub-slice. All accesses are bounds-safe because validation
/// was performed upfront in [`TableBlock::parse`].
#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
pub struct TableBlock<'a> {
    /// The raw block data (including header), length == block size.
    data: BlockData<'a>,
    vtable: &'a [VTableEntry],
}

impl<'a> TableBlock<'a> {
    /// Parse and validate a TABLE block from `data`.
    ///
    /// `data` must start at the block header and its pointer must be
    /// 2-aligned (minimum block alignment). After successful return,
    /// all subsequent field accesses are bounds-safe and aligned.
    pub fn parse(data: BlockData<'a>) -> Result<Self, CodecError> {
        let block_header = data.block_header();
        if block_header.block_type != BlockType::Table {
            return Err(CodecError::UnexpectedBlockType);
        }
        let t16_prefix = data.as_tagged16_prefix();
        if t16_prefix.len() < 2 {
            return Err(CodecError::OutOfBounds);
        }
        let vtable_with_header = &t16_prefix[1..];
        let entry_count = vtable_with_header[0].size();
        if entry_count + 1 > vtable_with_header.len() {
            return Err(CodecError::OutOfBounds);
        }
        if vtable_with_header[0].params() != 0 {
            return Err(CodecError::InvalidValue);
        }

        let vtable = bytemuck::cast_slice(&vtable_with_header[1..entry_count + 1]);

        let table = Self { data, vtable };
        // Validate all entries.
        table.validate_entries()?;

        Ok(table)
    }

    pub const fn heap_start(&self) -> usize {
        4 + 2 * self.vtable.len()
    }

    /// Validate all vtable entries for structural correctness.
    fn validate_entries(&self) -> Result<(), CodecError> {
        let heap_start = self.heap_start();
        let size = self.data.len();
        for entry in self.vtable {
            if !entry.in_bounds(heap_start, size) {
                return Err(CodecError::OutOfBounds);
            }
            let entry_type = entry.entry_type();
            match entry_type {
                VTableEntryType::Link => {
                    Link::new_from_prefix(&self.data.0[entry.value()..])?;
                }
                VTableEntryType::Block => {
                    BlockData::new_from_prefix(&self.data.0[entry.value()..])?;
                }
                VTableEntryType::Reserved => {
                    return Err(CodecError::InvalidValue);
                }
                _ => {}
            };
        }
        Ok(())
    }

    /// Total size of this block in bytes.
    pub fn size(&self) -> usize {
        self.data.len()
    }

    /// Number of vtable entries.
    pub fn len(&self) -> usize {
        self.vtable.len()
    }

    pub fn is_empty(&self) -> bool {
        self.vtable.is_empty()
    }

    /// Get the vtable entry at `index`, or NULL if `index >= entry_count`.
    pub fn get_entry(&self, index: usize) -> VTableEntry {
        match self.vtable.get(index) {
            Some(&entry) => entry,
            None => VTableEntry::null(),
        }
    }

    fn get_heap_data(&self, offset: usize) -> &'a [u8] {
        debug_assert!(offset >= self.heap_start() && offset < self.data.len());
        &self.data.0[offset..]
    }

    fn get_primitive_from_direct<T: AnyBitPattern>(&self, offset: usize) -> Result<&T, CodecError> {
        let heap_data = self.get_heap_data(offset);
        try_from_bytes_prefix::<T>(heap_data)
    }

    fn match_uinline(&self, index: usize) -> Result<Option<u16>, VTableEntry> {
        let entry = self.get_entry(index);
        match entry.entry_type() {
            VTableEntryType::Null => Ok(None),
            VTableEntryType::Inline => Ok(Some(Size::from_tagged16(entry.0).into())),
            _ => Err(entry),
        }
    }

    fn match_sinline(&self, index: usize) -> Result<Option<i16>, VTableEntry> {
        let entry = self.get_entry(index);
        match entry.entry_type() {
            VTableEntryType::Null => Ok(None),
            VTableEntryType::Inline => Ok(Some(Size::from_tagged16(entry.0).into())),
            _ => Err(entry),
        }
    }

    fn match_u32(&self, index: usize) -> Result<Option<u32>, VTableEntry> {
        match self.match_uinline(index) {
            Ok(result) => Ok(result.map(Into::into)),
            Err(entry) if entry.entry_type() == VTableEntryType::Direct4 => Ok(self
                .get_primitive_from_direct::<u32>(entry.value())
                .copied()
                .ok()),
            Err(entry) => Err(entry),
        }
    }

    fn match_i32(&self, index: usize) -> Result<Option<i32>, VTableEntry> {
        match self.match_sinline(index) {
            Ok(result) => Ok(result.map(Into::into)),
            Err(entry) if entry.entry_type() == VTableEntryType::Direct4 => Ok(self
                .get_primitive_from_direct::<i32>(entry.value())
                .copied()
                .ok()),
            Err(entry) => Err(entry),
        }
    }

    pub fn get_u8(&self, index: usize) -> Option<u8> {
        self.match_uinline(index)
            .unwrap_or(None)
            .and_then(|v| v.try_into().ok())
    }

    pub fn get_u16(&self, index: usize) -> Option<u16> {
        self.match_u32(index)
            .unwrap_or(None)
            .and_then(|v| v.try_into().ok())
    }

    pub fn get_u32(&self, index: usize) -> Option<u32> {
        self.match_u32(index).unwrap_or(None)
    }

    pub fn get_u64(&self, index: usize) -> Option<u64> {
        match self.match_u32(index) {
            Ok(result) => result.map(Into::into),
            Err(entry) if entry.entry_type() == VTableEntryType::Direct8 => self
                .get_primitive_from_direct::<u64>(entry.value())
                .copied()
                .ok(),
            Err(_) => None,
        }
    }

    pub fn get_i8(&self, index: usize) -> Option<i8> {
        self.match_sinline(index)
            .unwrap_or(None)
            .and_then(|v| v.try_into().ok())
    }

    pub fn get_i16(&self, index: usize) -> Option<i16> {
        self.match_i32(index)
            .unwrap_or(None)
            .and_then(|v| v.try_into().ok())
    }

    pub fn get_i32(&self, index: usize) -> Option<i32> {
        self.match_i32(index).unwrap_or(None)
    }

    pub fn get_i64(&self, index: usize) -> Option<i64> {
        match self.match_i32(index) {
            Ok(result) => result.map(Into::into),
            Err(entry) if entry.entry_type() == VTableEntryType::Direct8 => self
                .get_primitive_from_direct::<i64>(entry.value())
                .copied()
                .ok(),
            Err(_) => None,
        }
    }

    pub fn get_f32(&self, index: usize) -> Option<f32> {
        let entry = self.get_entry(index);
        if entry.entry_type() == VTableEntryType::Direct4 {
            self.get_primitive_from_direct::<f32>(entry.value())
                .copied()
                .ok()
        } else {
            None
        }
    }

    pub fn get_f64(&self, index: usize) -> Option<f64> {
        let entry = self.get_entry(index);
        if entry.entry_type() == VTableEntryType::Direct8 {
            self.get_primitive_from_direct::<f64>(entry.value())
                .copied()
                .ok()
        } else {
            None
        }
    }

    /// Read raw fixed-size bytes from a DIRECT entry at `index`.
    ///
    /// Returns `None` for NULL entries.
    pub fn get_direct_data(&self, index: usize) -> Option<&'a [u8]> {
        let entry = self.get_entry(index);
        if entry.entry_type() != VTableEntryType::DirectData {
            return None;
        }
        let offset = entry.value();
        let heap_data = self.get_heap_data(offset);
        let header = try_from_bytes_prefix::<Tagged16>(heap_data).ok()?;
        if header.params() != 0 {
            return None;
        }
        let size = header.size();
        if offset + 2 + size > self.data.len() {
            return None;
        }
        Some(&self.data.0[(offset + 2)..(offset + 2 + size)])
    }

    /// Get a sub-block or Link from a BLOCK or LINK entry at `index`.
    ///
    /// Returns `None` for NULL entries.
    pub fn get_block_or_link(&self, index: usize) -> Result<Option<BlockOrLink<'a>>, CodecError> {
        let entry = self.get_entry(index);
        match entry.entry_type() {
            VTableEntryType::Block => {
                let offset = entry.value();
                let block = BlockData::new_from_prefix(&self.data.0[offset..])?;
                Ok(Some(BlockOrLink::Block(block)))
            }
            VTableEntryType::Link => {
                let offset = entry.value();
                let link = Link::new_from_prefix(&self.data.0[offset..])?;
                Ok(Some(BlockOrLink::Link(link)))
            }
            VTableEntryType::Null => Ok(None),
            _ => Err(CodecError::InvalidEntryType),
        }
    }
}

/// Result of looking up a BLOCK or LINK vtable entry.
pub enum BlockOrLink<'a> {
    /// Raw sub-block data (starts with block header).
    Block(BlockData<'a>),
    /// External link to another block.
    Link(&'a Link),
}

#[cfg(test)]
mod tests {
    use super::super::tests::*;
    use super::super::*;
    use super::*;

    impl BlockBuilder {
        pub fn push_vtable_entry(
            &mut self,
            entry_type: VTableEntryType,
            value: usize,
        ) -> &mut Self {
            self.push_t16(Tagged16::build(
                entry_type.to_params(),
                value.try_into().unwrap(),
            ));
            self
        }

        pub fn push_entry_count(&mut self, entry_count: usize) -> &mut Self {
            self.push_t16(Tagged16::new(0, entry_count).unwrap());
            self
        }
    }

    #[test]
    fn test_empty_table() {
        let mut builder = BlockBuilder::new_block(BlockType::Table, 4).unwrap();
        builder.push_t16(Tagged16::new(0, 0).unwrap());
        let block_data = builder.to_block_data().unwrap();
        let table = TableBlock::parse(block_data).unwrap();

        assert_eq!(table.len(), 0);
        assert_eq!(table.size(), 4);
        assert!(table.get_entry(0).is_null());
    }

    #[test]
    fn test_table_with_inline_entries() {
        let entry_count = 3;
        let size = 4 + 2 * entry_count;
        let mut builder = BlockBuilder::new_block(BlockType::Table, size).unwrap();
        builder
            .push_entry_count(entry_count)
            .push_vtable_entry(VTableEntryType::Null, 0)
            .push_vtable_entry(VTableEntryType::Inline, 42)
            .push_vtable_entry(VTableEntryType::Inline, 100);
        let block_data = builder.to_block_data().unwrap();

        let table = TableBlock::parse(block_data).unwrap();
        assert_eq!(table.len(), 3);

        assert!(table.get_entry(0).is_null());
        assert_eq!(table.get_u32(1), Some(42));
        assert_eq!(table.get_u32(2), Some(100));
        assert_eq!(table.get_u32(3), None);
    }

    #[test]
    fn test_table_with_direct_u32() {
        let entry_count = 1;
        let heap_start = 4 + 2 * entry_count;
        let value_offset = align_up(heap_start + 3, 4);
        let padding = value_offset - heap_start;
        let size = value_offset + 4;

        let mut builder = BlockBuilder::new_block(BlockType::Table, size).unwrap();
        builder
            .push_t16(Tagged16::new(0, entry_count).unwrap())
            .push_vtable_entry(VTableEntryType::Direct4, value_offset)
            .extend(core::iter::repeat(0u8).take(padding))
            .extend_from_slice(&0x12345678u32.to_le_bytes());

        let block_data = builder.to_block_data().unwrap();
        let table = TableBlock::parse(block_data).unwrap();
        assert_eq!(table.get_u32(0), Some(0x12345678));
    }

    #[test]
    fn test_table_with_direct_signed() {
        let entry_count = 1;
        let heap_start = (4 + 2 * entry_count) as usize;
        let value_offset = (heap_start + 3) & !3;
        let padding = value_offset - heap_start;
        let size = value_offset + 4;

        let mut builder = BlockBuilder::new_block(BlockType::Table, size).unwrap();
        builder
            .push_t16(Tagged16::new(0, entry_count).unwrap())
            .push_vtable_entry(VTableEntryType::Direct4, value_offset)
            .extend(core::iter::repeat(0u8).take(padding))
            .extend_from_slice(&(-1000i32).to_le_bytes());

        let block_data = builder.to_block_data().unwrap();
        let table = TableBlock::parse(block_data).unwrap();
        assert_eq!(table.get_i32(0), Some(-1000));
    }

    #[test]
    fn test_table_with_inline_signed() {
        let entry_count = 1;
        let size = 4 + 2 * entry_count;
        let mut builder = BlockBuilder::new_block(BlockType::Table, size).unwrap();
        builder
            .push_t16(Tagged16::new(0, entry_count).unwrap())
            .push_vtable_entry(VTableEntryType::Inline, 0x1FFF);
        let block_data = builder.to_block_data().unwrap();
        let table = TableBlock::parse(block_data).unwrap();
        assert_eq!(table.get_i32(0), Some(-1));
    }

    #[test]
    fn test_table_with_sub_block() {
        let inner_size = 4;
        let entry_count = 1;
        let heap_start = 4 + 2 * entry_count;
        let block_offset = heap_start;
        let outer_size = block_offset + inner_size;

        let mut builder = BlockBuilder::new_block(BlockType::Table, outer_size).unwrap();
        builder
            .push_t16(Tagged16::new(0, entry_count).unwrap())
            .push_vtable_entry(VTableEntryType::Block, block_offset)
            .push_block_header(BlockHeader::new(BlockType::Table, Size(inner_size)))
            .push_t16(Tagged16::new(0, 0).unwrap());
        let block_data = builder.to_block_data().unwrap();

        let table = TableBlock::parse(block_data).unwrap();
        let result = table.get_block_or_link(0).unwrap().unwrap();
        match result {
            BlockOrLink::Block(sub_data) => {
                let inner = TableBlock::parse(sub_data).unwrap();
                assert_eq!(inner.len(), 0);
            }
            BlockOrLink::Link(_) => panic!("expected Block"),
        }
    }

    #[test]
    fn test_table_with_link() {
        let entry_count = 1;
        let heap_start = 4 + 2 * entry_count;
        let link_offset = (heap_start + 3) & !3;
        let padding = link_offset - heap_start;
        let size = link_offset + LINK_SIZE;

        let mut builder = BlockBuilder::new_block(BlockType::Table, size).unwrap();
        builder
            .push_t16(Tagged16::new(0, entry_count).unwrap())
            .push_vtable_entry(VTableEntryType::Link, link_offset)
            .extend(core::iter::repeat(0u8).take(padding))
            .extend_from_slice(&[0xAA; 32])
            .extend_from_slice(&42u32.to_le_bytes());

        let block_data = builder.to_block_data().unwrap();
        let table = TableBlock::parse(block_data).unwrap();
        let result = table.get_block_or_link(0).unwrap().unwrap();
        match result {
            BlockOrLink::Link(link) => {
                assert_eq!(link.digest, [0xAAu8; 32]);
                assert_eq!(link.limit, 42);
            }
            BlockOrLink::Block(_) => panic!("expected Link"),
        }
    }

    #[test]
    fn test_table_rejects_zero_link_limit() {
        let entry_count = 1;
        let heap_start = 4 + 2 * entry_count;
        let link_offset = (heap_start + 3) & !3;
        let padding = link_offset - heap_start;
        let size = link_offset + LINK_SIZE;

        let mut builder = BlockBuilder::new_block(BlockType::Table, size).unwrap();
        builder
            .push_entry_count(entry_count)
            .push_vtable_entry(VTableEntryType::Link, link_offset)
            .extend(core::iter::repeat(0u8).take(padding))
            .extend_from_slice(&[0xBB; 32])
            .extend_from_slice(&0u32.to_le_bytes());
        let block_data = builder.to_block_data().unwrap();
        assert_eq!(
            TableBlock::parse(block_data).err().unwrap(),
            CodecError::InvalidValue
        );
    }

    #[test]
    fn test_table_rejects_reserved_entry_type() {
        let entry_count = 1;
        let size = 4 + 2 * entry_count;

        let mut builder = BlockBuilder::new_block(BlockType::Table, size).unwrap();
        builder
            .push_entry_count(entry_count)
            .push_vtable_entry(VTableEntryType::Reserved, size);
        let block_data = builder.to_block_data().unwrap();
        assert!(TableBlock::parse(block_data).is_err());
    }
}
