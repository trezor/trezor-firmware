#[cfg(not(test))]
use alloc::vec::Vec;
#[cfg(test)]
use std::vec::Vec;

pub const STRING_HEADER_BYTE: u8 = 0x80;
pub const LIST_HEADER_BYTE: u8 = 0xC0;

pub enum RLPItem<'a> {
    Int(u64),
    Bytes(&'a [u8]),
    List(Vec<RLPItem<'a>>),
}

/// Returns the minimum number of bytes needed to represent an unsigned integer
fn byte_size(x: u64) -> usize {
    for exp in 0..=8 {
        if x < 0x100_u64.pow(exp) {
            return exp as usize;
        }
    }
    8 // max 8 bytes for u64
}

/// Converts unsigned integer to big-endian bytes (minimal representation)
pub fn int_to_bytes(x: u64) -> Vec<u8> {
    let size = byte_size(x);
    x.to_be_bytes()[8 - size..].to_vec()
}

/// Calculates the length of the RLP header for given payload length
pub fn header_length(length: u32, data_start: Option<&[u8]>) -> u32 {
    // Special case: single byte < 0x80 has no header
    if length == 1 {
        if let Some(data) = data_start {
            if !data.is_empty() && data[0] <= 0x7F {
                return 0;
            }
        }
    }

    if length <= 55 {
        1
    } else {
        let encoded_length = int_to_bytes(length as u64);
        1 + encoded_length.len() as u32
    }
}

/// Calculates total RLP encoded length for an item
pub fn length(item: &RLPItem) -> u32 {
    match item {
        RLPItem::Int(x) => {
            let data = int_to_bytes(*x);
            header_length(data.len() as _, Some(&data)) + data.len() as u32
        }
        RLPItem::Bytes(bytes) => header_length(bytes.len() as _, Some(bytes)) + bytes.len() as u32,
        RLPItem::List(list) => {
            let payload_length: u32 = list.iter().map(length).sum();
            header_length(payload_length as _, None) + payload_length
        }
    }
}

/// Writes RLP header to the writer
pub fn write_header(w: &mut Vec<u8>, length: u32, header_byte: u8, data_start: Option<&[u8]>) {
    // Special case: single byte < 0x80 has no header
    if length == 1 {
        if let Some(data) = data_start {
            if !data.is_empty() && data[0] <= 0x7F {
                return;
            }
        }
    }

    if length <= 55 {
        w.push(header_byte + length as u8);
    } else {
        let encoded_length = int_to_bytes(length as u64);
        w.push(header_byte + 55 + encoded_length.len() as u8);
        w.extend_from_slice(&encoded_length);
    }
}

/// Writes a string (byte array) in RLP format
pub fn write_string(w: &mut Vec<u8>, string: &[u8]) {
    write_header(w, string.len() as _, STRING_HEADER_BYTE, Some(string));
    w.extend_from_slice(string);
}

/// Writes a list in RLP format
pub fn write_list(w: &mut Vec<u8>, lst: &[RLPItem]) {
    let payload_length: u32 = lst.iter().map(length).sum();
    write_header(w, payload_length as _, LIST_HEADER_BYTE, None);
    for item in lst {
        write(w, item);
    }
}

/// Writes an RLP item to the writer
pub fn write(w: &mut Vec<u8>, item: &RLPItem) {
    match item {
        RLPItem::Int(x) => {
            write_string(w, &int_to_bytes(*x));
        }
        RLPItem::Bytes(bytes) => {
            write_string(w, bytes);
        }
        RLPItem::List(list) => {
            write_list(w, list);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_string_dog() {
        let mut w = Vec::new();
        write_string(&mut w, b"dog");
        assert_eq!(w, vec![0x83, b'd', b'o', b'g']);
    }

    #[test]
    fn test_list_cat_dog() {
        let mut w = Vec::new();
        let items = vec![RLPItem::Bytes(b"cat"), RLPItem::Bytes(b"dog")];
        write_list(&mut w, &items);
        assert_eq!(
            w,
            vec![0xc8, 0x83, b'c', b'a', b't', 0x83, b'd', b'o', b'g']
        );
    }

    #[test]
    fn test_empty_string() {
        let mut w = Vec::new();
        write_string(&mut w, b"");
        assert_eq!(w, vec![0x80]);
    }

    #[test]
    fn test_empty_list() {
        let mut w = Vec::new();
        write_list(&mut w, &[]);
        assert_eq!(w, vec![0xc0]);
    }

    #[test]
    fn test_integer_0() {
        let mut w = Vec::new();
        write(&mut w, &RLPItem::Int(0));
        assert_eq!(w, vec![0x80]);
    }

    #[test]
    fn test_byte_0x00() {
        let mut w = Vec::new();
        write_string(&mut w, &[0x00]);
        assert_eq!(w, vec![0x00]);
    }

    #[test]
    fn test_byte_0x0f() {
        let mut w = Vec::new();
        write_string(&mut w, &[0x0f]);
        assert_eq!(w, vec![0x0f]);
    }

    #[test]
    fn test_bytes_0x04_0x00() {
        let mut w = Vec::new();
        write_string(&mut w, &[0x04, 0x00]);
        assert_eq!(w, vec![0x82, 0x04, 0x00]);
    }

    #[test]
    fn test_nested_empty_lists() {
        // [ [], [[]], [ [], [[]] ] ]
        let mut w = Vec::new();
        let items = vec![
            RLPItem::List(vec![]),                      // []
            RLPItem::List(vec![RLPItem::List(vec![])]), // [[]]
            RLPItem::List(vec![
                RLPItem::List(vec![]),                      // []
                RLPItem::List(vec![RLPItem::List(vec![])]), // [[]]
            ]),
        ];
        write_list(&mut w, &items);
        assert_eq!(w, vec![0xc7, 0xc0, 0xc1, 0xc0, 0xc3, 0xc0, 0xc1, 0xc0]);
    }

    #[test]
    fn test_long_string() {
        let lorem = b"Lorem ipsum dolor sit amet, consectetur adipisicing elit";
        let mut w = Vec::new();
        write_string(&mut w, lorem);

        let mut expected = vec![0xb8, 0x38]; // 0xb8 = 0x80 + 55 + 1, 0x38 = 56 (length)
        expected.extend_from_slice(lorem);

        assert_eq!(w, expected);
        assert_eq!(lorem.len(), 56);
    }
}
