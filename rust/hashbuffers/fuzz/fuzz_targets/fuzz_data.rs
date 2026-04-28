#![no_main]

use libfuzzer_sys::fuzz_target;

use hashbuffers::{BlockData, DataBlock};

fuzz_target!(|data: &[u8]| {
    let mut buf = vec![0u64; (data.len() + 7) / 8];
    let bytes: &mut [u8] = bytemuck::cast_slice_mut(&mut buf);
    let len = data.len().min(bytes.len());
    bytes[..len].copy_from_slice(&data[..len]);
    let aligned = &bytes[..len];

    let Ok(block_data) = BlockData::new_from_prefix(aligned) else {
        return;
    };
    let Ok(data_block) = DataBlock::parse(block_data) else {
        return;
    };

    // Exercise iteration
    for elem in data_block.iter() {
        let _ = elem.len();
    }

    // Try casting to various typed slices
    let _ = data_block.as_slice::<u8>();
    let _ = data_block.as_slice::<u16>();
    let _ = data_block.as_slice::<u32>();
    let _ = data_block.as_slice::<u64>();

    // Access raw data
    let _ = data_block.data();
});
