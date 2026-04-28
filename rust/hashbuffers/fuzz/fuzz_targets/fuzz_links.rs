#![no_main]

use libfuzzer_sys::fuzz_target;

use hashbuffers::{BlockData, LinksBlock};

fuzz_target!(|data: &[u8]| {
    let mut buf = vec![0u64; (data.len() + 7) / 8];
    let bytes: &mut [u8] = bytemuck::cast_slice_mut(&mut buf);
    let len = data.len().min(bytes.len());
    bytes[..len].copy_from_slice(&data[..len]);
    let aligned = &bytes[..len];

    let Ok(block_data) = BlockData::new_from_prefix(aligned) else {
        return;
    };
    let Ok(links) = LinksBlock::parse(block_data) else {
        return;
    };

    let _ = links.len();
    let _ = links.content_length();
    let _ = links.links();

    // Exercise index lookup at various points
    if links.content_length() > 0 {
        let cl = links.content_length();
        let _ = links.find_link_for_index(0);
        let _ = links.find_link_for_index(cl - 1);
        let _ = links.find_link_for_index(cl);
        let _ = links.find_link_for_index(cl / 2);
        // Try every boundary
        for link in links.links() {
            if link.limit > 0 {
                let _ = links.find_link_for_index(link.limit - 1);
            }
            let _ = links.find_link_for_index(link.limit);
        }
    }
});
