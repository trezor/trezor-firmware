#![no_main]

use libfuzzer_sys::fuzz_target;

use hashbuffers::{BlockData, SlotsBlock};

fuzz_target!(|data: &[u8]| {
    let mut buf = vec![0u64; (data.len() + 7) / 8];
    let bytes: &mut [u8] = bytemuck::cast_slice_mut(&mut buf);
    let len = data.len().min(bytes.len());
    bytes[..len].copy_from_slice(&data[..len]);
    let aligned = &bytes[..len];

    let Ok(block_data) = BlockData::new_from_prefix(aligned) else {
        return;
    };
    let Ok(slots) = SlotsBlock::parse(block_data) else {
        return;
    };

    // Exercise element access
    for i in 0..slots.len() {
        let elem = slots.get_element(i);
        if let Some(e) = elem {
            let _ = e.len();
        }
    }
    // Out of bounds
    let _ = slots.get_element(slots.len());

    // Iterator
    for elem in slots.iter_elements() {
        let _ = elem.len();
    }
});
