//! SLOTS block: array of variable-size byte strings.
//!
//! Layout: `[t16 header] [u16 offset_0] [u16 offset_1] ... [u16 sentinel]
//! [heap]`
//!
//! Each element `n` spans `offset[n] .. offset[n+1]` (exclusive end).
//! The sentinel is the last offset and equals the block size.
//!
//! After validation, the offset array is cast to `&[u16]` for direct
//! indexed access.

use crate::{BlockData, BlockType, CodecError, Tagged16};

/// A parsed SLOTS block, borrowing from the input data.
///
/// Provides zero-copy access to variable-size byte string elements.
/// The offset table is pre-cast to `&[u16]` during validation.
#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
pub struct SlotsBlock<'a> {
    /// The raw block data (including header), length == block size.
    data: BlockData<'a>,
    /// The offset table, cast from block data. Length = offset_count
    /// (includes sentinel). element_count = offsets.len() - 1.
    offsets: &'a [Tagged16],
}

impl<'a> SlotsBlock<'a> {
    /// Parse and validate a SLOTS block from `data`.
    pub fn parse(block_data: BlockData<'a>) -> Result<Self, CodecError> {
        if block_data.block_header().block_type != BlockType::Slots {
            return Err(CodecError::UnexpectedBlockType);
        }
        let t16_prefix = block_data.as_tagged16_prefix();
        if t16_prefix.len() < 2 {
            return Err(CodecError::OutOfBounds);
        }
        let offsets = &t16_prefix[1..];
        let heap_start = offsets[0].size();
        if heap_start < 4 || heap_start > block_data.len() {
            return Err(CodecError::OutOfBounds);
        }
        if !heap_start.is_multiple_of(2) {
            return Err(CodecError::InvalidValue);
        }
        let offsets_count = (heap_start - 2) / 2;
        let offsets = &offsets[..offsets_count];
        // offsets_count must be at least (4 - 2) / 2 = 1
        let sentinel = offsets[offsets_count - 1].size();
        if sentinel != block_data.len() {
            return Err(CodecError::InvalidValue);
        }

        // Validate: offsets must be non-decreasing.
        for w in offsets.windows(2) {
            if w[0].size() > w[1].size() {
                return Err(CodecError::InvalidValue);
            }
        }
        // given non-decreasing offsets and sentinel == block size, no offset overflows

        Ok(Self {
            data: block_data,
            offsets,
        })
    }

    /// Total block size in bytes.
    pub fn len(&self) -> usize {
        self.offsets.len() - 1
    }

    pub fn is_empty(&self) -> bool {
        self.offsets.is_empty()
    }

    /// Get the byte string at element `index`.
    ///
    /// Returns `None` if the index is out of bounds.
    pub fn get_element(&self, index: usize) -> Option<&'a [u8]> {
        if index >= self.len() {
            return None;
        }
        let start = self.offsets[index].size();
        let end = self.offsets[index + 1].size();
        // Validation guarantees non-decreasing and sentinel == size,
        // so start <= end <= data.len().
        Some(&self.data.0[start..end])
    }

    /// Iterate over all elements, yielding byte slices.
    pub fn iter_elements(&self) -> SlotsBlockIter<'a, '_> {
        SlotsBlockIter {
            block: self,
            current: 0,
        }
    }
}

/// Iterator over elements of a SLOTS block.
pub struct SlotsBlockIter<'a, 'b> {
    block: &'b SlotsBlock<'a>,
    current: usize,
}

impl<'a, 'b> Iterator for SlotsBlockIter<'a, 'b> {
    type Item = &'a [u8];

    fn next(&mut self) -> Option<Self::Item> {
        let elem = self.block.get_element(self.current)?;
        self.current += 1;
        Some(elem)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn encode_block_header(block_type: u8, size: u16) -> [u8; 2] {
        let parameters = block_type << 1;
        let raw = (parameters as u16) << 13 | (size & 0x1FFF);
        raw.to_le_bytes()
    }

    fn make_aligned(src: &[u8]) -> (Vec<u8>, usize) {
        let mut buf = vec![0u8; src.len() + 8];
        let base = buf.as_ptr() as usize;
        let offset = (8 - (base % 8)) % 8;
        buf.truncate(offset + src.len());
        buf[offset..].copy_from_slice(src);
        (buf, offset)
    }

    #[test]
    fn test_slots_empty() {
        let mut raw = Vec::new();
        raw.extend_from_slice(&encode_block_header(0b10, 4));
        raw.extend_from_slice(&4u16.to_le_bytes());

        let (buf, off) = make_aligned(&raw);
        let block_data = BlockData::new_from_prefix(&buf[off..]).unwrap();
        let block = SlotsBlock::parse(block_data).unwrap();
        assert_eq!(block.len(), 0);
        assert!(block.get_element(0).is_none());
    }

    #[test]
    fn test_slots_one_element() {
        let element_count = 1usize;
        // header + offsets + sentinel
        let heap_start = 2 + 2 * element_count + 2;
        let element = b"hello";
        let size = heap_start + element.len();

        let mut raw = Vec::new();
        // header
        raw.extend_from_slice(&encode_block_header(0b10, size as u16));
        // one offset
        raw.extend_from_slice(&(heap_start as u16).to_le_bytes());
        // one sentinel
        raw.extend_from_slice(&(size as u16).to_le_bytes());
        raw.extend_from_slice(element);

        let (buf, off) = make_aligned(&raw);
        let block_data = BlockData::new_from_prefix(&buf[off..]).unwrap();
        let block = SlotsBlock::parse(block_data).unwrap();
        assert_eq!(block.len(), 1);
        assert_eq!(block.get_element(0).unwrap(), b"hello");
        assert!(block.get_element(1).is_none());
    }

    #[test]
    fn test_slots_multiple_elements() {
        let heap_start = 10usize;
        let e0 = b"ab";
        let e1 = b"cde";
        let e2 = b"f";
        let size = heap_start + e0.len() + e1.len() + e2.len();

        let off0 = heap_start;
        let off1 = off0 + e0.len();
        let off2 = off1 + e1.len();
        let sentinel = off2 + e2.len();

        let mut raw = Vec::new();
        raw.extend_from_slice(&encode_block_header(0b10, size as u16));
        raw.extend_from_slice(&(off0 as u16).to_le_bytes());
        raw.extend_from_slice(&(off1 as u16).to_le_bytes());
        raw.extend_from_slice(&(off2 as u16).to_le_bytes());
        raw.extend_from_slice(&(sentinel as u16).to_le_bytes());
        raw.extend_from_slice(e0);
        raw.extend_from_slice(e1);
        raw.extend_from_slice(e2);

        let (buf, off) = make_aligned(&raw);
        let block_data = BlockData::new_from_prefix(&buf[off..]).unwrap();
        let block = SlotsBlock::parse(block_data).unwrap();
        assert_eq!(block.len(), 3);
        assert_eq!(block.get_element(0).unwrap(), b"ab");
        assert_eq!(block.get_element(1).unwrap(), b"cde");
        assert_eq!(block.get_element(2).unwrap(), b"f");
    }

    #[test]
    fn test_slots_empty_element() {
        let heap_start = 6usize;
        let size = heap_start;

        let mut raw = Vec::new();
        raw.extend_from_slice(&encode_block_header(0b10, size as u16));
        raw.extend_from_slice(&(heap_start as u16).to_le_bytes());
        raw.extend_from_slice(&(size as u16).to_le_bytes());

        let (buf, off) = make_aligned(&raw);
        let block_data = BlockData::new_from_prefix(&buf[off..]).unwrap();
        let block = SlotsBlock::parse(block_data).unwrap();
        assert_eq!(block.len(), 1);
        assert_eq!(block.get_element(0).unwrap(), b"");
    }

    #[test]
    fn test_slots_iterator() {
        let heap_start = 8usize;
        let e0 = b"x";
        let e1 = b"yz";
        let size = heap_start + e0.len() + e1.len();

        let mut raw = Vec::new();
        raw.extend_from_slice(&encode_block_header(0b10, size as u16));
        raw.extend_from_slice(&(heap_start as u16).to_le_bytes());
        let off1 = heap_start + e0.len();
        raw.extend_from_slice(&(off1 as u16).to_le_bytes());
        raw.extend_from_slice(&(size as u16).to_le_bytes());
        raw.extend_from_slice(e0);
        raw.extend_from_slice(e1);

        let (buf, off) = make_aligned(&raw);
        let block_data = BlockData::new_from_prefix(&buf[off..]).unwrap();
        let block = SlotsBlock::parse(block_data).unwrap();
        let elements: Vec<&[u8]> = block.iter_elements().collect();
        assert_eq!(elements, vec![b"x".as_slice(), b"yz".as_slice()]);
    }

    #[test]
    fn test_slots_rejects_bad_sentinel() {
        let mut raw = Vec::new();
        raw.extend_from_slice(&encode_block_header(0b10, 8));
        raw.extend_from_slice(&6u16.to_le_bytes());
        raw.extend_from_slice(&7u16.to_le_bytes());
        raw.extend_from_slice(&[0, 0]);

        let (buf, off) = make_aligned(&raw);
        assert_eq!(
            SlotsBlock::parse(BlockData::new_from_prefix(&buf[off..]).unwrap())
                .err()
                .unwrap(),
            CodecError::InvalidValue
        );
    }

    #[test]
    fn test_slots_rejects_odd_first_offset() {
        let mut raw = Vec::new();
        raw.extend_from_slice(&encode_block_header(0b10, 5));
        raw.extend_from_slice(&5u16.to_le_bytes());
        raw.push(0);

        let (buf, off) = make_aligned(&raw);
        assert_eq!(
            SlotsBlock::parse(BlockData::new_from_prefix(&buf[off..]).unwrap())
                .err()
                .unwrap(),
            CodecError::InvalidValue
        );
    }
}
