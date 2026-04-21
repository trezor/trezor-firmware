//! LINKS block: array of links / link tree inner node.
//!
//! Layout: `[t16 header] [u16 reserved] [link_0] [link_1] ...`
//!
//! Each link is 36 bytes: 32-byte digest + 4-byte cumulative limit.
//! Limits must be strictly increasing and non-zero.
//!
//! After validation, the links region is cast to `&[RawLink]` for
//! direct indexed access.

use crate::{BlockData, BlockType, CodecError, LINK_ALIGN, Link};

/// A parsed LINKS block, borrowing from the input data.
///
/// Provides access to an array of links for link tree traversal.
/// The links array is pre-cast to `&[RawLink]` during validation.
#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
pub struct LinksBlock<'a> {
    /// The links, cast from block data.
    links: &'a [Link],
}

impl<'a> LinksBlock<'a> {
    /// Parse and validate a LINKS block from `data`.
    pub fn parse(block_data: BlockData<'a>) -> Result<Self, CodecError> {
        let header = block_data.block_header();
        if header.block_type != BlockType::Links {
            return Err(CodecError::UnexpectedBlockType);
        }
        if block_data.len() < LINK_ALIGN {
            return Err(CodecError::OutOfBounds);
        }
        if !block_data.is_aligned_to(LINK_ALIGN) {
            return Err(CodecError::AlignmentError);
        }

        let t16_prefix = block_data.as_tagged16_prefix();

        // Check reserved field is zero.
        if t16_prefix[1].0 != 0 {
            return Err(CodecError::InvalidValue);
        }

        let links_data = &block_data.0[LINK_ALIGN..];
        // SAFETY: Link is repr(C) and valid for any bit pattern.
        let (_prefix, links, _suffix) = bytemuck::pod_align_to::<u8, Link>(links_data);
        // we just checked that we are aligned
        debug_assert!(_prefix.is_empty(), "Links data should be aligned to Link");
        // there must not be any trailing data
        if !_suffix.is_empty() {
            return Err(CodecError::InvalidBlock);
        }

        // Validate limits are strictly increasing and non-zero.
        let mut prev_limit: u32 = 0;
        for link in links {
            if link.limit == 0 || link.limit <= prev_limit {
                return Err(CodecError::InvalidValue);
            }
            prev_limit = link.limit;
        }

        Ok(Self { links })
    }

    /// Number of links in this block.
    pub fn len(&self) -> usize {
        self.links.len()
    }

    pub fn is_empty(&self) -> bool {
        self.links.is_empty()
    }

    pub fn links(&self) -> &[Link] {
        self.links
    }

    /// The total content length represented by this LINKS block.
    ///
    /// This is the `limit` of the last link (cumulative count).
    pub fn content_length(&self) -> u32 {
        self.links.last().map_or(0, |link| link.limit)
    }

    /// Find the link index whose content contains the global `target_index`.
    ///
    /// Returns `(link_index, local_index, stated_content_length)`:
    /// - `link_index`: which link to descend into
    /// - `local_index`: the index within that link's content
    /// - `stated_content_length`: expected element count of the child
    ///
    /// Returns `None` if `target_index >= content_length()`.
    pub fn find_link_for_index(&self, target_index: u32) -> Option<(usize, u32, u32)> {
        if self.links.is_empty() {
            return None;
        }

        let index = match self
            .links
            .binary_search_by_key(&target_index, |link| link.limit)
        {
            // found a link whose limit is exactly target_index -> pick the one on the right
            Ok(i) => i + 1,

            // found an insertion point -> link on that index is what we want
            Err(i) => i,
        };
        if index >= self.links.len() {
            // target_index is greater than the content length
            return None;
        }
        let prev_limit = if index == 0 {
            0
        } else {
            self.links[index - 1].limit
        };
        let limit = self.links[index].limit;
        let stated_content_length = limit - prev_limit;
        let local_index = target_index - prev_limit;

        Some((index, local_index, stated_content_length))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::LINK_SIZE;

    fn encode_block_header(block_type: u8, size: u16) -> [u8; 2] {
        let parameters = block_type << 1;
        let raw = (parameters as u16) << 13 | (size & 0x1FFF);
        raw.to_le_bytes()
    }

    fn make_link(digest_byte: u8, limit: u32) -> Vec<u8> {
        let mut link = vec![digest_byte; 32];
        link.extend_from_slice(&limit.to_le_bytes());
        link
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
    fn test_links_single() {
        let size = 4 + LINK_SIZE;
        let mut raw = Vec::new();
        raw.extend_from_slice(&encode_block_header(0b11, size as u16));
        raw.extend_from_slice(&0u16.to_le_bytes());
        raw.extend(make_link(0xAA, 100));

        let (buf, off) = make_aligned(&raw);
        let block_data = BlockData::new_from_prefix(&buf[off..]).unwrap();
        let block = LinksBlock::parse(block_data).unwrap();
        assert_eq!(block.len(), 1);
        assert_eq!(block.content_length(), 100);

        let link = &block.links()[0];
        assert_eq!(link.digest, [0xAA; 32]);
        assert_eq!(link.limit, 100);
    }

    #[test]
    fn test_links_multiple() {
        let size = 4 + 3 * LINK_SIZE;
        let mut raw = Vec::new();
        raw.extend_from_slice(&encode_block_header(0b11, size as u16));
        raw.extend_from_slice(&0u16.to_le_bytes());
        raw.extend(make_link(0x01, 100));
        raw.extend(make_link(0x02, 200));
        raw.extend(make_link(0x03, 321));

        let (buf, off) = make_aligned(&raw);
        let block_data = BlockData::new_from_prefix(&buf[off..]).unwrap();
        let block = LinksBlock::parse(block_data).unwrap();
        assert_eq!(block.len(), 3);
        assert_eq!(block.content_length(), 321);
    }

    #[test]
    fn test_links_find_index() {
        let size = 4 + 3 * LINK_SIZE;
        let mut raw = Vec::new();
        raw.extend_from_slice(&encode_block_header(0b11, size as u16));
        raw.extend_from_slice(&0u16.to_le_bytes());
        raw.extend(make_link(0x01, 100));
        raw.extend(make_link(0x02, 200));
        raw.extend(make_link(0x03, 321));

        let (buf, off) = make_aligned(&raw);
        let block_data = BlockData::new_from_prefix(&buf[off..]).unwrap();
        let block = LinksBlock::parse(block_data).unwrap();

        assert_eq!(block.find_link_for_index(0), Some((0, 0, 100)));
        assert_eq!(block.find_link_for_index(99), Some((0, 99, 100)));
        assert_eq!(block.find_link_for_index(100), Some((1, 0, 100)));
        assert_eq!(block.find_link_for_index(199), Some((1, 99, 100)));
        assert_eq!(block.find_link_for_index(200), Some((2, 0, 121)));
        assert_eq!(block.find_link_for_index(320), Some((2, 120, 121)));
        assert_eq!(block.find_link_for_index(321), None);
    }

    #[test]
    fn test_links_rejects_non_increasing_limits() {
        let size = 4 + 2 * LINK_SIZE;
        let mut raw = Vec::new();
        raw.extend_from_slice(&encode_block_header(0b11, size as u16));
        raw.extend_from_slice(&0u16.to_le_bytes());
        raw.extend(make_link(0x01, 100));
        raw.extend(make_link(0x02, 50));

        let (buf, off) = make_aligned(&raw);
        let block_data = BlockData::new_from_prefix(&buf[off..]).unwrap();
        assert_eq!(
            LinksBlock::parse(block_data).err().unwrap(),
            CodecError::InvalidValue
        );
    }

    #[test]
    fn test_links_rejects_nonzero_reserved() {
        let size = 4 + LINK_SIZE;
        let mut raw = Vec::new();
        raw.extend_from_slice(&encode_block_header(0b11, size as u16));
        raw.extend_from_slice(&1u16.to_le_bytes());
        raw.extend(make_link(0x01, 100));

        let (buf, off) = make_aligned(&raw);
        let block_data = BlockData::new_from_prefix(&buf[off..]).unwrap();
        assert_eq!(
            LinksBlock::parse(block_data).err().unwrap(),
            CodecError::InvalidValue
        );
    }

    #[test]
    fn test_links_rejects_wrong_data_size() {
        let size = 4 + 10;
        let mut raw = Vec::new();
        raw.extend_from_slice(&encode_block_header(0b11, size as u16));
        raw.extend_from_slice(&0u16.to_le_bytes());
        raw.extend_from_slice(&[0; 10]);

        let (buf, off) = make_aligned(&raw);
        let block_data = BlockData::new_from_prefix(&buf[off..]).unwrap();
        assert_eq!(
            LinksBlock::parse(block_data).err().unwrap(),
            CodecError::InvalidBlock
        );
    }
}
