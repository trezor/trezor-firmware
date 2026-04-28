//! Replay fuzzer corpus files under Miri to check for undefined behavior.
//!
//! Run with: cargo +nightly miri test --test miri_corpus

use hashbuffers::{BlockData, DataBlock, LinksBlock, SlotsBlock, TableBlock};
use std::path::Path;

/// An aligned buffer that we can borrow BlockData from.
struct AlignedBuf {
    buf: Vec<u64>,
    len: usize,
}

impl AlignedBuf {
    fn from_slice(data: &[u8]) -> Self {
        let mut buf = vec![0u64; (data.len() + 7) / 8];
        let bytes: &mut [u8] = bytemuck::cast_slice_mut(&mut buf);
        let len = data.len().min(bytes.len());
        bytes[..len].copy_from_slice(&data[..len]);
        Self { buf, len }
    }

    fn as_bytes(&self) -> &[u8] {
        let bytes: &[u8] = bytemuck::cast_slice(&self.buf);
        &bytes[..self.len]
    }
}

fn exercise_table(block_data: BlockData<'_>) {
    let Ok(table) = TableBlock::parse(block_data) else {
        return;
    };
    for i in 0..table.len() {
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
    let _ = table.get_u32(table.len());
    let _ = table.get_block_or_link(table.len());
}

fn exercise_data(block_data: BlockData<'_>) {
    let Ok(data_block) = DataBlock::parse(block_data) else {
        return;
    };
    for elem in data_block.iter() {
        let _ = elem.len();
    }
    let _ = data_block.as_slice::<u8>();
    let _ = data_block.as_slice::<u16>();
    let _ = data_block.as_slice::<u32>();
    let _ = data_block.as_slice::<u64>();
    let _ = data_block.data();
}

fn exercise_slots(block_data: BlockData<'_>) {
    let Ok(slots) = SlotsBlock::parse(block_data) else {
        return;
    };
    for i in 0..slots.len() {
        if let Some(e) = slots.get_element(i) {
            let _ = e.len();
        }
    }
    let _ = slots.get_element(slots.len());
    for elem in slots.iter_elements() {
        let _ = elem.len();
    }
}

fn exercise_links(block_data: BlockData<'_>) {
    let Ok(links) = LinksBlock::parse(block_data) else {
        return;
    };
    let _ = links.len();
    let _ = links.content_length();
    let _ = links.links();
    if links.content_length() > 0 {
        let cl = links.content_length();
        let _ = links.find_link_for_index(0);
        let _ = links.find_link_for_index(cl - 1);
        let _ = links.find_link_for_index(cl);
        let _ = links.find_link_for_index(cl / 2);
        for link in links.links() {
            if link.limit > 0 {
                let _ = links.find_link_for_index(link.limit - 1);
            }
            let _ = links.find_link_for_index(link.limit);
        }
    }
}

fn exercise_all(data: &[u8]) {
    let aligned = AlignedBuf::from_slice(data);
    let Ok(block_data) = BlockData::new_from_prefix(aligned.as_bytes()) else {
        return;
    };
    exercise_table(block_data);
    exercise_data(block_data);
    exercise_slots(block_data);
    exercise_links(block_data);
}

fn replay_corpus_dir(dir: &Path) {
    let Ok(entries) = std::fs::read_dir(dir) else {
        return;
    };
    let mut count = 0;
    for entry in entries {
        let entry = entry.unwrap();
        if !entry.file_type().unwrap().is_file() {
            continue;
        }
        let data = std::fs::read(entry.path()).unwrap();
        exercise_all(&data);
        count += 1;
    }
    eprintln!("  {}: {} files", dir.file_name().unwrap().to_str().unwrap(), count);
}

#[test]
fn replay_fuzz_corpus() {
    let fuzz_dir = Path::new(env!("CARGO_MANIFEST_DIR")).join("fuzz/corpus");
    if !fuzz_dir.exists() {
        eprintln!("No fuzz corpus found at {}", fuzz_dir.display());
        return;
    }
    let Ok(subdirs) = std::fs::read_dir(&fuzz_dir) else {
        return;
    };
    for entry in subdirs {
        let entry = entry.unwrap();
        if entry.file_type().unwrap().is_dir() {
            replay_corpus_dir(&entry.path());
        }
    }
}
