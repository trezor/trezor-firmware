#!/usr/bin/env -S cargo +nightly -Zscript
//! Generate seed corpus files for hashbuffers fuzzing.
//! Run with: rustc generate_seeds.rs && ./generate_seeds

use std::fs;

fn encode_header(block_type: u8, size: u16) -> [u8; 2] {
    let params = block_type << 1;
    let raw = (params as u16) << 13 | (size & 0x1FFF);
    raw.to_le_bytes()
}

fn t16(params: u8, number: u16) -> [u8; 2] {
    let raw = ((params as u16) << 13) | (number & 0x1FFF);
    raw.to_le_bytes()
}

fn make_link(digest_byte: u8, limit: u32) -> Vec<u8> {
    let mut link = vec![digest_byte; 32];
    link.extend_from_slice(&limit.to_le_bytes());
    link
}

fn main() {
    // --- TABLE seeds ---
    // Empty table (size=4)
    let mut v = Vec::new();
    v.extend_from_slice(&encode_header(0b00, 4));
    v.extend_from_slice(&t16(0, 0));
    fs::write("corpus/table/empty_table", &v).unwrap();
    fs::write("corpus/block/empty_table", &v).unwrap();

    // Table with inline entries
    let entry_count = 3u16;
    let size = 4 + 2 * entry_count;
    let mut v = Vec::new();
    v.extend_from_slice(&encode_header(0b00, size));
    v.extend_from_slice(&t16(0, entry_count));
    v.extend_from_slice(&t16(0b000, 0)); // NULL
    v.extend_from_slice(&t16(0b100, 42)); // INLINE 42
    v.extend_from_slice(&t16(0b100, 100)); // INLINE 100
    fs::write("corpus/table/inline_entries", &v).unwrap();
    fs::write("corpus/block/table_inline", &v).unwrap();

    // Table with DIRECT4
    let entry_count = 1u16;
    let heap_start = (4 + 2 * entry_count) as usize;
    let value_offset = (heap_start + 3) & !3; // align to 4
    let padding = value_offset - heap_start;
    let size = (value_offset + 4) as u16;
    let mut v = Vec::new();
    v.extend_from_slice(&encode_header(0b00, size));
    v.extend_from_slice(&t16(0, entry_count));
    v.extend_from_slice(&t16(0b010, value_offset as u16)); // DIRECT4
    v.extend(vec![0u8; padding]);
    v.extend_from_slice(&0x12345678u32.to_le_bytes());
    fs::write("corpus/table/direct4", &v).unwrap();
    fs::write("corpus/block/table_direct4", &v).unwrap();

    // Table with DIRECT8
    let entry_count = 1u16;
    let heap_start = (4 + 2 * entry_count) as usize;
    let value_offset = (heap_start + 7) & !7; // align to 8
    let padding = value_offset - heap_start;
    let size = (value_offset + 8) as u16;
    let mut v = Vec::new();
    v.extend_from_slice(&encode_header(0b00, size));
    v.extend_from_slice(&t16(0, entry_count));
    v.extend_from_slice(&t16(0b011, value_offset as u16)); // DIRECT8
    v.extend(vec![0u8; padding]);
    v.extend_from_slice(&0xDEADBEEFCAFEBABEu64.to_le_bytes());
    fs::write("corpus/table/direct8", &v).unwrap();
    fs::write("corpus/block/table_direct8", &v).unwrap();

    // Table with DIRECTDATA (bytestring "hello")
    let entry_count = 1u16;
    let heap_start = (4 + 2 * entry_count) as usize;
    let dd_offset = heap_start; // align=2, heap_start is always even
    let dd_data = b"hello";
    let size = (dd_offset + 2 + dd_data.len()) as u16;
    let mut v = Vec::new();
    v.extend_from_slice(&encode_header(0b00, size));
    v.extend_from_slice(&t16(0, entry_count));
    v.extend_from_slice(&t16(0b001, dd_offset as u16)); // DIRECTDATA
    v.extend_from_slice(&t16(0, dd_data.len() as u16)); // header: align_power=0, length
    v.extend_from_slice(dd_data);
    fs::write("corpus/table/directdata", &v).unwrap();
    fs::write("corpus/block/table_directdata", &v).unwrap();

    // Table with sub-block (inner empty table)
    let inner_size = 4u16;
    let entry_count = 1u16;
    let heap_start = 4 + 2 * entry_count;
    let block_offset = heap_start;
    let outer_size = block_offset + inner_size;
    let mut v = Vec::new();
    v.extend_from_slice(&encode_header(0b00, outer_size));
    v.extend_from_slice(&t16(0, entry_count));
    v.extend_from_slice(&t16(0b101, block_offset)); // BLOCK
    v.extend_from_slice(&encode_header(0b00, inner_size)); // inner table header
    v.extend_from_slice(&t16(0, 0)); // inner: 0 entries
    fs::write("corpus/table/sub_block", &v).unwrap();
    fs::write("corpus/block/table_sub_block", &v).unwrap();

    // Table with LINK
    let entry_count = 1u16;
    let heap_start = (4 + 2 * entry_count) as usize;
    let link_offset = (heap_start + 3) & !3; // align to 4
    let padding = link_offset - heap_start;
    let size = (link_offset + 36) as u16;
    let mut v = Vec::new();
    v.extend_from_slice(&encode_header(0b00, size));
    v.extend_from_slice(&t16(0, entry_count));
    v.extend_from_slice(&t16(0b110, link_offset as u16)); // LINK
    v.extend(vec![0u8; padding]);
    v.extend_from_slice(&[0xAA; 32]); // digest
    v.extend_from_slice(&42u32.to_le_bytes()); // limit
    fs::write("corpus/table/link_entry", &v).unwrap();
    fs::write("corpus/block/table_link", &v).unwrap();

    // Table with mixed entries
    let entry_count = 5u16;
    let heap_start = (4 + 2 * entry_count) as usize; // 14
    // DIRECTDATA at 14, DIRECT4 at 14+2+3=19->20, LINK at 24
    let dd_offset = heap_start;
    let dd_data = b"hi";
    let d4_offset = (dd_offset + 2 + dd_data.len() + 3) & !3;
    let link_offset = d4_offset + 4;
    let size = link_offset + 36;
    let mut v = Vec::new();
    v.extend_from_slice(&encode_header(0b00, size as u16));
    v.extend_from_slice(&t16(0, entry_count));
    v.extend_from_slice(&t16(0b000, 0)); // NULL
    v.extend_from_slice(&t16(0b100, 7)); // INLINE 7
    v.extend_from_slice(&t16(0b001, dd_offset as u16)); // DIRECTDATA
    v.extend_from_slice(&t16(0b010, d4_offset as u16)); // DIRECT4
    v.extend_from_slice(&t16(0b110, link_offset as u16)); // LINK
    // heap
    v.extend_from_slice(&t16(0, dd_data.len() as u16)); // DD header
    v.extend_from_slice(dd_data);
    v.resize(d4_offset, 0); // padding
    v.extend_from_slice(&999u32.to_le_bytes());
    v.extend_from_slice(&[0xCC; 32]); // link digest
    v.extend_from_slice(&10u32.to_le_bytes()); // link limit
    fs::write("corpus/table/mixed", &v).unwrap();
    fs::write("corpus/block/table_mixed", &v).unwrap();

    // --- DATA seeds ---
    // u8 array [1,2,3,4]
    let size = 8u16; // header(4) + 4 bytes
    let mut v = Vec::new();
    v.extend_from_slice(&encode_header(0b01, size));
    v.extend_from_slice(&t16(0, 1)); // align_power=0, elem_size=1
    v.extend_from_slice(&[1, 2, 3, 4]);
    fs::write("corpus/data/u8_array", &v).unwrap();
    fs::write("corpus/block/data_u8", &v).unwrap();

    // u16 array [100, 200]
    let size = 8u16;
    let mut v = Vec::new();
    v.extend_from_slice(&encode_header(0b01, size));
    v.extend_from_slice(&t16(1, 2)); // align_power=1, elem_size=2
    v.extend_from_slice(&100u16.to_le_bytes());
    v.extend_from_slice(&200u16.to_le_bytes());
    fs::write("corpus/data/u16_array", &v).unwrap();
    fs::write("corpus/block/data_u16", &v).unwrap();

    // u32 array [10, 20, 30]
    let size = 16u16;
    let mut v = Vec::new();
    v.extend_from_slice(&encode_header(0b01, size));
    v.extend_from_slice(&t16(2, 4)); // align_power=2, elem_size=4
    v.extend_from_slice(&10u32.to_le_bytes());
    v.extend_from_slice(&20u32.to_le_bytes());
    v.extend_from_slice(&30u32.to_le_bytes());
    fs::write("corpus/data/u32_array", &v).unwrap();
    fs::write("corpus/block/data_u32", &v).unwrap();

    // u64 array [100, 200]
    let size = 24u16; // header(4) + padding(4) + 2*8
    let mut v = Vec::new();
    v.extend_from_slice(&encode_header(0b01, size));
    v.extend_from_slice(&t16(3, 8)); // align_power=3, elem_size=8
    v.extend(vec![0u8; 4]); // padding to align to 8
    v.extend_from_slice(&100u64.to_le_bytes());
    v.extend_from_slice(&200u64.to_le_bytes());
    fs::write("corpus/data/u64_array", &v).unwrap();
    fs::write("corpus/block/data_u64", &v).unwrap();

    // Empty DATA
    let mut v = Vec::new();
    v.extend_from_slice(&encode_header(0b01, 4));
    v.extend_from_slice(&t16(0, 1)); // elem_size=1, align=1
    fs::write("corpus/data/empty", &v).unwrap();
    fs::write("corpus/block/data_empty", &v).unwrap();

    // --- SLOTS seeds ---
    // Empty slots (size=4, sentinel=4)
    let mut v = Vec::new();
    v.extend_from_slice(&encode_header(0b10, 4));
    v.extend_from_slice(&4u16.to_le_bytes());
    fs::write("corpus/slots/empty", &v).unwrap();
    fs::write("corpus/block/slots_empty", &v).unwrap();

    // One element "hello"
    let heap_start = 6u16; // header(2) + offset(2) + sentinel(2)
    let elem = b"hello";
    let size = heap_start + elem.len() as u16;
    let mut v = Vec::new();
    v.extend_from_slice(&encode_header(0b10, size));
    v.extend_from_slice(&heap_start.to_le_bytes());
    v.extend_from_slice(&size.to_le_bytes());
    v.extend_from_slice(elem);
    fs::write("corpus/slots/one_elem", &v).unwrap();
    fs::write("corpus/block/slots_one", &v).unwrap();

    // Three elements
    let heap_start = 10u16; // header(2) + 3 offsets(6) + sentinel(2) -- wait
    // offsets: off0, off1, off2, sentinel = 4 offsets, each 2 bytes = 8 + header 2 = 10
    let e0 = b"ab";
    let e1 = b"cde";
    let e2 = b"f";
    let off0 = heap_start;
    let off1 = off0 + e0.len() as u16;
    let off2 = off1 + e1.len() as u16;
    let sentinel = off2 + e2.len() as u16;
    let mut v = Vec::new();
    v.extend_from_slice(&encode_header(0b10, sentinel));
    v.extend_from_slice(&off0.to_le_bytes());
    v.extend_from_slice(&off1.to_le_bytes());
    v.extend_from_slice(&off2.to_le_bytes());
    v.extend_from_slice(&sentinel.to_le_bytes());
    v.extend_from_slice(e0);
    v.extend_from_slice(e1);
    v.extend_from_slice(e2);
    fs::write("corpus/slots/three_elems", &v).unwrap();
    fs::write("corpus/block/slots_three", &v).unwrap();

    // One empty element
    let heap_start = 6u16;
    let mut v = Vec::new();
    v.extend_from_slice(&encode_header(0b10, heap_start));
    v.extend_from_slice(&heap_start.to_le_bytes());
    v.extend_from_slice(&heap_start.to_le_bytes());
    fs::write("corpus/slots/empty_elem", &v).unwrap();
    fs::write("corpus/block/slots_empty_elem", &v).unwrap();

    // --- LINKS seeds ---
    // Single link
    let size = (4 + 36) as u16;
    let mut v = Vec::new();
    v.extend_from_slice(&encode_header(0b11, size));
    v.extend_from_slice(&0u16.to_le_bytes()); // depth=0, reserved=0
    v.extend(make_link(0xAA, 100));
    fs::write("corpus/links/single", &v).unwrap();
    fs::write("corpus/block/links_single", &v).unwrap();

    // Three links
    let size = (4 + 3 * 36) as u16;
    let mut v = Vec::new();
    v.extend_from_slice(&encode_header(0b11, size));
    v.extend_from_slice(&0u16.to_le_bytes());
    v.extend(make_link(0x01, 100));
    v.extend(make_link(0x02, 200));
    v.extend(make_link(0x03, 321));
    fs::write("corpus/links/three", &v).unwrap();
    fs::write("corpus/block/links_three", &v).unwrap();

    // Two links (minimum valid)
    let size = (4 + 2 * 36) as u16;
    let mut v = Vec::new();
    v.extend_from_slice(&encode_header(0b11, size));
    v.extend_from_slice(&0u16.to_le_bytes());
    v.extend(make_link(0xFF, 50));
    v.extend(make_link(0xEE, 100));
    fs::write("corpus/links/two_min", &v).unwrap();
    fs::write("corpus/block/links_two", &v).unwrap();

    // --- Edge cases for block corpus ---
    // Minimum size block (2 bytes) — should fail all typed parsers but not panic
    let mut v = Vec::new();
    v.extend_from_slice(&encode_header(0b00, 2));
    fs::write("corpus/block/min_size", &v).unwrap();

    // All zeros
    fs::write("corpus/block/zeros_4", &[0u8; 4]).unwrap();
    fs::write("corpus/block/zeros_8", &[0u8; 8]).unwrap();
    fs::write("corpus/block/zeros_64", &[0u8; 64]).unwrap();

    // All 0xFF
    fs::write("corpus/block/ones_4", &[0xFFu8; 4]).unwrap();
    fs::write("corpus/block/ones_64", &[0xFFu8; 64]).unwrap();

    // Near-max block
    let mut v = Vec::new();
    v.extend_from_slice(&encode_header(0b01, 8190)); // just under SIZE_MAX
    v.extend_from_slice(&t16(0, 1));
    v.resize(8190, 0x42);
    fs::write("corpus/block/near_max_data", &v).unwrap();
    fs::write("corpus/data/near_max", &v).unwrap();

    println!("Seed corpus generated successfully!");
}
