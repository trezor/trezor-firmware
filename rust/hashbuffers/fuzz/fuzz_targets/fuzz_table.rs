#![no_main]

use libfuzzer_sys::fuzz_target;

use hashbuffers::{BlockData, TableBlock};

fuzz_target!(|data: &[u8]| {
    let mut buf = vec![0u64; (data.len() + 7) / 8];
    let bytes: &mut [u8] = bytemuck::cast_slice_mut(&mut buf);
    let len = data.len().min(bytes.len());
    bytes[..len].copy_from_slice(&data[..len]);
    let aligned = &bytes[..len];

    let Ok(block_data) = BlockData::new_from_prefix(aligned) else {
        return;
    };
    let Ok(table) = TableBlock::parse(block_data) else {
        return;
    };

    // Exercise all typed accessors on every entry
    for i in 0..table.len().min(256) {
        let entry = table.get_entry(i);
        let _ = entry.entry_type();
        let _ = entry.is_null();
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
    // Also try out-of-bounds access
    let _ = table.get_u32(table.len());
    let _ = table.get_u32(table.len() + 1);
    let _ = table.get_block_or_link(table.len());
});
