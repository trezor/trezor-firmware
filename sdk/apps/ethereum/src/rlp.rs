#[cfg(not(test))]
use alloc::vec::Vec;
use primitive_types::U256;
#[cfg(test)]
use std::vec;
#[cfg(test)]
use std::vec::Vec;

use trezor_app_sdk::crypto::Hasher;

pub const STRING_HEADER_BYTE: u8 = 0x80;
pub const LIST_HEADER_BYTE: u8 = 0xC0;

pub trait RlpWriter {
    fn write_bytes(&mut self, bytes: &[u8]);

    fn write_byte(&mut self, b: u8) {
        self.write_bytes(&[b]);
    }
}

/// Vec<u8> can be used as a plain byte collector
impl RlpWriter for Vec<u8> {
    fn write_bytes(&mut self, bytes: &[u8]) {
        self.extend_from_slice(bytes);
    }
}

impl RlpWriter for trezor_app_sdk::crypto::Keccak256 {
    fn write_bytes(&mut self, bytes: &[u8]) {
        self.update(bytes);
    }
}

#[cfg_attr(test, derive(Debug))]
pub enum RLPItem<'a> {
    Int(U256),
    Bytes(&'a [u8]),
    List(&'a [RLPItem<'a>]),
}

/// Returns the minimum number of bytes needed to represent an unsigned integer
fn byte_size(x: U256) -> usize {
    (x.bits() + 7) / 8
}

/// Converts unsigned integer to big-endian bytes (minimal representation)
pub fn int_to_bytes(x: U256) -> Vec<u8> {
    let size = byte_size(x);
    x.to_big_endian()[32 - size..].to_vec()
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
        let encoded_length = int_to_bytes(length.into());
        1 + encoded_length.len() as u32
    }
}

/// Calculates total RLP encoded length for an item
pub fn length(item: &RLPItem<'_>) -> u32 {
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
pub fn write_header<W: RlpWriter>(
    writer: &mut W,
    length: u32,
    header_byte: u8,
    data_start: Option<&[u8]>,
) {
    // Special case: single byte < 0x80 has no header
    if length == 1 {
        if let Some(data) = data_start {
            if !data.is_empty() && data[0] <= 0x7F {
                return;
            }
        }
    }

    if length <= 55 {
        writer.write_byte(header_byte + length as u8);
    } else {
        let encoded_length = int_to_bytes(length.into());
        writer.write_byte(header_byte + 55 + encoded_length.len() as u8);
        writer.write_bytes(&encoded_length);
    }
}

/// Writes a string (byte array) in RLP format
pub fn write_string<W: RlpWriter>(writer: &mut W, string: &[u8]) {
    write_header(writer, string.len() as _, STRING_HEADER_BYTE, Some(string));
    writer.write_bytes(string);
}

/// Writes a list in RLP format
pub fn write_list<W: RlpWriter>(writer: &mut W, lst: &[RLPItem<'_>]) {
    let payload_length: u32 = lst.iter().map(length).sum();
    write_header(writer, payload_length as _, LIST_HEADER_BYTE, None);
    for item in lst {
        write(writer, item);
    }
}

/// Writes an RLP item to the writer
pub fn write<W: RlpWriter>(writer: &mut W, item: &RLPItem<'_>) {
    match item {
        RLPItem::Int(x) => {
            write_string(writer, &int_to_bytes(*x));
        }
        RLPItem::Bytes(bytes) => {
            write_string(writer, bytes);
        }
        RLPItem::List(list) => {
            write_list(writer, list);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::strutil;

    macro_rules! rlp_cases {
    ($($name:ident => ($item:expr, $expected_hex:expr)),+ $(,)?) => {
        $(
            mod $name {
                use super::*;

                #[test]
                #[inline(never)]
                fn write() {
                    let item = $item;
                    let expected = strutil::hex_decode($expected_hex).unwrap();
                    let mut out = Vec::new();
                    super::write(&mut out, &item);
                    assert_eq!(out, expected);
                }

                #[test]
                #[inline(never)]
                fn length() {
                    let item = $item;
                    let expected_len = ($expected_hex.len() / 2) as u32;
                    assert_eq!(super::length(&item), expected_len);
                }
            }
        )+
    };
}

    rlp_cases!(
        empty_bytes => (RLPItem::Bytes(b""), "80"),
        dog_bytes => (RLPItem::Bytes(b"dog"), "83646f67"),
        lorem_55 => (
            RLPItem::Bytes(b"Lorem ipsum dolor sit amet, consectetur adipisicing eli"),
            "b74c6f72656d20697073756d20646f6c6f722073697420616d65742c20636f6e7365637465747572206164697069736963696e6720656c69"
        ),
        lorem_56 => (
            RLPItem::Bytes(b"Lorem ipsum dolor sit amet, consectetur adipisicing elit"),
            "b8384c6f72656d20697073756d20646f6c6f722073697420616d65742c20636f6e7365637465747572206164697069736963696e6720656c6974"
        ),
        lorem_long => (
            RLPItem::Bytes(b"Lorem ipsum dolor sit amet, consectetur adipiscing elit. Curabitur mauris magna, suscipit sed vehicula non, iaculis faucibus tortor. Proin suscipit ultricies malesuada. Duis tortor elit, dictum quis tristique eu, ultrices at risus. Morbi a est imperdiet mi ullamcorper aliquet suscipit nec lorem. Aenean quis leo mollis, vulputate elit varius, consequat enim. Nulla ultrices turpis justo, et posuere urna consectetur nec. Proin non convallis metus. Donec tempor ipsum in mauris congue sollicitudin. Vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia Curae; Suspendisse convallis sem vel massa faucibus, eget lacinia lacus tempor. Nulla quis ultricies purus. Proin auctor rhoncus nibh condimentum mollis. Aliquam consequat enim at metus luctus, a eleifend purus egestas. Curabitur at nibh metus. Nam bibendum, neque at auctor tristique, lorem libero aliquet arcu, non interdum tellus lectus sit amet eros. Cras rhoncus, metus ac ornare cursus, dolor justo ultrices metus, at ullamcorper volutpat"),
            "b904004c6f72656d20697073756d20646f6c6f722073697420616d65742c20636f6e73656374657475722061646970697363696e6720656c69742e20437572616269747572206d6175726973206d61676e612c20737573636970697420736564207665686963756c61206e6f6e2c20696163756c697320666175636962757320746f72746f722e2050726f696e20737573636970697420756c74726963696573206d616c6573756164612e204475697320746f72746f7220656c69742c2064696374756d2071756973207472697374697175652065752c20756c7472696365732061742072697375732e204d6f72626920612065737420696d70657264696574206d6920756c6c616d636f7270657220616c6971756574207375736369706974206e6563206c6f72656d2e2041656e65616e2071756973206c656f206d6f6c6c69732c2076756c70757461746520656c6974207661726975732c20636f6e73657175617420656e696d2e204e756c6c6120756c74726963657320747572706973206a7573746f2c20657420706f73756572652075726e6120636f6e7365637465747572206e65632e2050726f696e206e6f6e20636f6e76616c6c6973206d657475732e20446f6e65632074656d706f7220697073756d20696e206d617572697320636f6e67756520736f6c6c696369747564696e2e20566573746962756c756d20616e746520697073756d207072696d697320696e206661756369627573206f726369206c756374757320657420756c74726963657320706f737565726520637562696c69612043757261653b2053757370656e646973736520636f6e76616c6c69732073656d2076656c206d617373612066617563696275732c2065676574206c6163696e6961206c616375732074656d706f722e204e756c6c61207175697320756c747269636965732070757275732e2050726f696e20617563746f722072686f6e637573206e69626820636f6e64696d656e74756d206d6f6c6c69732e20416c697175616d20636f6e73657175617420656e696d206174206d65747573206c75637475732c206120656c656966656e6420707572757320656765737461732e20437572616269747572206174206e696268206d657475732e204e616d20626962656e64756d2c206e6571756520617420617563746f72207472697374697175652c206c6f72656d206c696265726f20616c697175657420617263752c206e6f6e20696e74657264756d2074656c6c7573206c65637475732073697420616d65742065726f732e20437261732072686f6e6375732c206d65747573206163206f726e617265206375727375732c20646f6c6f72206a7573746f20756c747269636573206d657475732c20617420756c6c616d636f7270657220766f6c7574706174"
        ),
        int_0 => (RLPItem::Int(0.into()), "80"),
        int_1 => (RLPItem::Int(1.into()), "01"),
        int_16 => (RLPItem::Int(16.into()), "10"),
        int_79 => (RLPItem::Int(79.into()), "4f"),
        int_127 => (RLPItem::Int(127.into()), "7f"),
        int_128 => (RLPItem::Int(128.into()), "8180"),
        int_254 => (RLPItem::Int(254.into()), "81fe"),
        int_255 => (RLPItem::Int(255.into()), "81ff"),
        int_256 => (RLPItem::Int(256.into()), "820100"),
        int_1000 => (RLPItem::Int(1000.into()), "8203e8"),
        int_100000 => (RLPItem::Int(100000.into()), "830186a0"),
        int_hexffff => (RLPItem::Int(0xFFFF.into()), "82ffff"),
        int_hex10000 => (RLPItem::Int(0x1_0000.into()), "83010000"),
        int_hexffffff => (RLPItem::Int(0xFF_FFFF.into()), "83ffffff"),
        int_hex1000000 => (RLPItem::Int(0x100_0000.into()), "8401000000"),
        int_hexffffffff => (RLPItem::Int(0xFFFF_FFFF_u128.into()), "84ffffffff"),
        int_hex100000000 => (RLPItem::Int(0x1_0000_0000_u128.into()), "850100000000"),
        int_pattern => (RLPItem::Int(83729609699884896815286331701780722_u128.into()), "8f102030405060708090a0b0c0d0e0f2"),
        int_big_u256 => (
            RLPItem::Int(U256::from_dec_str("105315505618206987246253880190783558935785933862974822347068935681").unwrap()),
            "9c0100020003000400050006000700080009000a000b000c000d000e01"
        ),
        list_empty => (RLPItem::List(&[]), "c0"),
        list_dog_god_cat => (
            RLPItem::List(&[RLPItem::Bytes(b"dog"), RLPItem::Bytes(b"god"), RLPItem::Bytes(b"cat")]),
            "cc83646f6783676f6483636174"
        ),
        list_zw_4_1 => (RLPItem::List(&[RLPItem::Bytes(b"zw"), RLPItem::List(&[RLPItem::Int(4.into())]), RLPItem::Int(1.into())]), "c6827a77c10401"),
        list_asdf11 => (
            RLPItem::List(&[
                RLPItem::Bytes(b"asdf"), RLPItem::Bytes(b"qwer"), RLPItem::Bytes(b"zxcv"),
                RLPItem::Bytes(b"asdf"), RLPItem::Bytes(b"qwer"), RLPItem::Bytes(b"zxcv"),
                RLPItem::Bytes(b"asdf"), RLPItem::Bytes(b"qwer"), RLPItem::Bytes(b"zxcv"),
                RLPItem::Bytes(b"asdf"), RLPItem::Bytes(b"qwer"),
            ]),
            "f784617364668471776572847a78637684617364668471776572847a78637684617364668471776572847a78637684617364668471776572"
        ),
        list_4x_nested_triplet => (
            RLPItem::List(&[
                RLPItem::List(&[RLPItem::Bytes(b"asdf"), RLPItem::Bytes(b"qwer"), RLPItem::Bytes(b"zxcv")]),
                RLPItem::List(&[RLPItem::Bytes(b"asdf"), RLPItem::Bytes(b"qwer"), RLPItem::Bytes(b"zxcv")]),
                RLPItem::List(&[RLPItem::Bytes(b"asdf"), RLPItem::Bytes(b"qwer"), RLPItem::Bytes(b"zxcv")]),
                RLPItem::List(&[RLPItem::Bytes(b"asdf"), RLPItem::Bytes(b"qwer"), RLPItem::Bytes(b"zxcv")]),
            ]),
            "f840cf84617364668471776572847a786376cf84617364668471776572847a786376cf84617364668471776572847a786376cf84617364668471776572847a786376"
        ),
        list_32x_nested_triplet => (
            RLPItem::List(&[
                RLPItem::List(&[RLPItem::Bytes(b"asdf"), RLPItem::Bytes(b"qwer"), RLPItem::Bytes(b"zxcv")]),
                RLPItem::List(&[RLPItem::Bytes(b"asdf"), RLPItem::Bytes(b"qwer"), RLPItem::Bytes(b"zxcv")]),
                RLPItem::List(&[RLPItem::Bytes(b"asdf"), RLPItem::Bytes(b"qwer"), RLPItem::Bytes(b"zxcv")]),
                RLPItem::List(&[RLPItem::Bytes(b"asdf"), RLPItem::Bytes(b"qwer"), RLPItem::Bytes(b"zxcv")]),
                RLPItem::List(&[RLPItem::Bytes(b"asdf"), RLPItem::Bytes(b"qwer"), RLPItem::Bytes(b"zxcv")]),
                RLPItem::List(&[RLPItem::Bytes(b"asdf"), RLPItem::Bytes(b"qwer"), RLPItem::Bytes(b"zxcv")]),
                RLPItem::List(&[RLPItem::Bytes(b"asdf"), RLPItem::Bytes(b"qwer"), RLPItem::Bytes(b"zxcv")]),
                RLPItem::List(&[RLPItem::Bytes(b"asdf"), RLPItem::Bytes(b"qwer"), RLPItem::Bytes(b"zxcv")]),
                RLPItem::List(&[RLPItem::Bytes(b"asdf"), RLPItem::Bytes(b"qwer"), RLPItem::Bytes(b"zxcv")]),
                RLPItem::List(&[RLPItem::Bytes(b"asdf"), RLPItem::Bytes(b"qwer"), RLPItem::Bytes(b"zxcv")]),
                RLPItem::List(&[RLPItem::Bytes(b"asdf"), RLPItem::Bytes(b"qwer"), RLPItem::Bytes(b"zxcv")]),
                RLPItem::List(&[RLPItem::Bytes(b"asdf"), RLPItem::Bytes(b"qwer"), RLPItem::Bytes(b"zxcv")]),
                RLPItem::List(&[RLPItem::Bytes(b"asdf"), RLPItem::Bytes(b"qwer"), RLPItem::Bytes(b"zxcv")]),
                RLPItem::List(&[RLPItem::Bytes(b"asdf"), RLPItem::Bytes(b"qwer"), RLPItem::Bytes(b"zxcv")]),
                RLPItem::List(&[RLPItem::Bytes(b"asdf"), RLPItem::Bytes(b"qwer"), RLPItem::Bytes(b"zxcv")]),
                RLPItem::List(&[RLPItem::Bytes(b"asdf"), RLPItem::Bytes(b"qwer"), RLPItem::Bytes(b"zxcv")]),
                RLPItem::List(&[RLPItem::Bytes(b"asdf"), RLPItem::Bytes(b"qwer"), RLPItem::Bytes(b"zxcv")]),
                RLPItem::List(&[RLPItem::Bytes(b"asdf"), RLPItem::Bytes(b"qwer"), RLPItem::Bytes(b"zxcv")]),
                RLPItem::List(&[RLPItem::Bytes(b"asdf"), RLPItem::Bytes(b"qwer"), RLPItem::Bytes(b"zxcv")]),
                RLPItem::List(&[RLPItem::Bytes(b"asdf"), RLPItem::Bytes(b"qwer"), RLPItem::Bytes(b"zxcv")]),
                RLPItem::List(&[RLPItem::Bytes(b"asdf"), RLPItem::Bytes(b"qwer"), RLPItem::Bytes(b"zxcv")]),
                RLPItem::List(&[RLPItem::Bytes(b"asdf"), RLPItem::Bytes(b"qwer"), RLPItem::Bytes(b"zxcv")]),
                RLPItem::List(&[RLPItem::Bytes(b"asdf"), RLPItem::Bytes(b"qwer"), RLPItem::Bytes(b"zxcv")]),
                RLPItem::List(&[RLPItem::Bytes(b"asdf"), RLPItem::Bytes(b"qwer"), RLPItem::Bytes(b"zxcv")]),
                RLPItem::List(&[RLPItem::Bytes(b"asdf"), RLPItem::Bytes(b"qwer"), RLPItem::Bytes(b"zxcv")]),
                RLPItem::List(&[RLPItem::Bytes(b"asdf"), RLPItem::Bytes(b"qwer"), RLPItem::Bytes(b"zxcv")]),
                RLPItem::List(&[RLPItem::Bytes(b"asdf"), RLPItem::Bytes(b"qwer"), RLPItem::Bytes(b"zxcv")]),
                RLPItem::List(&[RLPItem::Bytes(b"asdf"), RLPItem::Bytes(b"qwer"), RLPItem::Bytes(b"zxcv")]),
                RLPItem::List(&[RLPItem::Bytes(b"asdf"), RLPItem::Bytes(b"qwer"), RLPItem::Bytes(b"zxcv")]),
                RLPItem::List(&[RLPItem::Bytes(b"asdf"), RLPItem::Bytes(b"qwer"), RLPItem::Bytes(b"zxcv")]),
                RLPItem::List(&[RLPItem::Bytes(b"asdf"), RLPItem::Bytes(b"qwer"), RLPItem::Bytes(b"zxcv")]),
                RLPItem::List(&[RLPItem::Bytes(b"asdf"), RLPItem::Bytes(b"qwer"), RLPItem::Bytes(b"zxcv")]),
            ]),
            "f90200cf84617364668471776572847a786376cf84617364668471776572847a786376cf84617364668471776572847a786376cf84617364668471776572847a786376cf84617364668471776572847a786376cf84617364668471776572847a786376cf84617364668471776572847a786376cf84617364668471776572847a786376cf84617364668471776572847a786376cf84617364668471776572847a786376cf84617364668471776572847a786376cf84617364668471776572847a786376cf84617364668471776572847a786376cf84617364668471776572847a786376cf84617364668471776572847a786376cf84617364668471776572847a786376cf84617364668471776572847a786376cf84617364668471776572847a786376cf84617364668471776572847a786376cf84617364668471776572847a786376cf84617364668471776572847a786376cf84617364668471776572847a786376cf84617364668471776572847a786376cf84617364668471776572847a786376cf84617364668471776572847a786376cf84617364668471776572847a786376cf84617364668471776572847a786376cf84617364668471776572847a786376cf84617364668471776572847a786376cf84617364668471776572847a786376cf84617364668471776572847a786376cf84617364668471776572847a786376"
        ),
        list_nested_empty_combo1 => (
            RLPItem::List(&[RLPItem::List(&[RLPItem::List(&[]), RLPItem::List(&[])]), RLPItem::List(&[])]),
            "c4c2c0c0c0"
        ),
        list_nested_empty_combo2 => (
            RLPItem::List(&[
                RLPItem::List(&[]),
                RLPItem::List(&[RLPItem::List(&[])]),
                RLPItem::List(&[RLPItem::List(&[]), RLPItem::List(&[RLPItem::List(&[])])])
            ]),
            "c7c0c1c0c3c0c1c0"
        ),
        list_keyvals => (
            RLPItem::List(&[
                RLPItem::List(&[RLPItem::Bytes(b"key1"), RLPItem::Bytes(b"val1")]),
                RLPItem::List(&[RLPItem::Bytes(b"key2"), RLPItem::Bytes(b"val2")]),
                RLPItem::List(&[RLPItem::Bytes(b"key3"), RLPItem::Bytes(b"val3")]),
                RLPItem::List(&[RLPItem::Bytes(b"key4"), RLPItem::Bytes(b"val4")]),
            ]),
            "ecca846b6579318476616c31ca846b6579328476616c32ca846b6579338476616c33ca846b6579348476616c34"
        ),
    );
}
