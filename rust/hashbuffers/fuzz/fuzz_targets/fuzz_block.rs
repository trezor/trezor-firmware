#![no_main]

use libfuzzer_sys::fuzz_target;

use hashbuffers::{BlockData, DataBlock, LinksBlock, SlotsBlock, TableBlock};

/// Align data to 8 bytes and try parsing as a generic block, then dispatch
/// to the appropriate typed parser.
fn do_fuzz(data: &[u8]) {
    // Align input to 8 (maximum alignment any block needs).
    let mut buf = vec![0u64; (data.len() + 7) / 8];
    let bytes: &mut [u8] = bytemuck::cast_slice_mut(&mut buf);
    let len = data.len().min(bytes.len());
    bytes[..len].copy_from_slice(&data[..len]);
    let aligned = &bytes[..len];

    let Ok(block_data) = BlockData::new_from_prefix(aligned) else {
        return;
    };

    // Try each typed parser — they should all either succeed or return
    // a clean error, never panic.
    let _ = TableBlock::parse(block_data);
    let _ = DataBlock::parse(block_data);
    let _ = SlotsBlock::parse(block_data);
    let _ = LinksBlock::parse(block_data);

    // If it parses as a table, exercise accessors
    if let Ok(table) = TableBlock::parse(block_data) {
        for i in 0..table.len() {
            let _ = table.get_u8(i);
            let _ = table.get_u16(i);
            let _ = table.get_u32(i);
            let _ = table.get_u64(i);
            let _ = table.get_i8(i);
            let _ = table.get_i16(i);
            let _ = table.get_i32(i);
            let _ = table.get_i64(i);
            let _ = table.get_f32(i);
            let _ = table.get_f64(i);
            let _ = table.get_direct_data(i);
            let _ = table.get_block_or_link(i);
        }
    }

    // If it parses as data, exercise iteration
    if let Ok(data_block) = DataBlock::parse(block_data) {
        for elem in data_block.iter() {
            let _ = elem;
        }
        let _ = data_block.as_slice::<u8>();
        let _ = data_block.as_slice::<u16>();
        let _ = data_block.as_slice::<u32>();
        let _ = data_block.as_slice::<u64>();
    }

    // If it parses as slots, exercise element access
    if let Ok(slots) = SlotsBlock::parse(block_data) {
        for i in 0..slots.len() {
            let _ = slots.get_element(i);
        }
        for elem in slots.iter_elements() {
            let _ = elem;
        }
    }

    // If it parses as links, exercise index lookup
    if let Ok(links) = LinksBlock::parse(block_data) {
        if links.content_length() > 0 {
            let _ = links.find_link_for_index(0);
            let _ = links.find_link_for_index(links.content_length() - 1);
            let _ = links.find_link_for_index(links.content_length());
            let _ = links.find_link_for_index(links.content_length() / 2);
        }
    }
}

fuzz_target!(|data: &[u8]| {
    do_fuzz(data);
});
