//! DATA block: array of fixed-size elements.
//!
//! Layout: `[t16 header] [padding] [element 0] [padding] [element 1] ...`
//!
//! Elements are of uniform size and alignment. Padding ensures proper alignment
//! after the 2-byte header and between elements.

use super::{align_up, BlockData, BlockType, CodecError};

/// A parsed DATA block, borrowing from the input data.
///
/// Provides zero-copy access to array elements of a fixed schema-defined size.
#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
pub struct DataBlock<'a> {
    data: BlockData<'a>,
    elem_size: usize,
    elem_align: usize,
}

impl<'a> DataBlock<'a> {
    /// Parse a DATA block from `data`.
    pub fn parse(data: BlockData<'a>) -> Result<Self, CodecError> {
        let header = data.block_header();
        if header.block_type != BlockType::Data {
            return Err(CodecError::UnexpectedBlockType);
        }
        let t16_prefix = data.as_tagged16_prefix();
        if t16_prefix.len() < 2 {
            return Err(CodecError::OutOfBounds);
        }
        let elem_properties = t16_prefix[1];
        let elem_size = elem_properties.size();
        let elem_align = 1usize << elem_properties.params();
        if elem_size == 0 {
            return Err(CodecError::InvalidValue);
        }
        let new = Self {
            data,
            elem_size,
            elem_align,
        };
        let padded_elem_size = align_up(elem_size, elem_align);
        let start_offset = new.start_offset();
        if (data.len() - start_offset) % padded_elem_size != 0 {
            return Err(CodecError::OutOfBounds);
        }
        Ok(new)
    }

    const fn start_offset(&self) -> usize {
        align_up(4, self.elem_align)
    }

    pub fn data(&self) -> &'a [u8] {
        &self.data.0[self.start_offset()..]
    }

    pub fn as_slice<T: bytemuck::AnyBitPattern>(&self) -> Result<&'a [T], CodecError> {
        let padded_elem_size = align_up(self.elem_size, self.elem_align);
        if core::mem::size_of::<T>() != padded_elem_size
            || core::mem::align_of::<T>() > self.elem_align
        {
            return Err(CodecError::AlignmentError);
        }
        let data = self.data();
        Ok(bytemuck::cast_slice(data))
    }

    pub fn iter(&self) -> impl Iterator<Item = &'a [u8]> + '_ {
        let padded_elem_size = align_up(self.elem_size, self.elem_align);
        let data = self.data();
        data.chunks(padded_elem_size)
            .map(|chunk| &chunk[..self.elem_size])
    }
}

#[cfg(test)]
mod tests {
    use super::{
        super::{tests::BlockBuilder, *},
        *,
    };

    impl BlockBuilder {
        pub fn push_elem_params(&mut self, elem_size: usize, elem_align: usize) -> &mut Self {
            let params = Tagged16::new(elem_align.ilog2() as u8, elem_size).unwrap();
            self.push_t16(params);
            self
        }
    }

    #[test]
    fn test_data_block_u32_array() {
        // DATA block with 3 x u32 elements (align=4, elem_size=4)
        // start_offset = max(4, 2) = 4
        // So: header(4) + 3*4 = 16
        let size = 16;
        let mut builder = BlockBuilder::new_block(BlockType::Data, size).unwrap();
        builder
            .push_elem_params(4, 4)
            .extend_from_slice(&10u32.to_le_bytes())
            .extend_from_slice(&20u32.to_le_bytes())
            .extend_from_slice(&30u32.to_le_bytes());
        let block_data = builder.to_block_data().unwrap();
        let block = DataBlock::parse(block_data).unwrap();
        let array = block.as_slice::<u32>().unwrap();
        assert_eq!(array, &[10u32, 20u32, 30u32]);
    }

    #[test]
    fn test_data_block_u8_array() {
        // DATA block with 4 x u8 elements (align=1, elem_size=1)
        // So: header(4) + 4*1 = 6
        let size = 8;
        let mut builder = BlockBuilder::new_block(BlockType::Data, size).unwrap();
        builder
            .push_elem_params(1, 1)
            .extend_from_slice(&[1, 2, 3, 4]);

        let block_data = builder.to_block_data().unwrap();
        let block = DataBlock::parse(block_data).unwrap();
        let array = block.as_slice::<u8>().unwrap();
        assert_eq!(array, &[1, 2, 3, 4]);
    }

    #[test]
    fn test_data_block_u16_array() {
        // DATA block with 2 x u16 elements (align=2, elem_size=2)
        // start_offset = max(2, 2) = 2
        // So: header(4) + 2*2 = 8
        let size = 8;
        let mut builder = BlockBuilder::new_block(BlockType::Data, size).unwrap();
        builder
            .push_elem_params(2, 2)
            .extend_from_slice(&100u16.to_le_bytes())
            .extend_from_slice(&200u16.to_le_bytes());
        let block_data = builder.to_block_data().unwrap();
        let block = DataBlock::parse(block_data).unwrap();
        let array = block.as_slice::<u16>().unwrap();
        assert_eq!(array, &[100u16, 200u16]);
    }

    #[test]
    fn test_data_block_u64_array() {
        // DATA block with 5 x u64 elements (align=8, elem_size=8)
        // So: header(4) + padding(4) + 5*8 = 48
        let size = 48;
        let expected = [100u64, 200u64, 300u64, 400u64, 500u64];
        let mut builder = BlockBuilder::new_block(BlockType::Data, size).unwrap();
        // add padding to align the block to 8 bytes
        builder.push_elem_params(8, 8).extend_from_slice(&[0u8; 4]);
        for &value in &expected {
            builder.extend_from_slice(&value.to_le_bytes());
        }

        let block_data = builder.to_block_data().unwrap();
        let block = DataBlock::parse(block_data).unwrap();
        let array = block.as_slice::<u64>().unwrap();
        assert_eq!(array, &expected);
    }

    #[test]
    fn test_data_block_empty() {
        // Empty DATA block: just header, size=4
        let size = 4;
        let mut builder = BlockBuilder::new_block(BlockType::Data, size).unwrap();
        builder.push_elem_params(1, 1);

        let block_data = builder.to_block_data().unwrap();
        let block = DataBlock::parse(block_data).unwrap();
        let array = block.as_slice::<u8>().unwrap();
        assert_eq!(array.len(), 0);
    }

    #[test]
    fn test_data_block_empty_with_align() {
        // Empty DATA block with align=8: size = start_offset = 8
        let size = 8;
        let mut builder = BlockBuilder::new_block(BlockType::Data, size).unwrap();
        builder.push_elem_params(8, 8);

        let block_data = builder.to_block_data().unwrap();
        let block = DataBlock::parse(block_data).unwrap();
        let array = block.as_slice::<u64>().unwrap();
        assert_eq!(array, &[] as &[u64]);
    }

    #[test]
    fn test_data_block_iter() {
        // element = u8
        // count = 4
        // padded_elem_size = align_up(1, 1) = 1
        // total size = header(4) + 4*1 = 8
        let size = 8;
        let array = [1, 2, 3, 4];
        let mut builder = BlockBuilder::new_block(BlockType::Data, size).unwrap();
        builder.push_elem_params(1, 1).extend_from_slice(&array);
        for elem in array {
            builder.extend_from_slice(&elem.to_le_bytes());
        }

        let block_data = builder.to_block_data().unwrap();
        let block = DataBlock::parse(block_data).unwrap();
        let array = block.iter().collect::<Vec<&[u8]>>();
        assert_eq!(array, &[&[1], &[2], &[3], &[4]]);
    }

    #[derive(Copy, Clone, PartialEq, Eq, Debug, bytemuck::AnyBitPattern)]
    struct Tuple3(u32, u32, u32);

    #[test]
    fn test_custom_elem_size() {
        // element = 3xu32
        // count = 3
        // total size = header(4) + 3*(3*4) = 40

        let array = [
            Tuple3(1u32, 2u32, 3u32),
            Tuple3(4u32, 5u32, 6u32),
            Tuple3(7u32, 8u32, 9u32),
        ];
        let size = 40;
        let mut builder = BlockBuilder::new_block(BlockType::Data, size).unwrap();
        builder.push_elem_params(12, 4);
        for Tuple3(a, b, c) in &array {
            builder
                .extend_from_slice(&a.to_le_bytes())
                .extend_from_slice(&b.to_le_bytes())
                .extend_from_slice(&c.to_le_bytes());
        }

        let block_data = builder.to_block_data().unwrap();
        let block = DataBlock::parse(block_data).unwrap();

        let decoded = block.as_slice::<Tuple3>().unwrap();
        assert_eq!(decoded, &array);
    }

    #[derive(Copy, Clone, PartialEq, Eq, Debug, bytemuck::AnyBitPattern)]
    struct Tuple3Het(u32, u32, u8);

    #[test]
    fn test_irregular_elem_size() {
        // element = 2xu32 + 1u8
        // count = 3
        // oadded_elem_size = align_up(2*4 + 1, 4) = 12
        // total size = header(4) + 3*12 = 40
        let size = 40;

        let array = [
            Tuple3Het(1u32, 2u32, 3u8),
            Tuple3Het(4u32, 5u32, 6u8),
            Tuple3Het(7u32, 8u32, 9u8),
        ];

        let mut builder = BlockBuilder::new_block(BlockType::Data, size).unwrap();
        builder.push_elem_params(4 + 4 + 1, 4);
        for Tuple3Het(a, b, c) in &array {
            builder
                .extend_from_slice(&a.to_le_bytes())
                .extend_from_slice(&b.to_le_bytes())
                .extend_from_slice(&c.to_le_bytes())
                .extend_from_slice(&[0u8; 3]);
        }
        let block_data = builder.to_block_data().unwrap();
        let block = DataBlock::parse(block_data).unwrap();
        let decoded = block.as_slice::<Tuple3Het>().unwrap();
        assert_eq!(decoded, &array);
    }
}
